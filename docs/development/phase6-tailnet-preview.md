# CAR Phase 6 Tailnet Preview (Local Experiment)

This bounded preview serves one verified CAR Run 03 model to an exact Tailscale
HTTPS device origin. It is not a public API, production deployment, or claim of
useful predictive quality. The existing CAR model has negative Development R²
and performs below its Dummy baseline.

Tailnet mode is an opt-in layer on the normal RegScope site: the current public
Case Selector and all six phases remain available. Only Used Car → Phase 6 uses
the local prediction API. Other cases and phases continue using their existing
public package renderers.

## Security boundaries

- Both the web gateway and prediction API bind to `127.0.0.1` on separate ports.
- The gateway serves the normal site shell and current `current-release.json`
  plus files listed by the two current public Case Package manifests. It
  verifies index→package and package→asset digests and sizes before serving.
  Synthetic UI fixtures are available only on the explicit loopback prototype
  route; arbitrary repository paths, model/schema files, CSV data, and private
  research rows are not served.
- Browser prediction requests use same-origin `/api/...`. The gateway forwards
  only the three fixed API routes to the loopback API and does not log bodies,
  URLs, or prediction values. The UI enables this route only for the CAR Phase
  6 view.
- Tailnet mode requires an exact configured `https://<device>.<tailnet>.ts.net`
  origin. No wildcard CORS, public listener, Funnel, or production setting is
  used. Tailnet membership and device access remain governed by the existing
  Tailscale ACL.
- The local Run 03 model and generated input schema stay in ignored local
  storage. They must not be copied into `web/` or committed.
- No training, Holdout/OOF access, batch prediction, or model search occurs.

## Start local web + API processes

Activate the project's Python 3.12 environment, then substitute the trusted
local Run root, locally generated schema path, and the device's exact MagicDNS
HTTPS origin. Do not put private artifact paths or the Tailnet origin in
Git-tracked files.

```sh
PYTHONPATH=python/src:. python \
  tools/modeling/serve_car_phase6_preview.py \
  --run-root <trusted-local-run-03-root> \
  --schema <ignored-local-prediction-input-schema.json> \
  --web-port 8788 --api-port 8789 \
  --tailnet-origin https://<device>.<tailnet>.ts.net
```

The process verifies the pinned model, schema, Run, configuration, and input
order before opening either listener. The API remains on loopback. Press
`Ctrl-C` in the serving terminal to stop both local listeners.

For local-only inspection, omit `--tailnet-origin` and visit:

```text
http://127.0.0.1:8788/?car-phase6-prototype=1&car-local-inference=1#phase-6
```

## Optional Tailnet HTTPS route

First inspect the actual current state:

```sh
/Applications/Tailscale.app/Contents/MacOS/Tailscale serve status
/Applications/Tailscale.app/Contents/MacOS/Tailscale funnel status
```

Only if Serve has no existing configuration and Funnel is still unconfigured,
expose the already-running loopback gateway to the tailnet:

```sh
/Applications/Tailscale.app/Contents/MacOS/Tailscale serve --bg --https=443 8788
```

If Tailscale requests tailnet-wide or administrator consent, stop here and
obtain that approval; do not use `--yes`, change ACLs, or enable Funnel. Verify
Serve status after configuring it. The API port is not mounted directly.

Open the exact configured device origin for normal Case Selector and Phase 1–6
browsing. Add the opt-in query only when local CAR Phase 6 inference is wanted:

```text
https://<device>.<tailnet>.ts.net/
https://<device>.<tailnet>.ts.net/?car-tailnet-preview=1&car-local-inference=1#phase-6
```

A second Tailnet device is needed to claim remote-client verification. A local
browser check alone does not prove another device can access the page.

## Stop Tailnet route

Stop the Python process with `Ctrl-C`, then inspect Serve status. If this task's
HTTPS root route is the only Serve configuration, remove only that route:

```sh
/Applications/Tailscale.app/Contents/MacOS/Tailscale serve --https=443 off
/Applications/Tailscale.app/Contents/MacOS/Tailscale serve status
/Applications/Tailscale.app/Contents/MacOS/Tailscale funnel status
```

Do not reset the entire Serve configuration if another route has appeared.
