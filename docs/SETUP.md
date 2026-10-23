# Developer Setup

This guide covers optional WSL workflow and security-hook setup. The experiment environment supports Windows, macOS, and Linux without WSL; follow [Python Experiment Environment](../python/README.md) for its versioned installation instructions. Keep account credentials and personal agent configuration outside the repository.

## Open the project in WSL

From a WSL terminal, enter the repository checkout. For a Windows checkout on drive `D:`, WSL normally mounts it under `/mnt/d`:

```bash
cd /mnt/d/path/to/AIoT-HW2-Housing-Regression
pwd
git status --short --branch
```

Use a `feature/*` branch for changes and submit a pull request to `main`. Reserve `deploy` for reviewed production releases.

## Optional WSL tooling

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r tools/research_collector/requirements.txt
python -m pip install pre-commit
pre-commit install
```

The installed pre-commit hook scans staged/tracked files when you commit. Run the tests before opening a pull request; GitHub Actions scans the pull request once.

```bash
python -m unittest discover -s tests/security -v
```

Use `python tools/security_scan.py --all` for an initial release audit or if you bypassed the hook, not for every routine change.

## Data boundary

Keep papers, raw datasets, credentials, private notes, and NotebookLM import files in the ignored `local/` directory. Do not add local files to build inputs. Read the [Security and Data Policy](SECURITY_AND_DATA_POLICY.md) before changing deployment configuration.
