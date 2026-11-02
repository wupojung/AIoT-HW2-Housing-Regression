"""Minimal compatibility class required by the pinned Steam Run 01 artifact."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


CASE_ID = "steam-review-multiplier"
MODEL_INPUT_FIELDS = (
    "genres", "price", "required_age", "dlc_count", "achievements", "release_year",
    "windows", "mac", "linux", "genre_count", "category_count", "tag_count",
    "supported_language_count", "full_audio_language_count", "has_english",
    "has_traditional_chinese", "discount", "developer_count", "publisher_count",
    "screenshot_count", "movie_count", "has_website",
)


class SteamFeatureEncoder(BaseEstimator, TransformerMixin):
    """The fitted encoder implementation used by the serialized Run 01 model."""

    base_columns = [field for field in MODEL_INPUT_FIELDS if field != "genres"]

    def __init__(self, max_genres: int = 12):
        self.max_genres = max_genres

    def fit(self, X, y=None):
        counts = Counter(
            genre
            for values in X["genres"]
            for genre in (values if isinstance(values, list) else [])
        )
        self.genre_vocabulary_ = [name for name, _ in counts.most_common(self.max_genres)]
        return self

    def transform(self, X):
        result = np.empty((len(X), len(self.base_columns) + len(self.genre_vocabulary_)), dtype=float)
        for index, column in enumerate(self.base_columns):
            result[:, index] = pd.to_numeric(X[column], errors="coerce").to_numpy(dtype=float)
        offset = len(self.base_columns)
        vocabulary = self.genre_vocabulary_
        for row_index, values in enumerate(X["genres"]):
            genres = set(values if isinstance(values, list) else [])
            for genre_index, genre in enumerate(vocabulary):
                result[row_index, offset + genre_index] = float(genre in genres)
        return result

    def get_feature_names_out(self, input_features=None):
        return np.asarray(
            self.base_columns + [f"genre::{genre}" for genre in self.genre_vocabulary_],
            dtype=object,
        )
