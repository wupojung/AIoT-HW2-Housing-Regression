# NCHU AIoT 2026 — HW2 Housing Regression Lab

This repository is an independent home for the HW2 Housing Regression Lab. It will explore housing regression, feature selection, and a web dashboard. The initial repository setup establishes project and data-safety practices; it does not claim that the model or dashboard is implemented.

## Project method: CRISP-DM

The project adopts CRISP-DM as its end-to-end data-mining process:

1. **Business Understanding** — define the housing problem, audience, and success criteria.
2. **Data Understanding** — identify permitted sources and assess data meaning and quality.
3. **Data Preparation** — document cleaning, transformations, and feature selection.
4. **Modeling** — build and compare regression approaches.
5. **Evaluation** — assess results against the stated criteria and known limitations.
6. **Deployment** — prepare reviewed outputs for the intended application and release.

Work is tracked through GitHub Issues. An **Epic** groups related issues around a larger outcome; a **Milestone** marks a delivery point or deadline. Issues should state the CRISP-DM phase, goal, acceptance criteria, and related Epic where applicable.

## Collaboration

The team uses parallel agent collaboration: agents work on separate tasks and review or reconcile results before delivery. The workflow can use up to three concurrent agents when tasks can be isolated. Each change remains reviewable through Issues and pull requests. Public project documentation describes this workflow without exposing private handoffs or credentials.

## Repository map

- `python/src/` — Python application and modeling package.
- `web/` — web application and dashboard.
- `tools/research_collector/` — public-source metadata collection utilities.
- `tests/` — automated checks, including security scanner cases.
- `docs/` — public policy, CRISP-DM materials, and reviewed reports.
- `local/` — local-only working area; ignored by Git and excluded from deployment.

## Data boundary

Keep raw datasets, downloaded papers, private or sensitive data, NotebookLM import files, credentials, temporary research outputs, and caches in `local/`. The `tools/` source code may be public, but its outputs and credentials stay local. Only reviewed, publishable reports and metadata belong in `docs/`.

Copy `.env.example` to `.env` for local configuration. Never put real credentials in source code, examples, tests, issues, or pull requests. Read [Security and Data Policy](docs/SECURITY_AND_DATA_POLICY.md) before adding data or changing build/deployment behavior.

## Branch and release policy

- `main` is the integration branch. Changes arrive through reviewed pull requests from `feature/*` branches.
- `deploy` is reserved for approved production releases. It is not a development branch and must not be updated until the release is reviewed and the owner has verified Vercel settings.
- Do not configure `main` to publish Production. Set Vercel Production Branch to `deploy`; restrict Preview deployments and verify their output excludes local and sensitive content. Repository setup does not itself configure or trigger Vercel.

## Development checks

Install the pre-commit hook with `pre-commit install`. Run `python tools/security_scan.py --all` to scan tracked and untracked repository files before review. CI runs the same security checks. Follow **BUILD → RUN → TEST → VERIFY → PASS** and record validation evidence in the pull request.

For WSL, Python environment, and agent CLI setup, see [Developer Setup](docs/SETUP.md).
