from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from backend.data import (
    category_summary,
    filter_accidents,
    lighting_period_summary,
    municipality_summary,
    prepare_accidents,
    summarize_accidents,
    top_control_slots,
    weekday_hour_summary,
)
from backend.model import score_scenario, train_and_evaluate

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DEFAULT_DATA_PATH = ROOT / "data" / "securite_routiere.parquet"
DATA_PATH = Path(os.getenv("BAAC_DATA_PATH", str(DEFAULT_DATA_PATH))).expanduser()

app = FastAPI(
    title="Vigie Loiret API",
    description="Données et indicateurs de sécurité routière pour l'interface Streamlit.",
    version="1.0.0",
)


class ScenarioInput(BaseModel):
    mois: int = Field(ge=1, le=12)
    heure: int = Field(ge=0, le=23)
    jour_semaine: int = Field(ge=0, le=6)
    lat: float = Field(ge=-90, le=90)
    long: float = Field(ge=-180, le=180)
    vma: int = Field(ge=0, le=130)
    lum_libelle: str
    atm_libelle: str
    catr_libelle: str


@lru_cache(maxsize=1)
def load_accidents() -> pd.DataFrame:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Fichier de données introuvable : {DATA_PATH}")
    return prepare_accidents(pd.read_parquet(DATA_PATH))


@lru_cache(maxsize=1)
def load_model() -> tuple[Any, dict[str, Any]]:
    return train_and_evaluate(load_accidents())


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", date_format="iso", force_ascii=False))


def _options(data: pd.DataFrame) -> dict[str, Any]:
    return {
        "years": sorted(int(value) for value in data["annee"].unique()),
        "communes": sorted(data["commune"].dropna().unique().tolist()),
        "roads": sorted(data["catr_libelle"].dropna().unique().tolist()),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/options")
def options() -> dict[str, Any]:
    return _options(load_accidents())


@app.get("/dashboard")
def dashboard(
    first_year: int | None = None,
    last_year: int | None = None,
    communes: Annotated[list[str] | None, Query()] = None,
    road_types: Annotated[list[str] | None, Query()] = None,
) -> dict[str, Any]:
    data = load_accidents()
    years = sorted(int(value) for value in data["annee"].unique())
    filtered = filter_accidents(
        data,
        first_year=first_year if first_year is not None else years[0],
        last_year=last_year if last_year is not None else years[-1],
        communes=communes,
        road_types=road_types,
    )
    return {
        "records": _records(filtered),
        "summary": summarize_accidents(filtered),
        "municipalities": _records(municipality_summary(filtered)),
        "control_slots": _records(top_control_slots(filtered, limit=3)),
        "weekday_hours": _records(weekday_hour_summary(filtered)),
        "weather": _records(category_summary(filtered, "atm_libelle")),
        "lighting": _records(lighting_period_summary(filtered)),
        "roads": _records(category_summary(filtered, "catr_libelle")),
    }


@app.post("/scenario")
def scenario(request: ScenarioInput) -> dict[str, Any]:
    model, metrics = load_model()
    score = score_scenario(model, pd.DataFrame([request.model_dump()]))
    return {"score": score, "metrics": metrics}
