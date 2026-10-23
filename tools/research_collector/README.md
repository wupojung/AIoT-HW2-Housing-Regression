# Research Collector

Collect public DOI metadata and prepare a local NotebookLM import package. The collector does not crawl web pages. Registry entries for URL sources include concise, researcher-written metadata and summaries; preserve original URLs and do not paste full page content.

Use lawful public APIs. Do not bypass authentication, paywalls, anti-bot controls, or other restrictions. Only set `pdf_url` after confirming the file is openly accessible and its license permits local use. Kaggle downloads must be handled manually when login or competition terms apply.

`sources.yaml` is the shareable registry and may contain public identifiers, URLs, and reviewed metadata only. Downloaded PDFs go to `local/papers/`; metadata snapshots and reports go under `local/research/`; NotebookLM preparation goes to `local/notebooklm-import/`. Output paths outside `local/` are rejected. Never commit contents of `local/`.

Run with `python tools/research_collector/collect.py`. The run writes `local/research/collection-report.json` and `local/notebooklm-import/{sources.txt,sources_manifest.json,collection_report.md}`. Failed sources are recorded individually so they do not discard successful results. The manifest records acquisition status, license status, source URL/DOI, and SHA-256 when a permitted PDF is downloaded.
