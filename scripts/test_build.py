#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test version of fetch_and_build.py that uses mock data for testing.
"""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA_DIR = DOCS / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_test_data():
    """Create test data for development and testing."""
    
    # Mock work data
    work_data = {
        "doi": "10.1145/3183713.3196909",
        "openalex_id": "https://openalex.org/W2962771342",
        "display_name": "The Case for Learned Index Structures",
        "cited_by_count": 1234
    }
    
    # Mock citations data
    citations_data = [
        {
            "id": "https://openalex.org/W1234567890",
            "title": "Learned Index Structures for String Keys",
            "publication_year": 2020,
            "doi": "10.1145/3318464.3389741",
            "cited_by_count": 45,
            "host_venue": "SIGMOD",
            "landing_page_url": "https://dl.acm.org/doi/10.1145/3318464.3389741",
            "authorships": [
                {
                    "author_id": "https://openalex.org/A1234567890",
                    "name": "John Doe",
                    "institutions": ["MIT"]
                }
            ],
            "tags": ["String Key", "Updatable"]
        },
        {
            "id": "https://openalex.org/W0987654321",
            "title": "PGM-index: Learned Index Structures for Main Memory",
            "publication_year": 2021,
            "doi": "10.1145/3448016.3452831",
            "cited_by_count": 67,
            "host_venue": "SIGMOD",
            "landing_page_url": "https://dl.acm.org/doi/10.1145/3448016.3452831",
            "authorships": [
                {
                    "author_id": "https://openalex.org/A0987654321",
                    "name": "Jane Smith",
                    "institutions": ["Stanford"]
                }
            ],
            "tags": ["Main-memory", "PGM-index"]
        },
        {
            "id": "https://openalex.org/W1111111111",
            "title": "ALEX: An Updatable Adaptive Learned Index",
            "publication_year": 2020,
            "doi": "10.1145/3318464.3389742",
            "cited_by_count": 89,
            "host_venue": "SIGMOD",
            "landing_page_url": "https://dl.acm.org/doi/10.1145/3318464.3389742",
            "authorships": [
                {
                    "author_id": "https://openalex.org/A1111111111",
                    "name": "Bob Johnson",
                    "institutions": ["CMU"]
                }
            ],
            "tags": ["Updatable", "ALEX", "Main-memory"]
        },
        {
            "id": "https://openalex.org/W2222222222",
            "title": "Learned Bloom Filters for String Data",
            "publication_year": 2022,
            "doi": "10.1145/3514221.3517888",
            "cited_by_count": 34,
            "host_venue": "VLDB",
            "landing_page_url": "https://dl.acm.org/doi/10.1145/3514221.3517888",
            "authorships": [
                {
                    "author_id": "https://openalex.org/A2222222222",
                    "name": "Alice Brown",
                    "institutions": ["Berkeley"]
                }
            ],
            "tags": ["Bloom Filter", "String Key", "Learned Bloom Filter"]
        },
        {
            "id": "https://openalex.org/W3333333333",
            "title": "Distributed Learned Indexes for Big Data",
            "publication_year": 2021,
            "doi": "10.1145/3448016.3452833",
            "cited_by_count": 56,
            "host_venue": "SIGMOD",
            "landing_page_url": "https://dl.acm.org/doi/10.1145/3448016.3452833",
            "authorships": [
                {
                    "author_id": "https://openalex.org/A3333333333",
                    "name": "Charlie Wilson",
                    "institutions": ["Google"]
                }
            ],
            "tags": ["Distributed", "Main-memory"]
        }
    ]
    
    # Create citations.json
    citations_path = DATA_DIR / "citations.json"
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump({
            "work": work_data,
            "results": citations_data
        }, f, ensure_ascii=False, indent=2)
    
    # Create stats.json
    from collections import Counter
    
    by_year = Counter([w.get("publication_year") for w in citations_data if w.get("publication_year")])
    by_tag = Counter(tag for w in citations_data for tag in w.get("tags", []))
    by_venue = Counter()
    citations_sum = 0
    author_counts = Counter()
    author_citations = Counter()

    for w in citations_data:
        citations_sum += int(w.get("cited_by_count") or 0)
        hv = w.get("host_venue")
        if hv: by_venue[hv] += 1
        for a in (w.get("authorships") or []):
            aid = a.get("author_id") or a.get("name") or "unknown"
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

    stats = {
        "total_works": len(citations_data),
        "by_year": dict(sorted(by_year.items())),
        "by_tag": dict(sorted(by_tag.items(), key=lambda x:(-x[1], x[0]))),
        "by_venue": dict(by_venue.most_common(30)),
        "top_authors": top_authors,
        "citations_sum": citations_sum,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    
    stats_path = DATA_DIR / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"Created test data:")
    print(f"  - {citations_path}")
    print(f"  - {stats_path}")
    print(f"  - Total papers: {len(citations_data)}")
    print(f"  - Total citations: {citations_sum}")

if __name__ == "__main__":
    create_test_data() 