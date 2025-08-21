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
USER_AGENT = os.getenv("USER_AGENT", "learned-index-citations/1.0 (+GitHub Actions)")

# Tagging rules: (TAG_NAME, regex pattern). Case-insensitive search on title/abstract/venue.
TAG_RULES: List[tuple[str,str]] = [
    ("String Key", r"\b(string|text|varchar|character|lexicograph|dictionary)\b"),
    ("Updatable", r"\b(update|mutable|insert|delete|dynamic|online|incremental|lsm)\b"),
    ("Disk", r"\b(disk|ssd|storage|i/o|external memory|out[- ]of[- ]core)\b"),
    ("Main-memory", r"\b(in[- ]?memory|ram)\b"),
    ("Multidimensional", r"\b(multidimensional|multi[- ]?dimensional|spatial|kd[- ]?tree|r[- ]?tree|quadtree|octree)\b"),
    ("Bloom Filter", r"\b(bloom filter|learned bloom|\bLBF\b)\b"),
    ("Sketch", r"\b(count[- ]?min|cms|sketch|hyperloglog|countmin)\b"),
    ("Hash Table", r"\b(hash table|cuckoo|robin hood|tabulation|perfect hash)\b"),
    ("B-tree", r"\b(b[- ]?tree|b\+[- ]?tree|btree)\b"),
    ("LSM-tree", r"\b(lsm[- ]?tree|log[- ]?structured merge)\b"),
    ("GPU", r"\b(gpu|cuda)\b"),
    ("Distributed", r"\b(distributed|cluster|spark|hadoop|federated)\b"),
    ("Theoretical", r"\b(theorem|proof|approximation ratio|lower bound|upper bound|asymptotic|complexity)\b"),
    ("Security/Adversarial", r"\b(poison|adversarial|attack|robust|privacy|secure)\b"),
    ("Compression", r"\b(compress|compression|succinct|entropy)\b"),
    ("Benchmark", r"\b(benchmark|microbenchmark|sosd|workload|evaluation framework)\b"),
    ("Range", r"\b(range query|interval|scan)\b"),
    ("Time-series", r"\b(time[- ]?series|temporal)\b"),
    ("Disk-based Learned Index", r"learned index.*(disk|page|io|secondary storage)"),
    ("PGM-index", r"\bpgm[- ]?index\b"),
    ("ALEX", r"\balex\b"),
    ("Learned Bloom Filter", r"learned bloom filter|lbf"),
]

# ===== Helpers =====

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def get_work_by_doi(sess: requests.Session, doi: str) -> Dict[str, Any]:
    # Using the documented "external ID" syntax for DOIs
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    params = {"mailto": OPENALEX_MAILTO} if OPENALEX_MAILTO else {}
    r = sess.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def iter_citations(sess: requests.Session, cited_by_api_url: str) -> Iterable[Dict[str, Any]]:
    """Iterate all citing works using OpenAlex cursor paging."""
    base = cited_by_api_url
    cursor = "*"
    per_page = 200  # max 200
    params = {"per-page": per_page, "cursor": cursor}
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    # Reduce payload size via select
    params["select"] = ",".join([
        "id","display_name","publication_year","doi","cited_by_count",
        "host_venue","primary_location","authorships","concepts","abstract_inverted_index"
    ])

    total = 0
    while True:
        r = sess.get(base, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        for w in results:
            yield w
        total += len(results)
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        params["cursor"] = cursor
        # polite delay
        time.sleep(0.2)


def text_blob(work: Dict[str,Any]) -> str:
    parts: List[str] = []
    title = work.get("display_name") or ""
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
    for tag, pat in TAG_RULES:
        if re.search(pat, blob, flags=re.IGNORECASE):
            tags.add(tag)
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
    by_venue = Counter()
    citations_sum = 0
    author_counts = Counter()
    author_citations = Counter()

    for w in items:
        citations_sum += int(w.get("cited_by_count") or 0)
        hv = (w.get("host_venue") or {}).get("display_name")
        if hv: by_venue[hv] += 1
        for a in (w.get("authorships") or []):
            auth = a.get("author") or {}
            aid = auth.get("id") or auth.get("display_name") or "unknown"
            author_counts[aid] += 1
            author_citations[aid] += int(w.get("cited_by_count") or 0)

    top_authors = [
        {
            "author_id": aid,
            "name": aid.split("/")[-1] if aid.startswith("https://") else aid,
            "papers": cnt,
            "sum_citations": int(author_citations[aid]),
            "avg_citations": (author_citations[aid] / cnt) if cnt else 0.0,
        }
        for aid, cnt in author_counts.most_common(50)
    ]

    return {
        "total_works": len(items),
        "by_year": dict(sorted(by_year.items())),
        "by_tag": dict(sorted(by_tag.items(), key=lambda x:(-x[1], x[0]))),
        "by_venue": dict(by_venue.most_common(30)),
        "top_authors": top_authors,
        "citations_sum": citations_sum,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> None:
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
            "host_venue": (w.get("host_venue") or {}).get("display_name") or (w.get("primary_location") or {}).get("source",{}).get("display_name"),
            "landing_page_url": (w.get("primary_location") or {}).get("landing_page_url"),
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
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Wrote {citations_path}")
    print(f"Wrote {stats_path}")

if __name__ == "__main__":
    main() 