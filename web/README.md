# RegScope web foundation

RegScope M0 is a lightweight, static HTML/CSS/JavaScript showcase. It has no application backend, database, third-party runtime packages, or model results. The small responsive navigation script only opens and closes the mobile menu.

## Run locally

From the repository root:

```powershell
python -m http.server 8000 --directory web
```

Open <http://localhost:8000>. The same command works with Python on macOS and Linux.

## Vercel output

The root `vercel.json` sets `web/` as the static output directory. Only the site files in that directory are published as the deployment output. There is no build command or install step. Before an approved deployment, run:

```powershell
python tools/security_scan.py --build-dir web
```

Do not add local data, credentials, research PDFs, or raw datasets to `web/`. See `docs/SECURITY_AND_DATA_POLICY.md` for the repository data boundary and Vercel release checks.
