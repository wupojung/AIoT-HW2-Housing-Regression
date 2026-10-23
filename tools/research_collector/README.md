# Research Collector

Minimal starting point for collecting metadata about sources identified by DOI or URL. Use lawful public APIs where available. Do not bypass authentication, paywalls, anti-bot controls, or other access restrictions.

`sources.yaml` is the shareable registry and may contain public DOI/URL identifiers only. Downloaded PDFs go to `local/papers/`; metadata snapshots and collection reports go under `local/research/`; NotebookLM import lists go to `local/notebooklm-import/`. Output paths outside `local/` are rejected.

Planned first-stage capabilities are metadata lookup, SHA-256 verification, deduplication, optional local PDF storage when legally accessible, a local collection report, and NotebookLM import preparation. This repository initialization provides the registry and policy boundary; bulk collection is not configured.
