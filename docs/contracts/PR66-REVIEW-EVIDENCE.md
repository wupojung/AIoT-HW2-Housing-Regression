# PR #66 — Architecture Review Remediation Evidence

External review: [comment 6496594226](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/66#issuecomment-6496594226). This is a **checkpoint, not a merge PASS**.

## #1 CP-03 lexical reference security

`tests/docs/test_case_package_contract.py` now rejects original input containing `.. ` / `.` segments, repeated or trailing slash, absolute path, backslash, colon/drive/URI formats and nonstrings; it contains positive and negative cases. **Scope: lexical only.** File-system containment, symlink checks, MIME integrity and published full assets are not proven by this function.

## #2 Gate evidence

See [CASE-PACKAGE-CONTRACT.md](CASE-PACKAGE-CONTRACT.md) section *Gate coverage versus execution evidence*. All executed results remain **NOT RUN**; test implementation coverage is consistently PARTIAL or NOT IMPLEMENTED.

## #3 Reproducibility and Schema migration

Commands to run on a checked-out PR #66 head:

```sh
python -m unittest discover -s tests/docs -p 'test_case_package_contract.py' -v
python -m unittest discover -s tests/core -p 'test_phase5_evaluation.py' -v
python -m unittest discover -s tests/core -p 'test_model_exploration.py' -v
python -m unittest discover -s tests/core -p 'test_used_car_case_package.py' -v
python -m unittest discover -s tests/e2e -p 'test_minimal_e2e_package.py' -v
git grep -n -e 'docs/design/data-contracts/schemas/' -e 'docs/ui-ux/case-package/phase-05/evaluation-index.schema.json' -- ':!docs/**'
```

**Execution result: NOT RUN.** The isolated execution container has no DNS access to `github.com` (`git ls-remote` failed with `Could not resolve host: github.com`); connector access does not provide a checked-out Python workspace. Do not represent those tests as PASS.

GitHub content SHA comparisons independently checked via connector, `main` designated source → PR #66 canonical destination:

| Phase | Old source blob SHA | New blob match |
| --- | --- | --- |
| 01 | `ee166769a954a3523314992b9eb95ca3ba6b1e36` | MATCH |
| 02 | `fd22267016e9edaaac2092368e57aa489623a487` | MATCH |
| 03 | `760b46716dbbffc8d5eba8672ea071b63edd6af0` | MATCH |
| 04 | `5dd41d3f268ed32b917d8e25e78f43d1fd48cf49` | MATCH |
| 05 | `c5ce014f9b96fded1df2f756f590c88d1401eac6` | MATCH |
| 06 | `12e77ab940e50a001676c27d72956553be5bcebc` | MATCH |

All schema files preserved byte-for-byte, including Phase 05 historical `$id`. Python consumers previously identified and updated: `reference_e2e.py`, `e2e_package.py`, `model_exploration_package.py`, `used_car_case_package.py`; tests: `test_model_exploration.py`, `test_phase5_evaluation.py`. **A complete grep across all text files has not been executed**; remaining consumers are UNKNOWN until local scan.

## #4–5 Contract boundary / CLI integration

The Case Package contract distinguishes published v1 MUST compatibility from observed-only fixture properties, PROPOSED CLI interfaces and non-goals. Staging/validation/publish-candidate flows, digest ordering, failure and immutable-release semantics documented without asserting implemented CLI.

## #6 UX inventory

[PHASE-ACCEPTANCE.md](../ui-ux/PHASE-ACCEPTANCE.md) includes UX-01–16 with static/browser surfaces, separate Ames/CAR expected states and `NOT RUN` evidence, against the released branch SHA; existing Phase 6 old heading is explicitly distinguished from the approved target.

## #7 Supersession evidence

- [PR #63](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/63): CLOSED / UNMERGED; supersession comment [6496379016](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/63#issuecomment-6496379016).
- [PR #65](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/65): CLOSED / UNMERGED; supersession comment [6496381257](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/65#issuecomment-6496381257).
- [PR #66](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/66): only candidate Draft; no merge/deploy authorization.

## Stop conditions

No merge until local focused tests, repository-wide active-reference scan, independent reviewer acceptance, and explicit Owner merge gate. This checkpoint does not certify privacy/license, scientific fitness, Production HTTP, or responsive/browser validation.
