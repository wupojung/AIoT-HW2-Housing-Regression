# RegScope Case Package — Published v1 compatibility contract

**Normative for future CLI output:** this document describes the *existing published* `package_schema_version: "1.0.0"` envelope and its validation gates. It does **not** authorize a v2 format, change currently deployed data, or claim the historical frozen Phase 1–6 schemas are sufficient for every public case artifact.

## Separation of concerns

- `docs/contracts/`: machine-readable package shape, schema registry and CLI export contract.
- `docs/ui-ux/`: how existing web renders the package; states, navigation, evidence and accessible messaging.
- `docs/crisp-dm/`: experimental protocol, split, methodology and metric meaning.
- `web/data/releases/`: published immutable evidence. Do not change these paths merely to satisfy documentation.

The authoritative **compatibility fixtures** are actual `deploy` packages:
- Ames: `web/data/releases/ames-full-model-exploration-20261028-02/cases/ames-full-model-exploration/package.json` (235 manifest files, PARTIAL).
- CAR: `web/data/releases/run03-r1/cases/used-car-price-optimized/package.json` (91 manifest files, PARTIAL).
- Release pointer: `web/data/current-release.json`, `release_id: research-cases-20261029-01`, two entries. The release pointer `package_sha256` and `package_bytes` refer to the serialized package bytes, not a recomputed/normalized dictionary.

## Published package envelope

```text
package.json
├─ package_schema_version: "1.0.0"
├─ package_id: string
├─ case_id: string  [must match selection/index]
├─ package_revision: string
├─ package_status: "PARTIAL"  [existing two cases; not a universal enum]
├─ publication: { approved: boolean, release_id: string|null, review_status: string }
├─ case_ref: "case.json"
├─ phases: { phase1..phase6: {status: string, data_ref: relative JSON path} }
├─ asset_manifest_ref: "assets/figure-manifest.json"
└─ files: [{path: relative POSIX path, sha256: 64 lowercase hex, bytes: nonnegative integer, mime: string}]
```

This is an **envelope skeleton** based on two released packages, not a newly invented authoritative comprehensive JSON Schema. Optional/required constraints not established by these two sources are marked **not specified** pending explicit contract approval. Existing Phase 1–6 schemas govern the *corresponding phase documents*; Phase 5 is now `schemas/phase-05.schema.json` (its historical `$id` remains unchanged). A package validator must not assume phase status VERIFIED implies publication approved or infer a prediction API.

## CLI pipeline (proposed interface, no code implementation authorized here)

```text
CLI input dataset + approved research artifacts
  → private computation + provenance collection (local/)
  → six phase documents and case.json
  → manifest of public-safe assets
  → validate shape, cross-refs and scientific status
  → privacy/license scan and publication-review gate
  → deterministic export, digest and byte-count generation
  → immutable public revision
  → optional Owner-approved release-index update
  → preview and Production smoke checks (separately authorized)
```

The future CLI should support **validate-only**, **export to staging** and **publish candidate** as distinct operations. It must fail closed on missing files, traversal, symlinks, duplicate manifest paths, hash mismatch, unsafe file types, dangling phase refs, inconsistent case IDs, fake VERIFIED, absent publication evidence and private row/model output. It must not overwrite immutable released revisions. CLI exit codes, flags and JSON validation-report schema are *PROPOSED*, not current implementation.

## Required acceptance gates

| Gate | Check | Expected |
| --- | --- | --- |
| CP-01 | Package parses, expected keys and six named phases exist | PASS / explicit error |
| CP-02 | `case_ref`, `asset_manifest_ref` and every `data_ref` are manifest-listed | PASS |
| CP-03 | Relative POSIX manifest paths, no traversal/absolute/backslash/duplicates | PASS |
| CP-04 | Each `files[*]` digest, byte length, MIME and actual object verified | PASS when full artifacts locally available |
| CP-05 | `case_id` matches release-index case identity | PASS |
| CP-06 | Release index package SHA-256/bytes match exact `package.json` byte stream | PASS |
| CP-07 | Phase status and publication review are reported separately | PASS |
| CP-08 | No private row data, raw CSV/TSV/parquet, model binaries or credentials in public assets | PASS |
| CP-09 | No fabricated metrics, features, runs or chart data; identity links to evidence | PASS by research audit |
| CP-10 | Phase 4 configuration and Phase 5 evaluation identity/protocol alignment | PASS by research audit |
| CP-11 | Phase 6 readiness does not imply online API | PASS |
| CP-12 | View states remain sensible for unavailable / planned / partial artifacts | PASS by UI acceptance |

See `tests/docs/test_case_package_contract.py` for a **dependency-free repository contract smoke check** covering CP-01/02/03/05/06/07 against published packages, **not** full asset bytes/visual/scientific/rights tests. All gates beyond the executed subset must be recorded UNKNOWN, not PASS.

## Security and release

Do not publish raw Kaggle samples, VIN, row-level OOF, final-fit models, secrets or private paths. The CAR competition Rules review remains PENDING. Both public packages remain PARTIAL; their mere presence in the index is not publication approval. The code branch `main` is integration; `deploy` is a release branch and is not changed under this task.
