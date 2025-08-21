#!/usr/bin/env python3

import json
import time
from pathlib import Path

def test_with_abstract():
    """OpenAlex APIからabstract情報を含むデータを取得してテスト"""
    
    # 既存のデータを読み込み
    citations_path = Path("docs/data/citations.json")
    with open(citations_path, "r", encoding="utf-8") as f:
        citations_data = json.load(f)
    
    # 最初の5件の論文について、OpenAlex APIから詳細情報を取得
    from fetch_and_build import _session, get_work_by_doi
    
    sess = _session()
    updated_count = 0
    
    for i, item in enumerate(citations_data["results"][:5]):  # 最初の5件のみ
        work_id = item.get("id")
        if not work_id:
            continue
            
        print(f"Processing {i+1}/5: {item['title'][:50]}...")
        
        try:
            # OpenAlex APIから詳細情報を取得
            url = f"https://api.openalex.org/works/{work_id}"
            params = {}
            if hasattr(sess, 'headers') and 'mailto' in str(sess.headers):
                params["mailto"] = sess.headers.get('mailto')
            
            r = sess.get(url, params=params, timeout=30)
            r.raise_for_status()
            work_detail = r.json()
            
            # abstractとconcepts情報を更新
            item["abstract_inverted_index"] = work_detail.get("abstract_inverted_index")
            item["concepts"] = work_detail.get("concepts")
            
            # タグを再計算
            from fetch_and_build import auto_tags_for
            new_tags = auto_tags_for(item)
            old_tags = set(item.get("tags", []))
            item["tags"] = sorted(new_tags)
            
            if old_tags != set(new_tags):
                print(f"  Tags updated: {old_tags} -> {new_tags}")
                updated_count += 1
            
            # API制限を避けるため少し待機
            time.sleep(1.0)
            
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    print(f"\nUpdated {updated_count} papers with abstract information")
    
    # 更新されたデータを保存
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump(citations_data, f, ensure_ascii=False, indent=2)
    
    # 統計を再計算
    from fetch_and_build import build_stats
    stats = build_stats(citations_data["results"])
    stats["execution_time_seconds"] = 0.5  # テスト用
    
    stats_path = Path("docs/data/stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print("Data and statistics updated")

if __name__ == "__main__":
    test_with_abstract() 