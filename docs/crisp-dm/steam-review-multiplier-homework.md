# Steam Review Multiplier Prediction — Homework Research

**Status:** Local homework candidate. Research artifacts are generated from the named local CSV snapshots; publication review is pending. The Steam case is not in `web/data/current-release.json` and is not a Production release.

## Phase 1 — Business Understanding

### Background and purpose

Steam review counts are sometimes used as a proxy for the audience of a game. The Owner's experience-based estimate is `Estimated Ownership ≈ Review Count × 30`; K=20 and K=50 are sensitivity comparators. This study treats all three values as hypotheses and baselines. It asks whether game attributes, especially genre, help predict a game's review multiplier.

The research is a course experiment. Results are estimates from the available dataset and models and are intended for method exploration and comparison.

### Research questions

1. Do Steam genres have different typical review multipliers?
2. Do genre, platform, language, price and other game attributes support regression of K?
3. How do feature selection and regression model choices affect K prediction?
4. How does feature-based K compare with fixed K=30 when estimating the dataset's SteamSpy ownership intervals?

### Hypotheses

- **H1:** Genre groups differ in the distribution of K proxies; multi-genre titles can belong to more than one group.
- **H2:** A model using game attributes can improve holdout K-proxy error and/or ownership-interval compatibility over fixed K=30.
- **H3:** Feature selection changes model performance and the set of useful inputs.

These are tested hypotheses, not assumed outcomes.

### Quantities and formulas

- **Review Count:** `num_reviews_total`; use `positive + negative` only if that field is missing. The two measurements are profiled and not assumed equivalent.
- **Estimated Owners:** the lower and upper bounds in SteamSpy's `estimated_owners` interval.
- **K interval:** `[owners_low / review_count, owners_high / review_count]` when the review count is positive.
- **K midpoint proxy:** `((owners_low + owners_high) / 2) / review_count`. The interval midpoint is an analytical proxy, not an observed multiplier.
- **Estimated Ownership:** `review_count × predicted_K`, compared with the dataset's SteamSpy interval.
- **Actual sales:** not present and not verifiable from this dataset.

Rows with fewer than 20 reviews or a zero upper ownership bound are excluded from the primary supervised target because their ratios are uninformative or unstable. They remain in Phase 2 quality summaries.

### Data source and provenance

The local source is the Kaggle **Steam Games Dataset 2025**, by Artemiy Ermilov and three collaborators: <https://www.kaggle.com/datasets/artermiloff/steam-games-dataset> (Kaggle dataset identifier `10.34740/KAGGLE/DSV/11017460`). Kaggle describes collection via Steam store scraping and the Steam Games Scraper using Steam API and SteamSpy, gives March 2025 as the current snapshot, and labels the dataset MIT. The locally supplied snapshots are May 2024 and March 2025. `games_march2025_cleaned.csv` is described on Kaggle as excluding duplicate and playtest versions; the local full/cleaned comparison only establishes AppID subset relationships. The precise cleaning recipe for both local cleaned files is **unknown**.

### Objectives and success criteria

- Produce a traceable six-phase CRISP-DM case using the existing RegScope schemas and preview architecture.
- Reconcile source columns, target construction, features and AppID snapshots.
- Compare fixed, genre-statistical and learned models under a held-out evaluation protocol.
- Provide aggregate-only charts, metrics and a local interactive prediction preview.
- Preserve the interval nature of SteamSpy ownership and report unsuccessful or uncertain model performance as measured.

## Phase 2 — Data Understanding

Machine-readable inventory, missingness, review reconciliation, interval summaries, genre summaries and source digests are in the generated Phase 2 analysis document. The script scans the CSVs in streaming mode and retains only a compact feature frame for calculations. See `web/data/candidates/steam-review-multiplier/` for the aggregate-only case candidate.

## Phase 3 — Data Preparation

The primary supervised population uses March 2025 cleaned rows with a parseable owner interval, positive review count, at least 20 reviews, and a positive owner upper bound. The label is the log-transformed K midpoint proxy. The holdout split is a reproducible random 80/20 split of unique AppIDs (seed 42). Median imputation, scaling and any feature selection are fitted inside each training fold or on the development partition only. AppID, names, descriptions, review counts, review scores and popularity measures are excluded from model inputs.

