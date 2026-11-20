from __future__ import annotations

import pandas as pd

from backend.data import (
    filter_accidents,
    lighting_period_summary,
    prepare_accidents,
    summarize_accidents,
    top_control_slots,
)


def sample_accidents() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2023-01-02", "2023-01-02", "2024-01-05", "2024-01-06"]
            ),
            "heure": [17, 17, 8, 8],
            "lat": [47.9, 47.9, 47.8, 47.8],
            "long": [2.0, 2.0, 2.1, 2.1],
            "vma": [50, 50, 80, 80],
            "nb_tues": [0, 0, 0, 1],
            "nb_hospitalises": [0, 1, 0, 0],
            "grave": [False, True, False, True],
            "commune": ["Orl�ans", "Orl�ans", "Gien", "Gien"],
            "lum_libelle": ["Plein jour"] * 4,
            "atm_libelle": ["Normale"] * 4,
            "catr_libelle": ["Voie communale", "Voie communale", "Autoroute", "Autoroute"],
        }
    )


def test_prepare_repairs_labels_and_derives_weekday() -> None:
    prepared = prepare_accidents(sample_accidents())
    assert prepared.loc[0, "commune"] == "Orleans"
    assert prepared.loc[0, "jour_nom"] == "Lundi"
    assert prepared.loc[3, "niveau_gravite"] == "Grave (hospitalisé ou tué)"


def test_shared_filters_and_kpis_use_the_same_rows() -> None:
    prepared = prepare_accidents(sample_accidents())
    filtered = filter_accidents(prepared, 2024, 2024, ["Gien"], ["Autoroute"])
    assert len(filtered) == 2
    assert summarize_accidents(filtered) == {
        "total": 2,
        "graves": 1,
        "part_grave": 0.5,
    }


def test_control_slots_rank_observed_grave_cases() -> None:
    prepared = prepare_accidents(sample_accidents())
    slots = top_control_slots(prepared, limit=3)
    assert slots.iloc[0]["jour_nom"] == "Lundi"
    assert slots.iloc[0]["heure"] == 17
    assert slots.iloc[0]["accidents_graves"] == 1


def test_lighting_summary_compares_night_and_day_with_counts() -> None:
    data = sample_accidents()
    data.loc[2:, "lum_libelle"] = "Nuit sans éclairage"
    summary = lighting_period_summary(prepare_accidents(data)).set_index(
        "periode_luminosite"
    )
    assert summary.loc["Plein jour", "accidents"] == 2
    assert summary.loc["Nuit (tous éclairages)", "accidents"] == 2
    assert summary.loc["Nuit (tous éclairages)", "part_grave"] == 0.5
