#!/usr/bin/env python3

import json
import time
from pathlib import Path

# 既存のデータを読み込んで、新しいタグ付けロジックを適用
def apply_new_tagging():
    citations_path = Path("docs/data/citations.json")
    stats_path = Path("docs/data/stats.json")
    
    # 既存のデータを読み込み
    with open(citations_path, "r", encoding="utf-8") as f:
        citations_data = json.load(f)
    
    # 新しいタグ付けロジックを適用
    from fetch_and_build import auto_tags_for
    
    updated_count = 0
    for item in citations_data["results"]:
        old_tags = set(item.get("tags", []))
        new_tags = set(auto_tags_for(item))
        
        if old_tags != new_tags:
            item["tags"] = sorted(new_tags)
            updated_count += 1
            title = item.get('title', 'Unknown Title')
            print(f"Updated: {title[:50]}...")
            print(f"  Old tags: {sorted(old_tags)}")
            print(f"  New tags: {sorted(new_tags)}")
            print()
    
    # 更新されたデータを保存
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump(citations_data, f, ensure_ascii=False, indent=2)
    
    print(f"Updated {updated_count} papers with new tagging logic")
    
    # 統計を再計算
    from fetch_and_build import build_stats
    stats = build_stats(citations_data["results"])
    stats["execution_time_seconds"] = 0.5  # テスト用
    
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print("Statistics updated")

if __name__ == "__main__":
    apply_new_tagging() 