#!/usr/bin/env python3

import json
import time
from pathlib import Path

# 既存のデータを読み込んで、新しい著者統計ロジックを適用
def test_author_stats():
    citations_path = Path("docs/data/citations.json")
    stats_path = Path("docs/data/stats.json")
    
    # 既存のデータを読み込み
    with open(citations_path, "r", encoding="utf-8") as f:
        citations_data = json.load(f)
    
    # 新しい統計生成ロジックを適用
    from fetch_and_build import build_stats
    
    print("統計を再生成中...")
    stats = build_stats(citations_data["results"])
    stats["execution_time_seconds"] = 0.5  # テスト用
    
    # 著者統計を表示
    print(f"\n総論文数: {stats['total_works']}")
    print(f"主要著者 (上位10名):")
    for i, author in enumerate(stats["top_authors"][:10], 1):
        print(f"  {i:2d}. {author['name']} ({author['papers']}本, 合計引用数: {author['sum_citations']})")
    
    # 更新されたデータを保存
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n統計が {stats_path} に保存されました")

if __name__ == "__main__":
    test_author_stats()