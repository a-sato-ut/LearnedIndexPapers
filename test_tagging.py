#!/usr/bin/env python3

import re
from typing import Dict, Any, List, Set

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
    ("Learned Index", r"\blearned[- ]?index(es)?\b"),
    ("Query optimization", r"\b(query optimization|query plan|query execution|query processing)\b"),
    ("Cardinality estimation", r"\b(cardinality estimation|selectivity estimation|row count estimation|table statistics)\b"),
    ("Learned Bloom Filter", r"learned bloom filter|lbf"),
]

def auto_tags_for(work: Dict[str,Any]) -> List[str]:
    # display_nameとtitleの両方を確認
    title = work.get("display_name", "") or work.get("title", "")
    blob = title.lower()
    tags: Set[str] = set()
    for tag, pat in TAG_RULES:
        if re.search(pat, blob, flags=re.IGNORECASE):
            tags.add(tag)
            # より具体的なタグがマッチした場合、より一般的なタグも追加
            if tag == "Disk-based Learned Index":
                tags.add("Learned Index")
            elif tag == "Learned Bloom Filter":
                tags.add("Bloom Filter")
    return sorted(tags)

# テストケース
test_cases = [
    {"display_name": "ALEX: An Updatable Adaptive Learned Index"},
    {"display_name": "Benchmarking learned indexes"},
    {"display_name": "Updatable learned index with precise positions"},
    {"display_name": "Learned Index Structures for Database Systems"},
    {"display_name": "Disk-based learned index for secondary storage"},
    {"display_name": "Learned bloom filter for approximate membership"},
]

print("タグ付けテスト結果:")
print("=" * 50)
for i, test_case in enumerate(test_cases, 1):
    tags = auto_tags_for(test_case)
    print(f"{i}. {test_case['display_name']}")
    print(f"   タグ: {tags}")
    print() 