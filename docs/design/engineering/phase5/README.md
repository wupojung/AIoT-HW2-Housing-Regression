# Phase 5 engineering plan

This directory is the cold-start implementation blueprint for Issue [#37](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37). It plans a future Python CLI and exporter; it does not implement one or authorize Phase 5 data work.

## Read first

1. [Issue #37](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37): scope and governing safety boundary.
2. [Issue #37 acceptance checklist](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37#issuecomment-6419852505): itemized acceptance; checklist completion is not execution permission.
3. [PM planning review](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37#issuecomment-6419882540): schedule and S1–S5 decisions.
4. [Implementation blueprint](./phase5-implementation.md): decisions, interfaces, gates, test plan, and stop rules.
5. [P4-B experiment protocol v2](../../../crisp-dm/04-modeling-p4b-experiment-protocol.md): source for fold aggregation semantics; do not edit it as part of Phase 5.

## Authority and status

The active Phase 5 JSON contract is PR #35's accepted v1.2 design at reviewed HEAD [`8d2bc4405e08e1a1b982204984f681d90975956a`](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35), specifically its `PHASE-05-DATA-CONTRACT-v1.md`, `evaluation-index.schema.json`, samples, and validation matrix. PR #35 is an open Draft PR, not merged. The schema allows exactly `mae`, `rmse`, and `r2` under `metrics`; `additionalProperties: false` makes MAPE and MedAE invalid canonical fields. The examples below therefore keep MAPE and MedAE as conditional research candidates only.

The repository currently uses a `python/src/` layout and has `python/src/environment_check.py`, which only imports dependencies. It has no tracked package metadata or registered Phase 5 CLI. All CLI names, flags, artifacts, commands, and tests in this directory are **PROPOSED / NOT IMPLEMENTED**. The implementation blueprint specifies a future packaging choice, repository-root working directory, and import path; no command is evidence of a working CLI, schema validator, cross-file bundle validator, authorized host, or real evaluation. The local Windows venv's imports of NumPy 2.5.4 and scikit-learn 1.9.1 are environment evidence only; they do not establish portability or an empirical result.