The initial implementation listed 14 raw candidate fields, but that was a hand-curated list rather than a data-quality-ranked boundary. Incremental feature review found five further defensible sources in March 2025 Cleaned: `developers`, `publishers`, `screenshots`, `movies`, and `website`. The expanded 19-source candidate set includes only low-cardinality counts/presence derived from these fields; names, identities and URLs are not model inputs. The 22 engineered model inputs include the multi-label `genres` input, numeric and binary attributes, and derived counts. The fitted encoder excludes the raw genre-list column and emits 12 train-fold-fitted common-genre indicators alongside the 21 non-genre inputs, for 33 encoded dimensions. The 14 in SelectKBest-14 and RFE-14 are per-experiment selector settings; all-feature candidates use every encoded dimension.

## Phase 4 — Modeling

Three-fold shuffled CV (seed 42) compares OLS, Ridge, Lasso and Random Forest, plus Ridge with SelectKBest-14 and Ridge with RFE-14. Feature extraction, imputation, scaling and selection are refit within each fold. The comparison score is RMSE on `log1p(K proxy)`; selected configuration is then refit on the development partition. Fixed K=20/30/50 and genre medians learned from development data are retained as holdout baselines.

## Phase 5 — Evaluation

The reserved 20% holdout reports K-proxy MAE/RMSE/R² and the share of estimated-owner points falling inside the source intervals. Baselines use the same holdout rows. Genre summaries use multi-label membership and are reported only for groups with at least 30 holdout games. The holdout was inspected during implementation and rescored after a missing-list handling correction; no model or feature-selection choice was changed from those holdout results, but it is not a sealed preregistered test. These metrics evaluate a SteamSpy-derived proxy, not official sales.

## Phase 6 — Deployment / Presentation

The local RegScope preview loads this case only when explicitly opened with the local Steam preview flag. Its case selector, CRISP-DM stepper and Phase 1–6 pages use the generated candidate package. The K prediction endpoint binds to the private local fitted model; it is not a Production API. Package and publication statuses remain `PARTIAL` / `PENDING`.

## Reproduction

Use Python 3.12. This run used the existing main-checkout interpreter at `../AIoT-HW2-Housing-Regression/.venv/bin/python` without changing its packages. For a standalone environment, create `.venv` in this worktree and install the exact pins in `tools/steam/requirements.txt`. From the repository root, with the dataset directory supplied to `--data-dir`:

```sh
PYTHONPATH=python/src ../AIoT-HW2-Housing-Regression/.venv/bin/python -m unittest tests.research.test_steam_review_multiplier -v
PYTHONPATH=python/src ../AIoT-HW2-Housing-Regression/.venv/bin/python tools/steam/run_homework.py profile --repo-root "$PWD" --data-dir /absolute/path/to/local/datasets/steam-games-dataset --run-dir /absolute/path/to/local/steam-review-multiplier/run-01
PYTHONPATH=python/src ../AIoT-HW2-Housing-Regression/.venv/bin/python tools/steam/run_homework.py models --repo-root "$PWD" --data-dir /absolute/path/to/local/datasets/steam-games-dataset --run-dir /absolute/path/to/local/steam-review-multiplier/run-01
PYTHONPATH=python/src ../AIoT-HW2-Housing-Regression/.venv/bin/python tools/steam/run_homework.py package --repo-root "$PWD" --data-dir /absolute/path/to/local/datasets/steam-games-dataset --run-dir /absolute/path/to/local/steam-review-multiplier/run-01
PYTHONPATH=python/src ../AIoT-HW2-Housing-Regression/.venv/bin/python -m housing_regression.steam_preview_server --repo-root "$PWD" --run-dir /absolute/path/to/local/steam-review-multiplier/run-01
```

The raw dataset directory is supplied as an argument and remains read-only. Aggregate candidate package files contain no row-level records. Model and row-level holdout predictions stay under ignored `local/steam-review-multiplier/`.

## Recorded experimental result (Run 01)

The four files were streamed from the supplied local directory. Rows/columns were 87,806/46 (May 2024 Full), 83,646/46 (May 2024 Cleaned), 94,948/47 (March 2025 Full), and 89,618/47 (March 2025 Cleaned). AppIDs are unique in every file. Cleaned AppIDs are subsets of their corresponding Full files; the measured removed counts are 4,160 and 5,330. The cleaned snapshots share 74,736 AppIDs.

