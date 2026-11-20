"""Data preparation and business summaries for the Loiret road-safety dashboard."""

from __future__ import annotations

import unicodedata

import pandas as pd

DAY_NAMES = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)

REQUIRED_COLUMNS = {
    "date",
    "heure",
    "lat",
    "long",
    "vma",
    "nb_tues",
    "nb_hospitalises",
    "grave",
    "commune",
    "lum_libelle",
    "atm_libelle",
    "catr_libelle",
}


def display_label(value: object) -> str:
    """Make damaged replacement characters in source labels readable."""
    if pd.isna(value):
        return "Non renseigné"
    text = str(value).replace("\ufffd", "e").strip()
    return unicodedata.normalize("NFC", text)


def prepare_accidents(data: pd.DataFrame) -> pd.DataFrame:
    """Validate the source and add reusable, presentation-friendly columns."""
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"Colonnes requises absentes : {', '.join(sorted(missing))}")

    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        raise ValueError("La colonne date contient des dates invalides.")

    for column in ("commune", "lum_libelle", "atm_libelle", "catr_libelle"):
        frame[column] = frame[column].map(display_label)

    frame["jour_semaine"] = frame["date"].dt.day_of_week
    frame["jour_nom"] = frame["jour_semaine"].map(dict(enumerate(DAY_NAMES)))
    frame["annee"] = frame["date"].dt.year
    frame["grave"] = frame["grave"].astype(bool)
    frame["niveau_gravite"] = frame["grave"].map(
        {True: "Grave (hospitalisé ou tué)", False: "Sans hospitalisation ni décès"}
    )
    return frame


def filter_accidents(
    data: pd.DataFrame,
    first_year: int,
    last_year: int,
    communes: list[str] | None = None,
    road_types: list[str] | None = None,
) -> pd.DataFrame:
    """Apply the shared dashboard filters to every view."""
    mask = data["annee"].between(first_year, last_year)
    if communes:
        mask &= data["commune"].isin(communes)
    if road_types:
        mask &= data["catr_libelle"].isin(road_types)
    return data.loc[mask].copy()


def summarize_accidents(data: pd.DataFrame) -> dict[str, int | float]:
    total = len(data)
    severe = int(data["grave"].sum())
    return {
        "total": total,
        "graves": severe,
        "part_grave": severe / total if total else 0.0,
    }


def municipality_summary(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(
            columns=["commune", "accidents", "graves", "part_grave", "lat", "long"]
        )
    result = (
        data.groupby("commune", as_index=False)
        .agg(
            accidents=("grave", "size"),
            graves=("grave", "sum"),
            part_grave=("grave", "mean"),
            lat=("lat", "median"),
            long=("long", "median"),
        )
        .sort_values(["graves", "accidents", "commune"], ascending=[False, False, True])
    )
    return result.reset_index(drop=True)


def weekday_hour_summary(data: pd.DataFrame) -> pd.DataFrame:
    counts = (
        data.groupby(["jour_semaine", "jour_nom", "heure"], as_index=False)
        .agg(accidents_graves=("grave", "sum"), accidents=("grave", "size"))
    )
    return counts


def top_control_slots(data: pd.DataFrame, limit: int = 3) -> pd.DataFrame:
    """Rank one-hour weekly control slots by historical severe-accident count."""
    result = weekday_hour_summary(data)
    result = result.loc[result["accidents_graves"] > 0]
    return (
        result.sort_values(
            ["accidents_graves", "accidents", "jour_semaine", "heure"],
            ascending=[False, False, True, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )


def category_summary(
    data: pd.DataFrame, category: str, minimum_accidents: int = 20
) -> pd.DataFrame:
    """Compare observed severity rates while suppressing very small groups."""
    if data.empty:
        return pd.DataFrame(columns=[category, "accidents", "graves", "part_grave"])
    result = (
        data.groupby(category, as_index=False, dropna=False)
        .agg(
            accidents=("grave", "size"),
            graves=("grave", "sum"),
            part_grave=("grave", "mean"),
        )
        .query("accidents >= @minimum_accidents")
        .sort_values(["part_grave", "accidents"], ascending=[False, False])
    )
    return result.reset_index(drop=True)


def lighting_period_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Combine detailed lighting labels into night, daylight, and twilight."""
    def period(label: str) -> str:
        normalized = label.lower()
        if normalized.startswith("nuit"):
            return "Nuit (tous éclairages)"
        if normalized == "plein jour":
            return "Plein jour"
        if normalized.startswith(("crépuscule", "crepuscule")):
            return "Crépuscule / aube"
        return "Autre / non renseigné"

    frame = data.assign(periode_luminosite=data["lum_libelle"].map(period))
    return category_summary(frame, "periode_luminosite", minimum_accidents=1)
