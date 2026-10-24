"""Deterministic train/validation splitting for labeled dataset."""

from __future__ import annotations

import random
from typing import Any, Mapping


def split_labeled_dataset(
    rows: list[dict[str, Any]],
    val_fraction: float = 0.2,
    random_state: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Perform deterministic train/validation split on labeled Ames records.

    Args:
        rows: Complete labeled training records (1,460 rows).
        val_fraction: Fraction allocated to internal validation (default 0.2).
        random_state: Integer seed for reproducible random permutation.

    Returns:
        (train_rows, val_rows): 80% train (1,168 rows) and 20% validation (292 rows).
    """
    if not rows:
        raise ValueError("Cannot split an empty dataset.")
    if not 0.0 < val_fraction < 1.0:
        raise ValueError(f"val_fraction must be in (0, 1), got {val_fraction}")

    n_total = len(rows)
    n_train = int(round(n_total * (1.0 - val_fraction)))
    n_val = n_total - n_train

    # Deterministic permutation using isolated Random instance
    rng = random.Random(random_state)
    indices = list(range(n_total))
    shuffled = indices[:]
    rng.shuffle(shuffled)

    train_indices = set(shuffled[:n_train])
    val_indices = set(shuffled[n_train:])

    assert len(train_indices) == n_train, "Train split size mismatch"
    assert len(val_indices) == n_val, "Validation split size mismatch"
    assert len(train_indices & val_indices) == 0, "Data leakage: train and val overlap"

    # Retain natural index sequence within each split for stable reproducibility
    train_rows = [rows[i] for i in sorted(train_indices)]
    val_rows = [rows[i] for i in sorted(val_indices)]

    return train_rows, val_rows
