"""Offline import smoke test for the pinned experiment environment."""

from __future__ import annotations

import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"Unsupported Python {sys.version_info.major}.{sys.version_info.minor}; "
        "this environment targets Python 3.12.x."
    )

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import statsmodels
import statsmodels.api as sm


def main() -> int:
    print(f"Python {sys.version.split()[0]}")
    for name, version in (
        ("NumPy", np.__version__),
        ("pandas", pd.__version__),
        ("scikit-learn", sklearn.__version__),
        ("statsmodels", statsmodels.__version__),
        ("matplotlib", matplotlib.__version__),
    ):
        print(f"{name} {version}")
    print(f"matplotlib backend {matplotlib.get_backend()}")
    plt.close("all")
    print("Experiment environment imports passed; no model was trained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
