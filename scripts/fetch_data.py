#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch all works that cite "The Case for Learned Index Structures" using OpenAlex.
This script only handles data fetching and saves raw data to JSON files.

- Source work is looked up by DOI, then we follow `cited_by_api_url` with cursor paging.
- No API key is required for OpenAlex; we include a `mailto` parameter if provided.
"""

from __future__ import annotations
import os, time, json
from pathlib import Path
from typing import Dict, Any, Iterable, List

import requests

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


def main() -> None:
    print("Fetching data from OpenAlex...")
    
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
        items.append(item)

    # Save raw data
    raw_data_path = DATA_DIR / "raw_citations.json"
    with open(raw_data_path, "w", encoding="utf-8") as f:
        json.dump({
            "work": {
                "doi": TARGET_DOI,
                "openalex_id": work.get("id"),
                "display_name": work.get("display_name"),
                "cited_by_count": work.get("cited_by_count"),
            }, 
            "results": items
        }, f, ensure_ascii=False, indent=2)

    print(f"Fetched {len(items)} papers")
    print(f"Saved raw data to {raw_data_path}")

if __name__ == "__main__":
    main() 