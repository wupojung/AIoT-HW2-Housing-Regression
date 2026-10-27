# Phase 1 Validation Matrix

| Check | Expected | Enforcement/status |
|---|---|---|
| Empty sample parses and matches schema | PASS | Shared Phase 1 schema |
| Synthetic text fixture matches schema | PASS | Shared Phase 1 schema; MOCK watermark required |
| Duplicate or empty section ID/title/body | REJECT | Schema handles empty values; uniqueness is Bundle Validator work, NOT_IMPLEMENTED |
| `VERIFIED` prose without attributable review/source | REJECT | Review/publication gate, NOT_IMPLEMENTED |
| Case text changes the target name/unit from `case.json` | REJECT | Cross-file content review, NOT_IMPLEMENTED |
| Empty body displayed as a scientific conclusion | REJECT | Frontend contract |
| Private paths, raw rows, credentials, or unsupported claims | REJECT | Data and editorial review |

`UNAVAILABLE` plus an empty `sections` list is valid and should render an explicit empty state. A schema PASS does not approve prose for release.
