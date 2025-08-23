# Learned-Index Citations (GitHub Pages)

This site lists **all papers citing** "The Case for Learned Index Structures" (SIGMOD 2018 / DOI: 10.1145/3183713.3196909), with **auto tags** and **stats**. Data is refreshed daily via GitHub Actions from the OpenAlex API.

## How it works
1. `scripts/fetch_and_build.py` resolves the target work by DOI via `GET /works/https://doi.org/{doi}` and follows `cited_by_api_url` (cursor paging) to enumerate **all citing works**.
2. It assigns tags by simple regex heuristics (editable), applies optional `data/overrides.yml`, and writes `docs/data/*.json`.
3. `docs/index.html` (GitHub Pages) loads JSON and renders search, tag filter, charts (Chart.js), and lists.

## Configure
- Enable GitHub Pages from branch **main /docs**.
- (Optional) Add repository secret `OPENALEX_MAILTO` with your email for OpenAlex usage statistics.
- Optionally edit `data/overrides.yml` to add/remove tags or hide items.

## Local run
```bash
python -m venv .venv && source .venv/bin/activate
pip install requests pyyaml
export OPENALEX_MAILTO=you@example.com
python scripts/fetch_and_build.py
# Open docs/index.html in a browser (uses relative JSON paths)
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
- 毎週月曜日の午前9時（UTC）に自動実行
- 新しい論文がある場合のみコミットとプッシュ
- 生成されたコミットメッセージを使用

## Notes

* OpenAlex API is free and no key is required. Respect rate limits; we include short delays and `mailto` for usage statistics.
* Citation counts shown for citing papers are `cited_by_count` reported by OpenAlex.
* This project is unaffiliated with OpenAlex/ACM. 