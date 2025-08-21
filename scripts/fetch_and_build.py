#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch all works that cite "The Case for Learned Index Structures" using OpenAlex,
assign auto tags, aggregate stats, and emit JSON files under docs/data/ for GitHub Pages.

- Source work is looked up by DOI, then we follow `cited_by_api_url` with cursor paging.
- No API key is required for OpenAlex; we include a `mailto` parameter if provided.
"""

from __future__ import annotations
import os, re, json, time, math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Any, Iterable, List, Set

import requests

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # optional

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA_DIR = DOCS / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ===== Configuration =====
# DOI of "The Case for Learned Index Structures" (SIGMOD'18)
TARGET_DOI = os.getenv("TARGET_DOI", "10.1145/3183713.3196909")
# Your email for OpenAlex usage statistics (optional, no emails sent)
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", os.getenv("OPENALEX_EMAIL", ""))
USER_AGENT = os.getenv("USER_AGENT", "learned-index-citations/1.0 (mailto:your-email@example.com)")

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

# ===== Helpers =====

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate"
    })
    return s


def get_work_by_doi(sess: requests.Session, doi: str) -> Dict[str, Any]:
    # Search for work by DOI using the search endpoint
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"doi:{doi}",
        "mailto": OPENALEX_MAILTO
    } if OPENALEX_MAILTO else {"filter": f"doi:{doi}"}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = sess.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if results:
                return results[0]  # Return the first (and should be only) result
            else:
                raise ValueError(f"No work found for DOI: {doi}")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text[:200]}")
            if e.response.status_code == 403 and attempt < max_retries - 1:
                print(f"Rate limited (403), retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
                continue
            else:
                raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request failed, retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
                continue
            else:
                raise


def iter_citations(sess: requests.Session, cited_by_api_url: str) -> Iterable[Dict[str, Any]]:
    """Iterate all citing works using OpenAlex cursor paging."""
    base = cited_by_api_url
    cursor = "*"
    per_page = 50  # reduced from 200 to avoid rate limiting
    params = {"per-page": per_page, "cursor": cursor}
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    # Reduce payload size via select - using valid field names
    params["select"] = ",".join([
        "id","display_name","publication_year","doi","cited_by_count",
        "primary_location","authorships","concepts","abstract_inverted_index"
    ])

    total = 0
    max_retries = 3
    while True:
        for attempt in range(max_retries):
            try:
                r = sess.get(base, params=params, timeout=60)
                r.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error {e.response.status_code}: {e.response.text[:200]}")
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    print(f"Rate limited (403), retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Request failed, retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise
        
        data = r.json()
        results = data.get("results", [])
        for w in results:
            yield w
        total += len(results)
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        params["cursor"] = cursor
        # polite delay - OpenAlex recommends at least 1 second between requests
        time.sleep(2.0)


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
    
    top_authors = [
        {
            "author_id": author_key,
            "name": get_author_display_name(author_key),
            "papers": cnt,
            "sum_citations": int(author_citations[author_key]),
            "avg_citations": (author_citations[author_key] / cnt) if cnt else 0.0,
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
    start_time = time.time()
    
    sess = _session()
    work = get_work_by_doi(sess, TARGET_DOI)
    cited_by_url = work.get("cited_by_api_url")
    if not cited_by_url:
        raise SystemExit("cited_by_api_url not found in the work object.")

    items: List[Dict[str,Any]] = []
    for w in iter_citations(sess, cited_by_url):
        item = {
            "id": w.get("id"),
            "title": w.get("display_name"),
            "publication_year": w.get("publication_year"),
            "doi": w.get("doi"),
            "cited_by_count": w.get("cited_by_count"),
            "host_venue": (w.get("primary_location") or {}).get("source",{}).get("display_name") if w.get("primary_location") and w.get("primary_location").get("source") else "Unknown",
            "landing_page_url": (w.get("primary_location") or {}).get("landing_page_url"),
            "abstract_inverted_index": w.get("abstract_inverted_index"),
            "concepts": w.get("concepts"),
            "authorships": [
                {
                    "author_id": (a.get("author") or {}).get("id"),
                    "name": (a.get("author") or {}).get("display_name"),
                    "institutions": [ (inst or {}).get("display_name") for inst in (a.get("institutions") or []) ],
                }
                for a in (w.get("authorships") or [])
            ],
        }
        item["tags"] = auto_tags_for(w)
        items.append(item)

    overrides = load_overrides()
    if overrides:
        apply_overrides(items, overrides)

    # Emit JSON
    citations_path = DATA_DIR / "citations.json"
    stats_path = DATA_DIR / "stats.json"

    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump({"work": {
            "doi": TARGET_DOI,
            "openalex_id": work.get("id"),
            "display_name": work.get("display_name"),
            "cited_by_count": work.get("cited_by_count"),
        }, "results": items}, f, ensure_ascii=False, indent=2)

    stats = build_stats(items)
    
    # 実行時間を記録
    end_time = time.time()
    execution_time = end_time - start_time
    stats["execution_time_seconds"] = round(execution_time, 2)
    
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Wrote {citations_path}")
    print(f"Wrote {stats_path}")
    print(f"Execution time: {execution_time:.2f} seconds")

if __name__ == "__main__":
    main() 