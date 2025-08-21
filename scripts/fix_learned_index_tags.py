#!/usr/bin/env python3

import json
import time
from pathlib import Path

def fix_learned_index_tags():
    citations_path = Path("docs/data/citations.json")
    stats_path = Path("docs/data/stats.json")
    
    # 既存のデータを読み込み
    with open(citations_path, "r", encoding="utf-8") as f:
        citations_data = json.load(f)
    
    # 新しいタグ付けロジックを適用
    from fetch_and_build import auto_tags_for
    
    updated_count = 0
    learned_index_count = 0
    
    for item in citations_data["results"]:
        old_tags = set(item.get("tags", []))
        new_tags = set(auto_tags_for(item))
        
        if old_tags != new_tags:
            item["tags"] = sorted(new_tags)
            updated_count += 1
            
            # "Learned Index"タグが追加された場合
            if "Learned Index" in new_tags and "Learned Index" not in old_tags:
                learned_index_count += 1
                title = item.get('title', 'Unknown Title')
                print(f"+ Learned Index: {title[:60]}...")
    
    print(f"\n更新された論文数: {updated_count}")
    print(f"新たに「Learned Index」タグが付いた論文数: {learned_index_count}")
    
    # 更新されたデータを保存
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump(citations_data, f, ensure_ascii=False, indent=2)
    
    # 統計を再計算
    from fetch_and_build import build_stats
    stats = build_stats(citations_data["results"])
    stats["execution_time_seconds"] = 0.5  # テスト用
    
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 最終的な「Learned Index」タグの数を確認
    total_learned_index = len([item for item in citations_data["results"] 
                              if "Learned Index" in item.get("tags", [])])
    print(f"総「Learned Index」タグ付き論文数: {total_learned_index}")
    
    print("データと統計が更新されました")

if __name__ == "__main__":
    fix_learned_index_tags()