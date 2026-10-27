# Python Experiment Environment

This lightweight environment prepares later experiments; it does not implement EDA or train models. It uses CPython 3.12.x. The current Windows verification uses CPython 3.12.10. CI uses the latest available Python 3.12 patch through `actions/setup-python`.

`requirements.in` lists the direct dependencies. `requirements.lock` pins the resolved dependency graph, including packages needed by the existing research-collector tests. Install the lock file for routine work; do not install from `requirements.in` directly unless refreshing the lock.

| Package | Version |
| --- | --- |
| NumPy | 2.5.4 |
| pandas | 3.1.0 |
| scikit-learn | 1.9.1 |
| statsmodels | 0.15.0 |
| Matplotlib | 3.11.2 |
| pytest | 9.1.1 |
| PyYAML (existing collector tests) | 6.0.3 |

## Windows (PowerShell)

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip==26.2.2
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe python/src/environment_check.py
.\.venv\Scripts\python.exe -m pytest -q
```

These commands do not require PowerShell script activation and do not assume WSL.

## macOS and Linux

From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip==26.2.2
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python python/src/environment_check.py
.venv/bin/python -m pytest -q
```

## Verify and maintain the environment

`python/src/environment_check.py` imports NumPy, pandas, scikit-learn, statsmodels, and Matplotlib, reports their versions, and exits without contacting a service or opening a dataset. After dependencies are installed, this smoke test and the test suite run offline.

The synthetic-data tests exercise NumPy/Pandas values, scikit-learn data splitting, a statsmodels design matrix, and a Matplotlib Agg render. They do not fit a model or report empirical results.

To refresh dependencies, update the exact direct pins in `requirements.in`, resolve them in a clean Python 3.12 environment using pip 26.2.2, and regenerate `requirements.lock` from that environment's `python -m pip freeze` output. Run the smoke test and complete test suite before committing the new lock.

## Data boundary and handoff

The setup and tests need no Kaggle dataset, paper, credentials, or NotebookLM file. Keep future raw CSVs and private experiment artifacts under ignored `local/datasets/` or `local/scratch/`. Never add them to fixtures, test output, or `python/src/`.

W1P1 can reuse this environment when later CRISP-DM work needs local experiments. This scaffold is cross-cutting infrastructure; it does not complete or revise Issue #5 or claim any CRISP-DM phase.
