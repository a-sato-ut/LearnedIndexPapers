# Learned Index Papers

このサイトは「The Case for Learned Index Structures」(SIGMOD 2018 / DOI: 10.1145/3183713.3196909) を引用している**全ての論文**を、**自動タグ付け**と**統計情報**と共に掲載しています。データはGitHub ActionsによってOpenAlex APIから毎日更新されます。

## ライブサイト
📖 **[https://a-sato-ut.github.io/LearnedIndexPapers/](https://a-sato-ut.github.io/LearnedIndexPapers/)**

このページのためのソースコードです。

## 動作原理
1. `scripts/fetch_data.py` がDOI経由で対象論文を特定し、`cited_by_api_url`（カーソルページング）を使用して**全ての引用論文**を列挙します。
2. シンプルな正規表現ヒューリスティクス（編集可能）でタグを割り当て、オプションで`data/overrides.yml`を適用し、`docs/data/*.json`に書き出します。
3. `docs/index.html`（GitHub Pages）がJSONを読み込み、検索、タグフィルター、グラフ（Chart.js）、リストを表示します。

## 設定
- GitHub Pagesを**main /docs**ブランチから有効化してください。
- （オプション）OpenAlex使用統計のため、リポジトリシークレット`OPENALEX_MAILTO`にメールアドレスを追加してください。
- 必要に応じて`data/overrides.yml`を編集してタグの追加/削除やアイテムの非表示を行ってください。

## ローカル実行
```bash
python -m venv .venv && source .venv/bin/activate
pip install requests pyyaml
export OPENALEX_MAILTO=you@example.com
python scripts/fetch_data.py
python scripts/process_data.py
# ブラウザでdocs/index.htmlを開く（相対パスのJSONを使用）
```

## コミットメッセージの自動生成

新しく追加された論文の数とタイトルを含むコミットメッセージが自動生成されます。

### 自動生成されるコミットメッセージの例
```
データ更新 (2024-01-15): 3件の新論文を追加

新しく追加された論文:
1. Learned Index Structures for Database Systems (2024)
2. Efficient Learned Indexing for Time Series Data (2024)
3. Neural Database Indexes: A Survey (2024)
```

### 手動でのコミットとプッシュ
```bash
# コミットメッセージを生成
python scripts/generate_commit_message.py

# 生成されたメッセージでコミットとプッシュ
python scripts/commit_and_push.py
```

### GitHub Actionsでの自動更新
- 毎日午後6時30分（UTC）に自動実行
- 新しい論文がある場合のみコミットとプッシュ
- 生成されたコミットメッセージを使用
