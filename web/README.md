# RegScope functional desktop prototype

This is a lightweight static HTML/CSS/JavaScript prototype. It has no application backend, model runtime, data-processing runtime, or third-party runtime packages.

## Preview locally

From the repository root:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/web/>. The Home / CRISP-DM route begins at Phase 1. The shared six-phase navigation, case switch, phase controls, dashboard mode switch, CSV header preview, and unavailable states work in the browser. The repository root is served only on loopback so the local preview can read the ignored staging package; do not expose this server to a network.

The case selector keeps the MOCK UI fixture as its own selectable case and adds the formal Ames Case Package as a separate option. Selecting the formal package loads its static Phase 5 evaluation index and displays the indexed CV fold mean and pooled OOF metrics. Other phase pages continue to show their existing preview content. Diagnostic figures remain unavailable because the evaluation records do not reference figures and the package marks its figure assets as `PLANNED`; those assets are not substituted with mock charts. A planned placeholder case remains available to demonstrate state clearing. Dashboard Custom Dataset can preview a small local CSV header and sample; the file is not uploaded or stored. Direct URL is format-checked only, and Run stays disabled.

## Ames Case Package static reference

The complete Case Package copy is kept outside the static site at the ignored private path `local/staging/formal-data-test-20261027-01/case-package/`. Keep the package root, `package.json`, all manifest-listed files, and relative paths together. It contains 236 files (235 package manifest entries plus `package.json`); all manifest file hashes and byte counts match. This is staging, not a public release.

The frontend reads this private staging path only on a loopback preview. On other hosts it shows an unavailable state until an approved immutable release is produced. The PR #35 release layout is `/data/current-release.json` plus `/data/releases/<release_id>/cases/<case_id>/...`; this staging copy is not placed under `web/` and will not leak into the static output. Its package content and Phases 1–4 are marked `VERIFIED` for the requested UI state check. Phase 5 retains `PLANNED` / independent review `PENDING`, and each evaluation remains `AWAITING_REVIEW`. The Kaggle source page identifies the dataset license as MIT. The Phase 5 index has 60 evaluations, while figure references are empty and the figure manifest marks its 90 PNG assets `PLANNED`.

Phase 6 offers manual entry and an alternate browser-local CSV flow. CSV headers are matched only by the exact names `Neighborhood`, `OverallQual`, `BedroomAbvGr`, and `GrLivArea`; a selected row can populate the matching manual controls. The file is read in browser memory, is not uploaded or persisted, and unsupported or out-of-range values are not applied. The mock estimate remains fixed and is not calculated from either manual or CSV input.

The prototype remains static. It does not fetch live research services, call an API, train or evaluate a model, or enable real prediction. Do not copy raw datasets, private research, credentials, or unreviewed working files into `web/`.

## Vercel output

The root `vercel.json` sets `web/` as the static output directory. There is no build command or install step. Deployment and security checks require their separate authorization gates. Do not add local data, credentials, research PDFs, or raw datasets to `web/`.
