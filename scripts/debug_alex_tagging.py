#!/usr/bin/env python3

import json
import time
from pathlib import Path

def debug_alex_tagging():
    citations_path = Path("docs/data/citations.json")
    
    # 既存のデータを読み込み
    with open(citations_path, "r", encoding="utf-8") as f:
        citations_data = json.load(f)
    
    # ALEX論文を探す
    alex_paper = None
    for item in citations_data["results"]:
        if "ALEX: An Updatable Adaptive Learned Index" in item.get("title", ""):
            alex_paper = item
            break
    
    if not alex_paper:
        print("ALEX論文が見つかりませんでした")
        return
    
    print("ALEX論文の現在の状態:")
    print(f"タイトル: {alex_paper['title']}")
    print(f"現在のタグ: {alex_paper.get('tags', [])}")
    
    # 新しいタグ付けロジックを適用
    from fetch_and_build import auto_tags_for
    
    new_tags = auto_tags_for(alex_paper)
    print(f"新しいタグ: {new_tags}")
    
    # タグを更新
    old_tags = set(alex_paper.get("tags", []))
    alex_paper["tags"] = sorted(new_tags)
    
    print(f"タグが更新されました: {old_tags} -> {new_tags}")
    
    # 更新されたデータを保存
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump(citations_data, f, ensure_ascii=False, indent=2)
    
    print("データが保存されました")

if __name__ == "__main__":
    debug_alex_tagging() 