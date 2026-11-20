from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.data import prepare_accidents
from backend.model import MODEL_FEATURES, build_feature_frame, train_and_evaluate

ROOT = Path(__file__).resolve().parents[1]


def test_model_excludes_outcomes_and_evaluates_on_latest_year() -> None:
    data = prepare_accidents(pd.read_parquet(ROOT / "data" / "securite_routiere.parquet"))
    features = build_feature_frame(data)
    assert list(features.columns) == MODEL_FEATURES
    assert not {"grave", "nb_tues", "nb_hospitalises", "nb_usagers"}.intersection(features.columns)

    model, metrics = train_and_evaluate(data)
    assert metrics["annee_test"] == 2025
    assert metrics["n_test"] == 413
    assert metrics["auc"] > 0.6
    assert 0 <= model.predict_proba(features.iloc[[0]])[0, 1] <= 1
