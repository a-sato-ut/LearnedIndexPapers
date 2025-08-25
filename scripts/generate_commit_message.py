#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate commit message based on newly added papers.
This script compares current data with previous data and generates a commit message
that includes the count and titles of newly added papers.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA_DIR = DOCS / "data"

def load_current_data() -> List[Dict[str, Any]]:
    """現在のデータを読み込む"""
    citations_path = DATA_DIR / "citations.json"
    if not citations_path.exists():
        return []
    
    with open(citations_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("results", [])

def load_previous_data() -> List[Dict[str, Any]]:
    """前回のデータを読み込む（Gitの前回のコミットから）"""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:docs/data/citations.json"],
            capture_output=True,
            text=True,
            cwd=ROOT
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("results", [])
        else:
            return []
    except Exception:
        return []

def get_new_papers(current: List[Dict[str, Any]], previous: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """新しく追加された論文を特定する"""
    if not previous:
        return current
    
    previous_ids = {paper.get("id") for paper in previous if paper.get("id")}
    new_papers = []
    
    for paper in current:
        if paper.get("id") and paper.get("id") not in previous_ids:
            new_papers.append(paper)
    
    return new_papers

def generate_commit_message(new_papers: List[Dict[str, Any]]) -> str:
    """コミットメッセージを生成する"""
    if not new_papers:
        return "データ更新: 新しく追加された論文なし"
    
    count = len(new_papers)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    message = f"データ更新 ({current_date}): {count}件の新論文を追加\n\n"
    message += "新しく追加された論文:\n"
    
    for i, paper in enumerate(new_papers, 1):
        title = paper.get("title") or paper.get("display_name") or "タイトルなし"
        year = paper.get("publication_year") or "年不明"
        url = paper.get("url") or paper.get("doi") or ""
        
        message += f"{i}. {title} ({year})\n"
        if url:
            message += f"   URL: {url}\n"
        message += "\n"
    
    return message

def save_commit_message(message: str) -> None:
    """コミットメッセージをファイルに保存"""
    commit_msg_path = ROOT / "commit_message.txt"
    with open(commit_msg_path, "w", encoding="utf-8") as f:
        f.write(message)

def main() -> None:
    current_data = load_current_data()
    previous_data = load_previous_data()
    new_papers = get_new_papers(current_data, previous_data)
    commit_message = generate_commit_message(new_papers)
    save_commit_message(commit_message)

if __name__ == "__main__":
    main() 