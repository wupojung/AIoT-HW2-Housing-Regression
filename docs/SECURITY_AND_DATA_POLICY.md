# Security and Data Policy

## Public and local data

The GitHub repository and deployment outputs are public-facing. They may contain source code, tests, the web application, CRISP-DM documents, reviewed research reports, and public metadata or references.

Keep the following on the local machine in `local/`: downloaded research papers and PDFs, raw Kaggle datasets, private or sensitive data, NotebookLM import files, API keys, cookies, credentials, temporary datasets, caches, search working files, and unreviewed research drafts. Public availability of a source does not by itself make a downloaded copy or a derived file suitable for publication.

Suggested local layout (created locally and ignored as a whole):

```text
local/
├── internal/             # Private project references and handoffs
├── papers/               # Downloaded papers and PDFs
├── datasets/             # Raw datasets
├── research/              # Search results, metadata, drafts, and run reports
├── notebooklm-import/     # Files prepared for NotebookLM
├── config/                # Local configuration
├── sensitive/             # Private data and credentials
└── scratch/               # Temporary working files
```

Reviewed reports may be copied into `docs/reports/` only after checking permissions, personal information, licensing, and accidental inclusion of source material or secrets. `docs/research/notebooklm/` may describe public workflows; NotebookLM import files stay local.

## Credentials

Use environment variables or ignored local configuration for credentials. `.env.example` may contain variable names and safe placeholders only. Do not put secrets in code, notebooks, tests, commit messages, issues, or pull requests. Rotate a credential immediately if it is committed or exposed.

## Git checks

`.gitignore` is a convenience, not a security boundary. The pre-commit hook scans staged/tracked content once at commit time; CI scans each pull request once. Both check forbidden local paths, research/data file types, credential files, and common secret patterns. This avoids running the same routine scan on both branch pushes and pull requests. Use `python tools/security_scan.py --all` for an initial public-release audit or when the hook was bypassed. Review `git status` and the staged diff before every commit. If a sensitive file is already tracked, stop and remove it from the index/history using the repository owner’s incident procedure before pushing; do not continue as if ignore rules repaired it.

The scanner is a guardrail, not a proof that content is safe. Review generated files, archives, and diffs manually. Never include local data in build inputs or artifacts. Before a production release, scan the generated output once with `python tools/security_scan.py --build-dir <build-output-directory>`. Build/deployment changes must preserve this boundary and must be reviewed before enabling deployment.

## Research collection

Use lawful public metadata APIs and openly accessible source pages. Do not bypass authentication, paywalls, anti-bot controls, or access restrictions. The collector stores downloaded PDFs and working outputs under `local/`; only reviewed metadata and reports may be published.

## Branches and deployments

Use `feature/*` branches and reviewed PRs into `main`. Reserve `deploy` for approved production release commits. Configure Vercel Production Branch as `deploy`; do not allow `main` to publish Production. Restrict Preview deployments and verify the generated output contains no local or sensitive material. The repository cannot verify account-level Vercel settings, so the owner must confirm them in Vercel before enabling deployment.