`num_reviews_total` differs from `positive + negative` on 83,401 of 89,618 March 2025 Cleaned rows where both are available (93.1%). The median absolute difference is 8; the 90th percentile is 134 and 99th percentile is 4,412.47. The main label therefore consistently uses `num_reviews_total` when parseable.

The K profile is restricted to rows with valid owners intervals, at least 20 reviews and owners upper bound above zero: 37,941 rows. The source has 7,904 zero-review rows and 39,109 rows with 1–19 reviews; 6,285 positive-review rows have a zero owners upper bound. These are excluded from the supervised target for the documented denominator/target-quality reasons. The main-population K proxy median is 208.3 (10th/90th percentiles 50.7/625.0). K=20, 30 and 50 fall inside the source K interval for 53.8%, 55.5% and 58.7% of rows. Descriptive median K proxies are 217.4 for Indie, 200.0 for Adventure, 216.8 for Action, 232.6 for Casual, 169.5 for Simulation and 172.0 for RPG. These intervals overlap across multi-genre groups and do not establish significant differences.

For 33,174 shared AppIDs with eligible K proxies in both snapshots, the 2024 and 2025 median proxies are 217.4 and 204.1, median absolute log-K change is 0.0606, and Spearman rank correlation is 0.925. This is a matched-snapshot description, not a future-time test. Within the main population, free games number 5,037 (median K proxy 265.2) and paid games 32,904 (median 200.0).

The 37,941 eligible March 2025 rows were split into 30,352 development and 7,589 reserved holdout rows by unique AppID (80/20, seed 42). In the original 17-input/28-encoded-feature run, all-feature Random Forest had mean three-fold CV RMSE 0.93861 on `log1p(K)`. Following the incremental five-feature expansion, the all-feature Random Forest uses 22 engineered inputs and 33 encoded dimensions and scores 0.93717. The same-fold Ridge SelectKBest-14 comparison moved from 0.99954 to 0.99509; Ridge RFE-14 moved from 0.99497 to 0.99077. The selector settings remain fixed-size comparisons, not global caps.

The added sources have good aggregate coverage in the 89,618-row March 2025 Cleaned CSV. Exact valid/missing counts, means, medians, 95th percentiles and unique-value counts are recorded as `added_feature_quality` in the generated Phase 2 audit. The inputs retain only developer/publisher counts, screenshot/movie counts and website-presence. These additions are plausible descriptive game/store attributes, not evidence of causal effects; the holdout changes below do not establish a consistent gain.

| Holdout method | K proxy MAE | K proxy RMSE | R² | Owners interval compatibility |
|---|---:|---:|---:|---:|
| Fixed K=20 | 375.83 | 1,086.70 | -0.1356 | 54.0% |
| Fixed K=30 | 366.37 | 1,083.29 | -0.1285 | 55.7% |
| Fixed K=50 | 348.94 | 1,076.70 | -0.1148 | 58.8% |
| Train-only genre median | 290.25 | 1,035.96 | -0.0320 | 51.1% |
| Random Forest K, original 17/28 | 267.40 | 1,009.94 | 0.0191 | 57.2% |
| Random Forest K, expanded 22/33 | **267.26** | 1,011.38 | 0.0163 | **57.6%** |

The expanded feature set lowered holdout proxy MAE by 0.14 but increased RMSE by 1.44, lowered R² by 0.0028 and improved interval compatibility by 0.34 percentage points. This is a small mixed result, not evidence that more inputs consistently improve generalization. The expanded model improves K-proxy MAE over K=30 by 27.1%, but its R² is close to zero and K=50 has better ownership-interval compatibility. Large errors and weak explanatory fit remain; the model is a usable course demonstration, not evidence that dynamic K is generally accurate. Random Forest impurity importance ranks price, achievements, release year, tag count and supported-language count highest; this is predictive importance, not causal effect.

Phase 5 contains the real holdout metrics and aggregate chart assets, but its Phase document status remains `PLANNED` because the existing Phase 5 schema requires an approved publication review and release ID before a phase may be marked `VERIFIED`. No such publication approval was given or inferred. Individual metric evidence is marked verified, the case package remains `PARTIAL`, and the local candidate UI can show it for homework review.

## Local preview

Run the preview server command above, then open `http://127.0.0.1:8767/web/?steam-homework-preview=1`. The query flag adds Steam to the existing Case Selector only on loopback. The server exposes the fitted model through a same-origin local endpoint and refuses non-loopback binds. The preview does not alter `web/data/current-release.json`.
