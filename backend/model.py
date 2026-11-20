"""Leakage-conscious severity model and chronological holdout evaluation."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from backend.data import display_label

NUMERIC_FEATURES = ["mois", "heure", "jour_semaine", "lat", "long", "vma"]
CATEGORICAL_FEATURES = ["lum_libelle", "atm_libelle", "catr_libelle"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_feature_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Keep only conditions that can be known before an accident occurs."""
    missing = set(MODEL_FEATURES).difference(data.columns)
    if missing:
        raise ValueError(f"Variables du modèle absentes : {', '.join(sorted(missing))}")

    features = data.loc[:, MODEL_FEATURES].copy()
    for column in CATEGORICAL_FEATURES:
        features[column] = features[column].map(display_label)
    return features


def _new_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("impute", SimpleImputer(strategy="constant", fill_value="Non renseigné")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=8,
        max_features=0.75,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def train_and_evaluate(data: pd.DataFrame) -> tuple[Pipeline, dict[str, Any]]:
    """Evaluate on the latest complete year, then refit the deployable model."""
    if data.empty:
        raise ValueError("Impossible d'entraîner le modèle : le jeu de données est vide.")

    latest_year = int(data["annee"].max())
    train_mask = data["annee"] < latest_year
    test_mask = data["annee"] == latest_year
    if not train_mask.any() or not test_mask.any():
        raise ValueError("Il faut au moins deux années pour évaluer le modèle dans le temps.")

    train_features = build_feature_frame(data.loc[train_mask])
    test_features = build_feature_frame(data.loc[test_mask])
    train_target = data.loc[train_mask, "grave"].astype(bool)
    test_target = data.loc[test_mask, "grave"].astype(bool)
    if train_target.nunique() != 2 or test_target.nunique() != 2:
        raise ValueError("L'apprentissage et l'année de test doivent contenir les deux classes.")

    evaluation_model = _new_pipeline()
    evaluation_model.fit(train_features, train_target)
    probabilities = evaluation_model.predict_proba(test_features)[:, 1]
    predictions = probabilities >= 0.5

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(train_features, train_target)
    baseline_predictions = baseline.predict(test_features)

    metrics: dict[str, Any] = {
        "annee_test": latest_year,
        "n_apprentissage": int(train_mask.sum()),
        "n_test": int(test_mask.sum()),
        "auc": float(roc_auc_score(test_target, probabilities)),
        "exactitude": float(accuracy_score(test_target, predictions)),
        "precision": float(precision_score(test_target, predictions, zero_division=0)),
        "rappel": float(recall_score(test_target, predictions, zero_division=0)),
        "f1": float(f1_score(test_target, predictions, zero_division=0)),
        "exactitude_baseline": float(accuracy_score(test_target, baseline_predictions)),
    }

    deployed_model = _new_pipeline()
    deployed_model.fit(build_feature_frame(data), data["grave"].astype(bool))
    return deployed_model, metrics


def score_scenario(model: Pipeline, scenario: pd.DataFrame) -> float:
    """Return the model score for one pre-accident scenario."""
    features = build_feature_frame(scenario)
    return float(model.predict_proba(features)[0, 1])
