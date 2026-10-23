# Repository guidance

This repository is the NCHU AIoT 2026 HW2 Housing Regression Lab. Public repository content may include reviewed code, tests, web application files, CRISP-DM documents, reviewed research reports, and public metadata or references.

## Data boundary

- Keep downloaded papers, raw datasets, private or sensitive data, NotebookLM import files, credentials, temporary data, and caches under `local/` or another ignored local path.
- Read [the data and security policy](docs/SECURITY_AND_DATA_POLICY.md) before adding research material, data, credentials, or deployment configuration.
- Keep `local/` entirely untracked. Never copy its contents into public docs, test fixtures, build output, or deployment artifacts.
- Use `.env.example` for variable names and safe defaults. Read real secrets from environment variables or ignored local configuration.
- Run `python tools/security_scan.py --all` before proposing a change that adds files or modifies build configuration.

## Workflow

- Follow BUILD → RUN → TEST → VERIFY → PASS for implementation work. Record what ran and what passed in the PR.
- Use `feature/*` branches and PRs into `main`. `main` is the integration branch. `deploy` is reserved for approved production releases; do not use it for development.
- Organize work with GitHub Issues. Use an Epic to group related issues and a Milestone to track a delivery point.
- The project uses CRISP-DM and parallel agent collaboration, with up to three concurrent agents when tasks can be isolated; see the README for the public process.
- Keep the Python package under `python/src/`, reusable tools under `tools/`, and tests under `tests/`.
