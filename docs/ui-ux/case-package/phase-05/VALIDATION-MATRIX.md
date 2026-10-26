# Phase 5 — F01–F12 Validation Matrix / Checkpoint

**Scope:** [Review #6421939874](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6421939874). Draft document and synthetic fixtures, NOT empirical approval.

## Canonical checks and ownership

| Check | Intended result | Enforcer | Current evidence |
|---|---|---|---|
| Empty staging sample `evaluations.json` | PASS | JSON Schema 2020-12 + FormatChecker | JSON parse and basic shape only; **PASS GitHub Actions run 40365743511; see evidence section** |
| Nonempty synthetic `evaluations.nonempty.mock.json` | PASS | JSON Schema 2020-12 + FormatChecker | Created; **CI execution pending; see test_schema.py and workflow** |
| VERIFIED MAE/RMSE/R² has null `value` | REJECT | JSON Schema | conditional enforced |
| Negative VERIFIED MAE/RMSE | REJECT | JSON Schema | minimum 0 |
| UNAVAILABLE metric has nonnull value | REJECT | JSON Schema | conditional enforced |
| Wrong axis field or reference line by figure ID | REJECT | JSON Schema | FIG-P5-01/02/03 field-token constraints |
| Invalid residual sign, missing histogram metadata | REJECT | JSON Schema | figure conditional |
| INT-S PASS missing method/interval type/level/asset/ref | REJECT | JSON Schema | conditional on INT-S status; coverage evidence must also be checked for publication |
| default_evaluation_id absent from record IDs | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |
| linked evaluation points missing, mismatched config/protocol/population | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |
| duplicate evaluation_id, figure_id | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |
| fake SHA or image path traversal | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |
| asset publication review missing, MIME/size/hash mismatched | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |
| different package_revision/release_id, cross-case ref | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |
| root VERIFIED but no evaluations | REJECT | JSON Schema | conditional minItems=1 |
| staging release_id=null, timestamp=null, review=PENDING | ACCEPT staging only | JSON Schema | intended safe staging |
| published EMPTY evaluations=[] with proper release approval | ACCEPT after sealing and approval | Bundle Validator | **NOT_IMPLEMENTED** |
| Case target raw_field_id/unit vs Evaluation target column/unit mismatch | REJECT | Bundle Validator | **NOT_IMPLEMENTED** |

## Deterministic package-validator requirements (future permitted work)

1. Resolve `case.json` from `package.json.case_ref`; check `target.raw_field_id == evaluation.target.column`, `target.unit == evaluation.target.unit`, `target.value_type=number`; no guessed defaults.
2. Build unique IDs: `evaluation_id` for all records, `configuration_id` from Phase4; reject duplicate IDs, missing/default ID, source key mapping without SHA, unknown execution/config/metric_source.
3. Validate `linked_evaluation_ids[]` only to same case/release/execution/config/prediction origin and reviewed compatible protocol, distinct `cv_fold_mean` and `pooled_oof` records. **Never cross Holdout population**, even by transitive links.
4. Figure selected by its *own* owning evaluation ID; check image's source config/population, residual zero line, source paired rows approval, figure-manifest IDs and review rights. No Holdout scatter from aggregate-only.
5. Whitelist all `asset_ref`, `source_ref` and `fold_values_ref` as Case-root relative, no absolute paths, backslashes, schemes, `..` segments or symlink escape.
6. Enumerate all non-root package files, compare `package.json.files[]` one-for-one with SHA256, byte count and MIME/magic; reject unsafe SVG or unapproved private metadata/OOF/holdout rows; verify same immutable release revision.
7. Published mode: actual release ID, generated UTC timestamp (format assertion enabled), QA-approved release/reviewer, absence of MOCK empirical records, hashes complete and atomic index promotion last. Staging mode permits null/empty refs but is unpublishable.
8. Render gating: `ui` is layout-only; selected evaluation controls source/scope, review controls visibility, each metric/figure has independent VERIFIED state and asset QA. Clear stale context on case/config/population/evaluation switch.

## Test invocation to use once implementation authorized

```bash
python -m pip install 'jsonschema[format]==4.26.0'
python - <<'PY'
import json, pathlib
from jsonschema import Draft202012Validator, FormatChecker
root=pathlib.Path('docs/ui-ux/case-package/phase-05')
schema=json.loads((root/'evaluation-index.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(schema)
v=Draft202012Validator(schema,format_checker=FormatChecker())
for path in ('sample/evaluations.json','sample/evaluations.nonempty.mock.json'):
    data=json.loads((root/path).read_text(encoding='utf-8'))
    errors=list(v.iter_errors(data))
    print(path, 'PASS' if not errors else 'FAIL',*[e.message for e in errors],sep=' | ')
    assert not errors
PY
```

**Historical note (superseded by R3 evidence below):** Earlier local DNS failures prevented checkout. GitHub Actions later executed the pinned Draft 2020-12 validator successfully; see R3 Actual Runtime Evidence. Bundle validation remains NOT_IMPLEMENTED.

## F01–F12 disposition

F01 ACCEPT docs; F02 ACCEPT approach A docs; F03 ACCEPT synthetic data file; F04 DEFER negative fixtures beyond matrix until validator implementation; F05 DEFER actual schema test evidence (NOT_RUN); F06 DEFER bundle validator (NOT_IMPLEMENTED); F07 ACCEPT figure token schema; F08 ACCEPT authority decision table; F09 ACCEPT publication rules but runtime gate NOT_IMPLEMENTED; F10 ACCEPT scope/SD/INT gates; F11 ACCEPT deterministic target mapping; F12 ACCEPT canonical entry cleanup, follow-up source audit needed.


## R3 schema execution handoff (2026-10-27)

Executable [test_schema.py](./test_schema.py) was committed with synthetic positive branch (nonnegative MAE/RMSE and negative R² with evidence markers) and **10 runtime negative mutations**. It uses [GitHub Actions workflow](../../../../.github/workflows/phase5-schema-contract.yml) (workflow path from repository root: `.github/workflows/phase5-schema-contract.yml`) with `python3.11` and pinned `jsonschema==4.26.0`; `Draft202012Validator.check_schema` plus `FormatChecker()`. Run locally from checked-out PR branch with `python -m pip install 'jsonschema[format]==4.26.0' && python docs/ui-ux/case-package/phase-05/test_schema.py`.

**Runtime PASS remains UNVERIFIED until an actual workflow/job log or local stdout is captured.** Source tests are a small **Schema-only** harness; they do not implement a Bundle Validator. Cross-file JOIN, duplicate identity, provenance permission, path traversal, SHA/bytes/MIME, asset approval, target-vs-Case and release atomicity remain **NOT_IMPLEMENTED / OWNER GATE**. Do not merge/deploy from structural Schema PASS alone.

## R3 ACTUAL Runtime Evidence — 2026-10-27

**Schema validation PASS (only the schema scope)**: [GitHub Actions run #40365743511](https://github.com/wupojung/AIoT-HW2-Housing-Regression/actions/runs/40365743511), job #121722824612, branch PR #35; trigger commit `e2e8a17bd8d42ba220464c9bc9a5ae9785973638` (subsequent documentation commits do not change schema/test inputs). Python 3.11.17, `jsonschema[format]==4.26.0`, `Draft202012Validator.check_schema` and `FormatChecker` enabled. Exact command: `python docs/ui-ux/case-package/phase-05/test_schema.py` (see `.github/workflows/phase5-schema-contract.yml`).

**Observed stdout:** `empty staging PASS`, `nonempty synthetic PASS`, `synthetic numeric verified metrics / negative R2 PASS`; ten negative mutations all PASS by **actual=REJECTED**: verified MAE null, negative MAE, negative RMSE, unavailable metric with number, wrong residual X, wrong residual sign, wrong histogram reference line, interval PASS without method, root VERIFIED with empty evaluations, invalid UTC time when VERIFIED. Ends `SCHEMA STRUCTURAL TESTS PASS. Bundle JOIN/rights/hash validation NOT_IMPLEMENTED.`

**Failed run retained for causal audit:** Run [#40365535300](https://github.com/wupojung/AIoT-HW2-Housing-Regression/actions/runs/40365535300) found 9 expected negative rejections passed but `invalid UTC time` was erroneously VALID because only `jsonschema==4.26.0` core package was installed and the optional RFC3339 format validator was absent. Fixed install to **`jsonschema[format]==4.26.0`** and reran with all tests PASS. The fixture did not provide real empirical data. Do not promote MOCK to approved results.

**Separate remaining gate:** Cross-file config joins, linked population/metric-source compatibility, duplicate IDs, Case target, root manifest SHA/bytes/MIME, public asset rights, path traversal, pinned release references and actual publication remain **Bundle Validator NOT_IMPLEMENTED / Release NOT_AUTHORIZED**. Passing JSON Schema cannot certify any of those. The sample has `publication_review:PENDING` and `release_id:null` and is **staging only**.


## Local quick validator (engineer-provided simplified entry)

The stable file is [validate_schema.py](../../../design/tools/validate_schema.py), based on the engineer's provided `Draft202012Validator + FormatChecker` example. From repository root:

```bash
python -m pip install "jsonschema[format]==4.26.0"
python docs/design/tools/validate_schema.py --schema docs/ui-ux/case-package/phase-05/evaluation-index.schema.json docs/ui-ux/case-package/phase-05/sample/evaluations.json docs/ui-ux/case-package/phase-05/sample/evaluations.nonempty.mock.json
```

It prints PASS/FAIL per supplied sample and exits nonzero on schema errors. Unlike `test_schema.py`, this tool does not deliberately mutate samples into negative test cases. Neither tool validates full package hashes/authorization. Design entry: [docs/design/README.md](../../../design/README.md).
