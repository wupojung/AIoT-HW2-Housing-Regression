# Phase 2 Validation Matrix

| Check | Expected | Enforcement/status |
|---|---|---|
| Empty and synthetic selector examples parse and match schema | PASS | Shared Phase 2 schema |
| Empty analyses list | Accept only with `default_analysis_id:null` | Bundle Validator, NOT_IMPLEMENTED |
| Nonempty list default ID missing or duplicated item IDs | REJECT | Bundle Validator, NOT_IMPLEMENTED |
| `VERIFIED` image ref lacks a manifest entry, file/hash, alt, or rights review | REJECT | Figure Bundle Validator, NOT_IMPLEMENTED |
| Unavailable/mock image ref displayed as a real finding | REJECT | Frontend status gate |
| Case-root traversal, external asset URL, or cross-release ref | REJECT | Bundle Validator, NOT_IMPLEMENTED |
| Table contains raw row-level data | REJECT | Public-safety review |
| Selection change leaves previous figure/finding visible | REJECT | Frontend behavior contract |

The current Ames sample has four selectors with null image/table refs and `UNAVAILABLE` status. No image files are created until an approved public-safe asset exists.
