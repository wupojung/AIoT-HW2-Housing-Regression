# RegScope — Design Documentation Entry

**Status:** canonical topic entrypoint in Draft PR #35; existing design contracts are not moved in this PR. The design material belongs to the **design domain**, not strictly UI/UX. To avoid breaking reviewed links, sample paths, GitHub Actions, and related Issue #37 handoffs, physical migration is deferred to a separate path-migration PR with a complete link/CI audit.

## Read by responsibility

| Responsibility | Normative resource |
|---|---|
| Overall UX architecture / page directory | [Current UX entry](../ui-ux/REGSCOPE-UX-SPEC.md) |
| Phase 1–6 and Dashboard wireframes | [Page index](../ui-ux/REGSCOPE-RECONSTRUCTION-INDEX.md) |
| **Case Package data format** | [Case Package Spec v1](../ui-ux/case-package/CASE-PACKAGE-SPEC-v1.md) |
| **Phase 5 static data format** | [Phase 5 Data Contract](../ui-ux/case-package/phase-05/PHASE-05-DATA-CONTRACT-v1.md) |
| Phase 5 JSON Schema | [evaluation-index.schema.json](../ui-ux/case-package/phase-05/evaluation-index.schema.json) |
| Phase 5 empty and nonempty sample | [Sample folder](../ui-ux/case-package/phase-05/sample/) |
| **Phase 5 local schema validation** | [validate_schema.py](./tools/validate_schema.py) |
| Full positive/negative regression checks | [test_schema.py](../ui-ux/case-package/phase-05/test_schema.py) |
| Validation evidence and separate Bundle Gate | [VALIDATION-MATRIX.md](../ui-ux/case-package/phase-05/VALIDATION-MATRIX.md) |

### Standard local command

From repository root:

```bash
python -m pip install "jsonschema[format]==4.26.0"
python docs/design/tools/validate_schema.py --schema docs/ui-ux/case-package/phase-05/evaluation-index.schema.json docs/ui-ux/case-package/phase-05/sample/evaluations.json docs/ui-ux/case-package/phase-05/sample/evaluations.nonempty.mock.json
```

`[format]` is **required** to ensure `FormatChecker` enforces date-time on clean machines, not just on a machine with optional dependencies already installed.

The generic CLI accepts `--schema` plus one or more JSON files. It checks both example JSON documents **against the JSON Schema**. It is not an upload validator, private source audit, cross-Case JOIN validator or publication sign-off. For negative tests use `python docs/ui-ux/case-package/phase-05/test_schema.py`.

### Future directory standard (proposed, not performed)

```text
docs/design/
  README.md                          # now exists
  pages/                             # future move from docs/ui-ux/pages
  data-contracts/
    case-package/
    phase-05/
  history/
```

Only move physical files after approval and verification of all incoming GitHub references, Issue #37, relative Markdown links, Schema references, file-path based CI and sample package refs. **Do not duplicate authoritative contracts under both paths.**


## Shared validation utility

The one canonical JSON Schema CLI lives in [tools/validate_schema.py](./tools/validate_schema.py). All future Phase 1–6 schemas use the **same script**, passing their own `--schema` and JSON paths; do not duplicate `validate_schema.py` in each phase. This validates a single JSON against one Draft 2020-12 schema and does not perform cross-file bundle/reference/publication QA.
