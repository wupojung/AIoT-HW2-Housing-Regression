# Phase 3 Validation Matrix

| Check | Expected | Enforcement/status |
|---|---|---|
| Empty and nonempty synthetic examples parse and match schema | PASS | Shared Phase 3 schema |
| Stages not exactly raw → filtered → processed → encoded | REJECT | Bundle Validator, NOT_IMPLEMENTED |
| Stage units compared as one common feature denominator | REJECT | UI contract |
| VERIFIED total without source evidence | REJECT | Evidence/publication review |
| VERIFIED segments have negative counts, unknown types, or sum != total | REJECT | Bundle Validator, NOT_IMPLEMENTED |
| Unknown distribution rendered as equal-width segments | REJECT | UI contract |
| Split row counts confused with feature counts or don't reconcile | REJECT | Bundle Validator, NOT_IMPLEMENTED |
| Treatment claims lack source evidence | REJECT | Data review |
| Lineage leaks row IDs/fold membership/private artifact paths | REJECT | Public-safety review |

For the Ames Sample, raw/encoded totals and split counts are source-reported only; treatment, subtype distributions, filtered counts, and pre-encoding counts remain unavailable. Validation does not inspect raw rows or run preprocessing.
