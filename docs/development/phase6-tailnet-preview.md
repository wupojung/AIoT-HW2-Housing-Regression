# CAR Phase 6 Tailnet Preview (Local Experiment)

This opt-in preview binds a second web gateway directly to one verified local
Tailscale IPv4 address. It does not use Tailscale Serve/Funnel, add a firewall
rule, or create a public API. The gateway still serves the normal RegScope
Case Selector and all six package-backed phases. Only the explicit CAR Phase 6
inference route uses the local Run 03 model. The model has negative Development
R² and performs below its Dummy baseline; inference is not a claim of useful
predictive quality.

## Security boundaries

- The existing local preview binds to `127.0.0.1:8788`; the optional second web
  listener binds only to the explicitly selected Tailscale IPv4 at port 8788.
  Startup verifies that address using the installed Tailscale CLI and rejects
  wildcard, LAN, public, missing, or unassigned addresses.
- The prediction API/model runtime remains bound to `127.0.0.1:8789`.
- The direct-IP web listener requires HTTP Basic authentication. It creates a
  random token in ignored `local/phase6-tailnet-preview/auth-token.txt` with
  owner-only permissions. The token is never printed or logged. The username
  is `regscope`.
- Direct-IP HTTP is intended only over the encrypted Tailscale network. Do not
  expose the address through a router, reverse proxy, public tunnel, or
  non-Tailnet interface. The gateway also checks the exact Host and Origin.
- Browser requests use same-origin `/api/...`. The authenticated gateway
  forwards only `/api/health`, `/api/schema`, and `/api/predict` to loopback.
  Request URLs, credentials, bodies, and predictions are not logged.
- The site gateway serves the current release index and only files listed by
  the two current public Case Package manifests, verifying hashes and sizes.
  Synthetic fixtures are available only on the loopback prototype route.
  Arbitrary repository paths, model/schema files, CSV data, and private rows
  are not served.
- No training, Holdout/OOF access, batch prediction, or model search occurs.

## Start the local and optional direct-IP previews

Activate the project Python 3.12 environment and provide the trusted local Run
root and locally generated Prediction Input Schema. Never commit those private
paths or the authentication token.

```sh
PYTHONPATH=python/src:. python \
  tools/modeling/serve_car_phase6_preview.py \
  --run-root <trusted-local-run-03-root> \
  --schema <ignored-local-prediction-input-schema.json> \
  --web-port 8788 --api-port 8789
```

This starts the loopback preview and API. To additionally bind the web gateway
to the verified Tailscale IPv4, explicitly pass the address shown by
`tailscale ip -4` (the server runs this check again before binding):

```sh
PYTHONPATH=python/src:. python \
  tools/modeling/serve_car_phase6_preview.py \
  --run-root <trusted-local-run-03-root> \
  --schema <ignored-local-prediction-input-schema.json> \
  --web-port 8788 --api-port 8789 --tailnet-ip <verified-tailscale-ipv4>
```

The server keeps the loopback preview at `http://127.0.0.1:8788/` and opens a
second listener at `http://<verified-tailscale-ipv4>:8788/`. The direct-IP
listener prompts for Basic credentials. Retrieve the ignored token over the
existing authenticated SSH connection, for example:

```sh
scp -p <ssh-user>@<verified-tailscale-ip>:<repository-root>/local/phase6-tailnet-preview/auth-token.txt <private-local-path>
chmod 600 <private-local-path>
```

Enter the token in the browser's Basic-auth prompt with username `regscope`.
Do not paste it into chat, a PR, or an Issue. The source token file is
owner-only and remains local on this Mac.

Open the normal direct-IP URL to browse the Case Selector and Phases 1–6. To
opt in to real local CAR Phase 6 inference, add:

```text
?car-tailnet-preview=1&car-local-inference=1#phase-6
```

Only CAR Phase 6 makes prediction requests. Other cases/phases remain on their
verified public Case Packages. The API port is never exposed on the Tailscale
interface. Stop both web listeners and the API with Ctrl-C in the serving
terminal. No Serve/Funnel or firewall configuration is part of this workflow.

## Verification limits

A successful local-IP request proves only that the local device served the
preview. A second device on the same Tailnet is required to verify remote
access. Do not claim second-device verification until it has actually been
performed.
