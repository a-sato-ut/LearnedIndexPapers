#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データをコミットしてプッシュするスクリプト。
生成されたコミットメッセージを使用して自動的にコミットとプッシュを行います。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run_git_command(command: list, check: bool = True) -> subprocess.CompletedProcess:
    """Gitコマンドを実行する"""
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    if check and result.returncode != 0:
        print(f"Gitコマンドが失敗しました: {' '.join(command)}")
        print(f"エラー: {result.stderr}")
        sys.exit(1)
    return result

def check_git_status() -> bool:
    """Gitの状態をチェックし、変更があるかどうかを確認する"""
    result = run_git_command(["git", "status", "--porcelain"], check=False)
    return bool(result.stdout.strip())

def stage_changes() -> None:
    """変更をステージングする"""
    print("変更をステージング中...")
    run_git_command(["git", "add", "."])
    print("変更がステージングされました")

def commit_changes() -> None:
    """生成されたコミットメッセージでコミットする"""
    commit_msg_path = ROOT / "commit_message.txt"
    
    if not commit_msg_path.exists():
        print("コミットメッセージファイルが見つかりません。")
        print("まず、generate_commit_message.pyを実行してください。")
        sys.exit(1)
    
    print("コミット中...")
    run_git_command(["git", "commit", "-F", "commit_message.txt"])
    print("コミットが完了しました")

def push_changes() -> None:
    """変更をプッシュする"""
    print("変更をプッシュ中...")
    run_git_command(["git", "push"])
    print("プッシュが完了しました")

def show_commit_message() -> None:
    """生成されたコミットメッセージを表示する"""
    commit_msg_path = ROOT / "commit_message.txt"
    
    if commit_msg_path.exists():
        print("\n生成されたコミットメッセージ:")
        print("-" * 50)
        with open(commit_msg_path, "r", encoding="utf-8") as f:
            print(f.read())
        print("-" * 50)
    else:
        print("コミットメッセージファイルが見つかりません。")

def main() -> None:
    print("データのコミットとプッシュを開始します...")
    
    # Gitの状態をチェック
    if not check_git_status():
        print("コミットする変更がありません。")
        return
    
    # コミットメッセージを表示
    show_commit_message()
    
    try:
        # 変更をステージング
        stage_changes()
        
        # コミット
        commit_changes()
        
        # プッシュ
        push_changes()
        
        print("\n✅ データの更新が完了しました！")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 