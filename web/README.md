# RegScope functional desktop prototype

This is a lightweight static HTML/CSS/JavaScript prototype. It has no application backend, model runtime, data-processing runtime, or third-party runtime packages.

## Preview locally

From the repository root:

```powershell
python -m http.server 8000 --directory web
```

Open <http://localhost:8000>. The Home / CRISP-DM route begins at Phase 1. The shared six-phase navigation, case switch, phase controls, dashboard mode switch, CSV header preview, and unavailable states work in the browser.

The included Ames content is an explicitly labeled MOCK fixture adapted from Draft PR #35 static samples. A planned placeholder case is available to demonstrate state clearing. No empirical model scores, EDA images, feature distributions, evaluations, trained models, or predictions are included. Dashboard Custom Dataset can preview a small local CSV header and sample; the file is not uploaded or stored. Direct URL is format-checked only, and Run stays disabled.

The prototype preserves the existing static architecture. It does not fetch live research JSON, call an API, train/evaluate models, or enable prediction. Responsive refinements, visual polish, tests, integration, Preview, and deployment are outside this handoff.

## Vercel output

The root `vercel.json` sets `web/` as the static output directory. There is no build command or install step. Deployment and security checks require their separate authorization gates. Do not add local data, credentials, research PDFs, or raw datasets to `web/`.
