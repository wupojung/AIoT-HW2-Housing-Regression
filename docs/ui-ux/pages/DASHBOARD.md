# Dashboard — Separate Route / Design Proposal

**PARTIAL, not engineering-ready.** Two mutually exclusive modes. The older design is retained as reference only; precise layout to be independently reviewed.

## ASCII wireframe — DASHBOARD (separate route)

~~~text
+--------------------------------------------------------------------------------+
| RegScope                                     [< Back to CRISP-DM Home]          |
+--------------------------------------------------------------------------------+
| Dashboard — integrated regression analysis                                    |
| Problem [Preset 1 / Preset 2 v]  OR Dataset [CSV upload / direct URL input]    |
| Target [select]  Features [select]  [Validate] [Run if supported]              |
| [Load status, errors and supported/unsupported notices]                        |
| +----------------------+----------------------+---------------------------+    |
| | Dataset overview     | Feature selection    | Metrics                   |    |
| +----------------------+----------------------+---------------------------+    |
| | Prediction visual / verified CI or PI when justified; else unavailable  |    |
| +--------------------------------------------------------------------------+    |
| | Reproducibility, provenance, limits, run status                           |    |
| +--------------------------------------------------------------------------+    |
+--------------------------------------------------------------------------------+
~~~

## Deterministic pending-state UX
```text
DASHBOARD   Mode [Verified Research*] [Custom Dataset]
VERIFIED ONLY:
 [Study case select] [approved execution/config selection]
 [Dataset overview] [Feature-selection summary] [Metrics/provenance]
 [Prediction illustration only if separately approved]
 [NO APPROVED RESULTS → unavailable in the same cards]
CUSTOM ONLY:
 [Upload CSV] or [Direct HTTP(S) URL]
 [Parse/preview feedback and source filename]
 [Target select] [Features multi-select] [Validate]
 [Run: DISABLED until explicitly authorized]
 [Errors: file/URL/schema/size/network, reset on input change]
```
The modes must NEVER share stale results or suggest custom datasets are audited research cases. Full desktop visual reference and interaction detail remain outstanding.