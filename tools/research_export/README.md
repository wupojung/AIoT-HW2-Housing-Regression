# Phase 4 Case Package exporter

`case_package_export.py` is the Phase 4 CLI. Its modeling gate permits it to read only the P4-B manifest and public summary. It writes a schema-valid Case Package with Phase 4 metadata and an empty, unavailable Phase 5 slot. It does not calculate Phase 5 metrics.

Reading the OOF CSV requires the separate `--oof-gate` and `--handoff-root` arguments. That path writes a normalized `handoff.json` and `oof.csv` outside the Case Package. The handoff contains provenance digests and task/fold joins; it does not contain Phase 5 results.

The Phase 5 CLI is `tools/phase5_evaluation/cli.py`. Its `evaluate-handoff` command consumes only this normalized private handoff and the Case Package. It validates the package and handoff identities and hashes before calculating Development OOF metrics. It does not read P4-B manifests, summaries, or source OOF CSVs. Keep both outputs in the authorized private staging locations; this workflow does not authorize publication, Holdout evaluation, push, merge, or deployment.

Install the exporter validator in a tool-local environment with `python -m pip install -r tools/research_export/requirements.txt`.
