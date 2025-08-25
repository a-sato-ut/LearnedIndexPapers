#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process raw citation data by applying tags and generating statistics.
This script reads raw_citations.json and outputs citations.json and stats.json.

- Applies auto-tagging based on tag_rules.yml
- Applies manual overrides from overrides.yml
- Generates statistics and charts data
"""

from __future__ import annotations
import os, re, json, time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Any, List, Set

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # optional

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA_DIR = DOCS / "data"

def load_tag_rules() -> List[tuple[str,str,str]]:
    """Load tagging rules from YAML file."""
    path = ROOT / "data" / "tag_rules.yml"    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    rules = []
    for rule in data.get("tag_rules", []):
        name = rule.get("name")
        pattern = rule.get("pattern")
        category = rule.get("category", "Other")
        if name and pattern:
            rules.append((name, pattern, category))
    
    return rules


def text_blob(work: Dict[str,Any]) -> str:
    parts: List[str] = []
    # タイトルを取得（display_nameまたはtitleフィールドから）
    title = work.get("title") or work.get("display_name") or ""
    parts.append(str(title))
    # venue names
    for key in ("host_venue","primary_location"):
        hv = work.get(key) or {}
        if isinstance(hv, dict):
            dn = hv.get("display_name")
            if dn: parts.append(str(dn))
            src = hv.get("source") or {}
            if isinstance(src, dict):
                sdn = src.get("display_name")
                if sdn: parts.append(str(sdn))
    # abstract (inverted index → bag of words)
    inv = work.get("abstract_inverted_index") or {}
    if isinstance(inv, dict) and inv:
        parts.append(" ".join(inv.keys()))
    # concepts
    concepts = work.get("concepts") or []
    for c in concepts:
        dn = c.get("display_name")
        if dn: parts.append(str(dn))
    return " \n".join(parts).lower()


def auto_tags_for(work: Dict[str,Any]) -> List[str]:
    blob = text_blob(work)
    tags: Set[str] = set()
    tag_rules = load_tag_rules()
    for tag, pat, category in tag_rules:
        if re.search(pat, blob, flags=re.IGNORECASE):
            tags.add(tag)
            # より具体的なタグがマッチした場合、より一般的なタグも追加
            if tag == "Disk-based Learned Index":
                tags.add("Learned Index")
            elif tag == "Learned Bloom Filter":
                tags.add("Bloom Filter")
    return sorted(tags)


def load_overrides() -> Dict[str, Any]:
    path = ROOT / "data" / "overrides.yml"
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def apply_overrides(items: List[Dict[str,Any]], overrides: Dict[str,Any]) -> None:
    add_map = {k: set(v or []) for k,v in (overrides.get("add_tags", {}) or {}).items()}
    remove_map = {k: set(v or []) for k,v in (overrides.get("remove_tags", {}) or {}).items()}
    hide_set = set(overrides.get("hide", []) or [])
    kept: List[Dict[str,Any]] = []
    for w in items:
        wid = w.get("id")
        if wid in hide_set:
            continue
        cur = set(w.get("tags", []))
        if wid in remove_map:
            cur -= remove_map[wid]
        if wid in add_map:
            cur |= add_map[wid]
        w["tags"] = sorted(cur)
        kept.append(w)
    items[:] = kept


def build_stats(items: List[Dict[str,Any]]) -> Dict[str,Any]:
    by_year = Counter([w.get("publication_year") for w in items if w.get("publication_year")])
    by_tag = Counter(tag for w in items for tag in w.get("tags", []))
    
    # Tag categories
    tag_categories = {}
    tag_rules = load_tag_rules()
    for tag, pattern, category in tag_rules:
        tag_categories[tag] = category
    
    by_venue = Counter()
    citations_sum = 0
    author_counts = Counter()
    author_citations = Counter()
    author_names = {}  # author_id -> name のマッピング

    for w in items:
        citations_sum += int(w.get("cited_by_count") or 0)
        hv = w.get("host_venue")
        if hv: by_venue[hv] += 1
        for a in (w.get("authorships") or []):
            # データ構造に応じて著者IDと名前を取得
            aid = a.get("author_id") or "unknown"
            name = a.get("name") or "unknown"
            # author_id がある場合はそれを使用、そうでなければ名前を使用
            author_key = aid if aid != "unknown" else name
            
            # 著者名をマッピングに保存
            if aid != "unknown" and name != "unknown":
                author_names[aid] = name
            elif aid == "unknown" and name != "unknown":
                author_names[name] = name
                
            author_counts[author_key] += 1
            author_citations[author_key] += int(w.get("cited_by_count") or 0)

    # 著者キーから適切な表示名を生成
    def get_author_display_name(author_key):
        # 著者名マッピングから実際の名前を取得
        if author_key in author_names:
            return author_names[author_key]
        elif author_key.startswith("https://openalex.org/"):
            return author_key.split("/")[-1]
        else:
            return author_key
    
    # 著者の所属情報を収集（年次情報付き）
    author_institutions = defaultdict(set)
    author_institution_years = defaultdict(lambda: defaultdict(set))
    for w in items:
        year = w.get("publication_year")
        for authorship in w.get("authorships", []):
            author_id = authorship.get("author_id", "unknown")
            author_name = authorship.get("name", "unknown")
            institutions = authorship.get("institutions", [])
            
            # 著者キーを決定
            author_key = author_id if author_id != "unknown" else author_name
            
            # 所属情報を追加
            for institution in institutions:
                author_institutions[author_key].add(institution)
                if year:
                    author_institution_years[author_key][institution].add(year)
    
    top_authors = [
        {
            "author_id": author_key,
            "name": get_author_display_name(author_key),
            "papers": cnt,
            "sum_citations": int(author_citations[author_key]),
            "avg_citations": (author_citations[author_key] / cnt) if cnt else 0.0,
            "institutions": list(author_institutions[author_key]),
            "institution_years": {
                institution: {
                    "years": sorted(list(years)),
                    "year_range": f"{min(years)}-{max(years)}" if years else ""
                }
                for institution, years in author_institution_years[author_key].items()
            }
        }
        for author_key, cnt in author_counts.most_common()
    ]

    # 著者名による論文数統計を追加
    by_author = {}
    for author_key, cnt in author_counts.items():
        author_name = get_author_display_name(author_key)
        by_author[author_name] = cnt

    return {
        "total_works": len(items),
        "by_year": dict(sorted(by_year.items())),
        "by_tag": dict(sorted(by_tag.items(), key=lambda x:(-x[1], x[0]))),
        "by_tag_category": dict(sorted(by_tag.items(), key=lambda x:(tag_categories.get(x[0], "Other"), -x[1], x[0]))),
        "tag_categories": tag_categories,
        "by_venue": dict(by_venue.most_common(30)),
        "by_author": by_author,
        "top_authors": top_authors,
        "citations_sum": citations_sum,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> None:
    print("Processing raw citation data...")
    
    # Load raw data
    raw_data_path = DATA_DIR / "raw_citations.json"
    if not raw_data_path.exists():
        raise SystemExit(f"Raw data file not found: {raw_data_path}")
    
    with open(raw_data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    items = raw_data.get("results", [])
    work_info = raw_data.get("work", {})
    
    print(f"Loaded {len(items)} papers from raw data")
    
    # Apply auto-tagging
    print("Applying auto-tags...")
    for item in items:
        item["tags"] = auto_tags_for(item)
    
    # Apply manual overrides
    overrides = load_overrides()
    if overrides:
        print("Applying manual overrides...")
        apply_overrides(items, overrides)
    
    # Generate output files
    citations_path = DATA_DIR / "citations.json"
    stats_path = DATA_DIR / "stats.json"
    
    # Save processed citations
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump({
            "work": work_info,
            "results": items
        }, f, ensure_ascii=False, indent=2)
    
    # Generate and save statistics
    stats = build_stats(items)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"Processed {len(items)} papers")
    print(f"Saved processed data to {citations_path}")
    print(f"Saved statistics to {stats_path}")

if __name__ == "__main__":
    main() 