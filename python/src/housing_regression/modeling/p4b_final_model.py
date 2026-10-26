"""Serializable final Development model: Phase 3 preprocessing plus selected OLS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from housing_regression.data_prep import AmesDataPreparationPipeline, TARGET_COLUMN


@dataclass
class FinalP4BDevelopmentModel:
    """Fitted preprocessing and Primary OLS model with a prediction interface."""

    preprocessing_pipeline: AmesDataPreparationPipeline
    selected_feature_names: tuple[str, ...]
    ols_coefficients: np.ndarray
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.preprocessing_pipeline.is_fitted:
            raise ValueError("Final model requires a fitted Phase 3 preprocessing pipeline.")
        if not self.selected_feature_names:
            raise ValueError("Final model requires at least one selected feature.")
        if len(set(self.selected_feature_names)) != len(self.selected_feature_names):
            raise ValueError("Selected feature names must be unique.")
        if self.ols_coefficients.ndim != 1 or len(self.ols_coefficients) != len(self.selected_feature_names) + 1:
            raise ValueError("OLS coefficient vector must contain intercept and one weight per feature.")
        if not np.isfinite(self.ols_coefficients).all():
            raise ValueError("OLS coefficients must be finite.")

    def predict(self, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
        """Transform prediction rows and return SalePrice predictions in selected order."""
        if any(TARGET_COLUMN in row for row in rows):
            raise ValueError("Prediction rows must not contain the SalePrice target.")
        transformed = self.preprocessing_pipeline.transform(rows, split_name="final_model_predict")
        names = list(transformed.feature_names)
        name_to_index = {name: index for index, name in enumerate(names)}
        missing = [name for name in self.selected_feature_names if name not in name_to_index]
        if missing:
            raise ValueError("Fitted preprocessing output is missing selected model features.")
        indices = [name_to_index[name] for name in self.selected_feature_names]
        matrix = transformed.to_numpy()[:, indices]
        return self.ols_coefficients[0] + matrix @ self.ols_coefficients[1:]
