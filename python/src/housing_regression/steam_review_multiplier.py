"""Trusted pickle import path for the private Steam Run 01 model.

This deploy-only compatibility module intentionally exposes the encoder under
the exact module and class name recorded in the fitted artifact. Training and
research runners remain in the main branch and are not part of this module.
"""

from .steam_model_compat import CASE_ID, MODEL_INPUT_FIELDS, SteamFeatureEncoder


def log_to_k(values):
    import numpy as np

    return np.maximum(0.0, np.expm1(np.asarray(values, dtype=float)))
