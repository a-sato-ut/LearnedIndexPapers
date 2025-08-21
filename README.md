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

## Notes

* OpenAlex API is free and no key is required. Respect rate limits; we include short delays and `mailto` for usage statistics.
* Citation counts shown for citing papers are `cited_by_count` reported by OpenAlex.
* This project is unaffiliated with OpenAlex/ACM. 