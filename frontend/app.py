from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DAY_NAMES = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)
MONTH_NAMES = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]
COLORS = {
    "background": "#0b1220",
    "panel": "#121d2e",
    "teal": "#0072b2",
    "coral": "#d55e00",
    "blue": "#56b4e9",
    "boundary": "#b45309",
    "muted": "#a7b3c5",
}
MAP_INITIAL_ZOOM = 6.8
HOVER_STYLE = {
    "bgcolor": "#102033",
    "bordercolor": "#00a8e8",
    "font": {"family": "Inter, sans-serif", "size": 13, "color": "#f3f6fb"},
    "align": "left",
}


def fetch_api(path: str, params: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    try:
        response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(
            f"Impossible de joindre l'API FastAPI ({API_BASE_URL}). "
            "Vérifiez que le service backend est démarré et que API_BASE_URL est correct."
        )
        st.stop()
        raise RuntimeError("Requête à l'API impossible.") from exc
    return response.json()


def post_api(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(
            f"{API_BASE_URL}{path}", json=payload, timeout=120
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(
            f"La requête vers l'API FastAPI a échoué ({API_BASE_URL}{path}). "
            "Vérifiez le service backend et ses journaux."
        )
        st.stop()
        raise RuntimeError("Requête à l'API impossible.") from exc
    return response.json()


st.set_page_config(
    page_title="Vigie Loiret · Sécurité routière",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #f3f6fb;
        --muted: #a7b3c5;
        --panel: #121d2e;
        --line: rgba(167, 179, 197, .16);
        --mint: #5fe1c2;
        --map-boundary: #b45309;
    }
    .stApp { background: #0b1220; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(11, 18, 32, .88); }
    [data-testid="stSidebar"] {
        background: #0e1828;
        border-right: 1px solid var(--line);
    }
    [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 18px 20px;
        border-radius: 14px;
    }
    [data-testid="stMetricLabel"] p { color: var(--muted); font-size: .88rem; }
    [data-testid="stMetricValue"] { color: var(--ink); }
    .eyebrow {
        color: var(--mint); font-weight: 700; font-size: .76rem;
        letter-spacing: .12em; text-transform: uppercase;
    }
    .hero {
        padding: 8px 0 14px 0;
        border-bottom: 1px solid var(--line);
        margin-bottom: 20px;
    }
    .hero h1 { margin: 4px 0 8px; letter-spacing: -.035em; }
    .hero p { color: var(--muted); max-width: 900px; margin-bottom: 0; }
    .note {
        border-left: 3px solid var(--mint); background: var(--panel);
        padding: 12px 16px; border-radius: 0 10px 10px 0;
        color: var(--muted); font-size: .92rem;
    }
    .map-legend {
        display: flex; flex-wrap: wrap; align-items: center;
        gap: .45rem 1rem; margin: 0 0 .45rem;
        color: #d5deeb; font-size: .78rem;
    }
    .map-legend span { display: inline-flex; align-items: center; gap: .4rem; }
    .map-legend-dot {
        display: inline-block; width: .58rem; height: .58rem;
        border-radius: 50%; box-shadow: 0 0 0 2px var(--panel);
    }
    .map-legend-severe { background: #d55e00; width: .75rem; height: .75rem; }
    .map-legend-other { background: #0072b2; }
    .map-legend-line {
        display: inline-block; width: 1rem;
        border-top: 2px solid var(--map-boundary);
    }
    @keyframes tooltip-arrive {
        from { opacity: 0; filter: drop-shadow(0 0 0 rgba(0, 168, 232, 0)); }
        to { opacity: 1; filter: drop-shadow(0 0 7px rgba(0, 168, 232, .42)); }
    }
    .js-plotly-plot .hoverlayer .hovertext {
        animation: tooltip-arrive .2s ease-out;
    }
    div[data-testid="stTabs"] button { font-weight: 650; }
    @media (max-width: 640px) {
        [data-testid="stMetric"] { padding: 12px; }
        .hero h1 { font-size: 1.8rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        .js-plotly-plot .hoverlayer .hovertext { animation: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Chargement des filtres depuis l'API…")
def load_options() -> dict[str, Any]:
    return fetch_api("/options")


@st.cache_data(show_spinner="Chargement des données depuis l'API…")
def load_dashboard(
    first_year: int,
    last_year: int,
    communes: tuple[str, ...],
    roads: tuple[str, ...],
) -> dict[str, Any]:
    params = [("first_year", str(first_year)), ("last_year", str(last_year))]
    params.extend(("communes", value) for value in communes)
    params.extend(("road_types", value) for value in roads)
    return fetch_api("/dashboard", params=params)


@st.cache_data(show_spinner="Évaluation du scénario par l'API…")
def score_remote_scenario(payload: tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "mois",
        "heure",
        "jour_semaine",
        "lat",
        "long",
        "vma",
        "lum_libelle",
        "atm_libelle",
        "catr_libelle",
    )
    return post_api("/scenario", dict(zip(keys, payload, strict=True)))


def plotly_layout(figure: go.Figure, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=48, b=14),
        paper_bgcolor=COLORS["panel"],
        plot_bgcolor=COLORS["panel"],
        font=dict(color="#e7edf5", family="Inter, sans-serif", size=13),
        title=dict(font=dict(size=16)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hoverlabel=HOVER_STYLE,
    )
    figure.update_traces(hoverlabel=HOVER_STYLE)
    figure.update_xaxes(
        gridcolor="rgba(167, 179, 197, .13)",
        zerolinecolor="rgba(167, 179, 197, .18)",
        automargin=True,
    )
    figure.update_yaxes(
        gridcolor="rgba(167, 179, 197, .13)",
        zerolinecolor="rgba(167, 179, 197, .18)",
        automargin=True,
    )
    return figure


@st.cache_data
def load_map_boundary() -> dict[str, Any]:
    boundary_path = Path(__file__).parent / "data" / "loiret-boundary.geojson"
    return json.loads(boundary_path.read_text(encoding="utf-8"))


def render_overview(data: pd.DataFrame, municipality_data: pd.DataFrame) -> None:
    map_data = data.copy()
    map_data["niveau"] = map_data["grave"].map(
        {True: "Grave", False: "Sans hospitalisation ni décès"}
    )
    map_data["date_affichee"] = (
        pd.to_datetime(map_data["date"], errors="coerce")
        .dt.strftime("%d/%m/%Y")
        .fillna("Non renseignée")
    )
    map_data["heure_affichee"] = pd.to_numeric(
        map_data["heure"], errors="coerce"
    ).map(lambda value: f"{int(value):02d} h" if pd.notna(value) else "Non renseignée")
    for column in ("catr_libelle", "lum_libelle", "atm_libelle"):
        map_data[column] = map_data[column].fillna("Non renseigné")

    boundary = load_map_boundary()
    west, south, east, north = boundary["bbox"]
    center = {"lat": (south + north) / 2, "lon": (west + east) / 2}
    boundary_geometry = boundary["features"][0]["geometry"]
    polygons = (
        boundary_geometry["coordinates"]
        if boundary_geometry["type"] == "MultiPolygon"
        else [boundary_geometry["coordinates"]]
    )
    boundary_lat: list[float | None] = []
    boundary_lon: list[float | None] = []
    for polygon in polygons:
        for ring in polygon:
            boundary_lon.extend(point[0] for point in ring)
            boundary_lat.extend(point[1] for point in ring)
            boundary_lon.append(None)
            boundary_lat.append(None)

    map_figure = go.Figure(
        go.Scattermap(
            lat=map_data["lat"],
            lon=map_data["long"],
            mode="markers",
            marker={
                "size": map_data["grave"].map({True: 11, False: 7}),
                "color": map_data["grave"].map(
                    {True: COLORS["coral"], False: COLORS["teal"]}
                ),
                "opacity": 0.8,
            },
            customdata=map_data[
                [
                    "commune",
                    "niveau",
                    "date_affichee",
                    "heure_affichee",
                    "catr_libelle",
                    "lum_libelle",
                    "atm_libelle",
                ]
            ].to_numpy(),
            cluster={
                "enabled": True,
                "maxzoom": 13,
                "color": "#174d63",
            },
            selected={"marker": {"size": 17, "opacity": 1}},
            unselected={"marker": {"opacity": 0.38}},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br><br>"
                "<b>Gravité :</b> %{customdata[1]}<br>"
                "<b>Date :</b> %{customdata[2]}<br>"
                "<b>Heure :</b> %{customdata[3]}<br>"
                "<b>Route :</b> %{customdata[4]}<br>"
                "<b>Luminosité :</b> %{customdata[5]}<br>"
                "<b>Météo :</b> %{customdata[6]}"
                "<extra></extra>"
            ),
            hoverlabel=HOVER_STYLE,
            name="Accidents",
        )
    )
    map_figure.update_layout(
        map={
            "style": "carto-positron",
            "center": center,
            "zoom": MAP_INITIAL_ZOOM,
        }
    )
    selection_state = st.session_state.get("accident_map", {})
    selection = (
        selection_state.get("selection", {})
        if isinstance(selection_state, dict)
        else getattr(selection_state, "selection", {})
    )
    selected_points = (
        selection.get("points", [])
        if isinstance(selection, dict)
        else getattr(selection, "points", [])
    )
    for point in selected_points:
        if not isinstance(point, dict):
            continue
        latitude = point.get("lat")
        longitude = point.get("lon")
        if latitude is None or longitude is None:
            continue
        map_figure.add_trace(
            go.Scattermap(
                lat=[latitude],
                lon=[longitude],
                mode="markers",
                marker={
                    "size": 26,
                    "color": "rgba(0, 168, 232, 0.35)",
                    "symbol": "circle",
                },
                hoverinfo="skip",
                showlegend=False,
                name="Point sélectionné",
            )
        )
    map_figure.add_trace(
        go.Scattermap(
            lat=boundary_lat,
            lon=boundary_lon,
            mode="lines",
            line={"color": COLORS["boundary"], "width": 2.5},
            hoverinfo="skip",
            showlegend=False,
            name="Contour du Loiret",
        )
    )
    map_figure.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=COLORS["panel"],
        font=dict(color="#e7edf5"),
        showlegend=False,
        map={"center": center, "zoom": MAP_INITIAL_ZOOM, "bearing": 0, "pitch": 0},
        transition={"duration": 260, "easing": "cubic-out"},
        uirevision="accidents-map",
    )

    cities = municipality_data.head(12).sort_values("graves")
    city_figure = px.bar(
        cities,
        x="graves",
        y="commune",
        orientation="h",
        text="graves",
        color="graves",
        color_continuous_scale="cividis",
        title=(
            f"{municipality_data.iloc[0]['commune']} : "
            f"{int(municipality_data.iloc[0]['graves'])} accidents graves "
            f"({int(municipality_data.iloc[0]['accidents'])} accidents)"
        ),
        labels={"graves": "Accidents graves", "commune": ""},
    )
    city_figure.update_layout(coloraxis_showscale=False)
    city_figure.update_traces(
        textposition="outside",
        cliponaxis=False,
        customdata=cities[["accidents", "part_grave"]].to_numpy(),
        hovertemplate=(
            "<b>%{y}</b><br>Accidents graves : %{x:.0f}<br>"
            "Tous accidents : %{customdata[0]:.0f}<br>"
            "Part grave : %{customdata[1]:.1%}<extra></extra>"
        ),
    )
    plotly_layout(city_figure, height=520)
    city_figure.update_layout(margin=dict(l=12, r=12, t=0, b=14))

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.markdown("#### Accidents géolocalisés")
        st.caption(
            "Clusters au faible zoom, points individuels en zoomant · "
            "cliquez sur un accident pour le mettre en évidence."
        )
        st.markdown(
            '<div class="map-legend">'
            '<span><i class="map-legend-dot map-legend-severe"></i>Accident grave</span>'
            '<span><i class="map-legend-dot map-legend-other"></i>Autre accident</span>'
            '<span><i class="map-legend-line"></i>Limite du Loiret</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            map_figure,
            width="stretch",
            config={"displayModeBar": False},
            key="accident_map",
            on_select="rerun",
            selection_mode="points",
            alt=(
                "Carte des accidents corporels du Loiret. Les accidents sont regroupés "
                "en clusters à faible zoom et se séparent en zoomant. Taille et couleur "
                "distinguent les accidents graves des autres."
            ),
        )
    with right:
        st.markdown("#### Top communes")
        st.caption("12 communes · accidents graves selon les filtres choisis.")
        st.plotly_chart(
            city_figure,
            width="stretch",
            config={"displayModeBar": False},
            alt="Classement des douze communes ayant le plus d’accidents graves.",
        )

    st.markdown("#### Explorer les accidents d'une commune")
    city_options = municipality_data["commune"].tolist()
    if city_options:
        selected_city = st.selectbox("Commune à détailler", city_options, key="detail_commune")
        details = data.loc[data["commune"] == selected_city].sort_values("date", ascending=False)
        detail_columns = {
            "date": "Date",
            "heure": "Heure",
            "niveau_gravite": "Gravité",
            "catr_libelle": "Type de route",
            "atm_libelle": "Météo",
            "lum_libelle": "Luminosité",
            "vma": "Vitesse (km/h)",
            "nb_tues": "Tués",
            "nb_hospitalises": "Hospitalisés",
        }
        display = details.loc[:, list(detail_columns)].rename(columns=detail_columns).head(50)
        st.caption(
            f"{len(details)} accidents dans {selected_city} pour les filtres choisis. "
            "Les 50 plus récents sont affichés."
        )
        st.dataframe(display, hide_index=True, width="stretch")
    else:
        st.info("Aucune commune ne correspond aux filtres.")


def render_planning(data: pd.DataFrame, dashboard: dict[str, Any]) -> None:
    total_graves = int(data["grave"].sum())
    slots = pd.DataFrame(dashboard["control_slots"])
    if slots.empty:
        st.info("Aucun accident grave dans cette sélection : aucun créneau ne peut être classé.")
        return

    selected_count = int(slots["accidents_graves"].sum())
    coverage = selected_count / total_graves if total_graves else 0.0
    st.markdown("#### Trois créneaux d'une heure à examiner en priorité")
    st.caption(
        "Classement descriptif des jours et heures ayant enregistré le plus d'accidents graves "
        "dans la période filtrée. Il ne mesure ni le trafic, ni l'effet d'un contrôle."
    )
    col1, col2 = st.columns([1, 1.55], gap="large")
    with col1:
        st.metric("Part des accidents graves observés dans ces 3 créneaux", f"{coverage:.1%}")
        table = slots.loc[:, ["jour_nom", "heure", "accidents_graves", "accidents"]].rename(
            columns={
                "jour_nom": "Jour",
                "heure": "Heure",
                "accidents_graves": "Graves (historique)",
                "accidents": "Tous accidents",
            }
        )
        table["Heure"] = table["Heure"].map(lambda hour: f"{hour:02d} h–{hour + 1:02d} h")
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption(f"Somme historique : {selected_count} accident(s) grave(s) sur {total_graves}.")

    weekly = pd.DataFrame(dashboard["weekday_hours"])
    matrix = (
        weekly.pivot(index="jour_nom", columns="heure", values="accidents_graves")
        .reindex(index=DAY_NAMES, columns=range(24))
        .fillna(0)
    )
    accident_matrix = (
        weekly.pivot(index="jour_nom", columns="heure", values="accidents")
        .reindex(index=DAY_NAMES, columns=range(24))
        .fillna(0)
    )
    heatmap = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=[f"{hour:02d} h" for hour in matrix.columns],
            y=matrix.index,
            colorscale="Cividis",
            colorbar=dict(title="Accidents<br>graves"),
            customdata=accident_matrix.values[..., None],
            hovertemplate=(
                "<b>%{y} · %{x}</b><br>Accidents graves : %{z:.0f}<br>"
                "Tous accidents : %{customdata[0]:.0f}<extra></extra>"
            ),
        )
    )
    busiest_hour = int(
        weekly.groupby("heure")["accidents_graves"].sum().idxmax()
    )
    busiest_hour_count = int(
        weekly.groupby("heure")["accidents_graves"].sum().max()
    )
    heatmap.update_layout(
        title=(
            f"Pic observé : {busiest_hour:02d} h · {busiest_hour_count} accident(s) grave(s)"
            f" · n={total_graves}"
        ),
        xaxis_title="Heure de l'accident",
        yaxis_title="Jour de la semaine",
    )
    plotly_layout(heatmap, height=380)
    st.plotly_chart(
        heatmap,
        width="stretch",
        config={"displayModeBar": False},
        alt=(
            "Carte de chaleur des accidents graves par jour de la semaine et heure, "
            "avec le nombre total d’accidents dans chaque case."
        ),
    )

    weather = pd.DataFrame(dashboard["weather"])
    lighting = pd.DataFrame(dashboard["lighting"])
    roads = pd.DataFrame(dashboard["roads"])
    left, right = st.columns(2, gap="large")
    for container, result, category, title, threshold in (
        (left, weather, "atm_libelle", "Météo", "catégories avec au moins 20 accidents"),
        (
            right,
            lighting,
            "periode_luminosite",
            "Période de luminosité",
            "effectif affiché",
        ),
    ):
        with container:
            if result.empty:
                st.info("Pas assez d'observations pour comparer ces catégories.")
                continue
            leading = result.iloc[0]
            chart = px.bar(
                result,
                x="part_grave",
                y=category,
                orientation="h",
                text=result["part_grave"].map(lambda value: f"{value:.0%}"),
                color="part_grave",
                color_continuous_scale="cividis",
                title=(
                    f"{title} : {leading[category]} · "
                    f"{leading['part_grave']:.1%} ({int(leading['graves'])}/"
                    f"{int(leading['accidents'])} accidents)"
                ),
                labels={
                    "part_grave": "Part d'accidents graves",
                    "accidents": "Tous accidents",
                    "graves": "Accidents graves",
                    category: "",
                },
            )
            chart.update_traces(
                customdata=result[["accidents", "graves"]].to_numpy(),
                hovertemplate=(
                    "<b>%{y}</b><br>Part grave : %{x:.1%}<br>"
                    "Accidents graves : %{customdata[1]:.0f}<br>"
                    "Tous accidents : %{customdata[0]:.0f}<extra></extra>"
                ),
            )
            chart.update_layout(coloraxis_showscale=False, xaxis_tickformat=".0%")
            chart.update_traces(textposition="outside", cliponaxis=False)
            plotly_layout(chart, height=max(300, 58 * len(result) + 100))
            st.caption(f"Comparaison descriptive · {threshold}.")
            st.plotly_chart(
                chart,
                width="stretch",
                config={"displayModeBar": False},
                alt=f"Comparaison de la part d’accidents graves selon {title.lower()}.",
            )

    if "Nuit (tous éclairages)" in lighting["periode_luminosite"].values and (
        "Plein jour" in lighting["periode_luminosite"].values
    ):
        lighting_index = lighting.set_index("periode_luminosite")
        night_rate = lighting_index.loc["Nuit (tous éclairages)", "part_grave"]
        day_rate = lighting_index.loc["Plein jour", "part_grave"]
        lighting_message = (
            f"{night_rate:.1%} des accidents recensés la nuit sont graves, contre "
            f"{day_rate:.1%} en plein jour. La nuit regroupe les trois situations "
            "d'éclairage nocturne ; cette comparaison descriptive ne tient pas compte "
            "du volume de circulation."
        )
    else:
        lighting_message = "Pas assez d'observations pour comparer la nuit et le plein jour."
    st.markdown("#### La nuit est-elle plus grave ?")
    st.caption(lighting_message)
    if not roads.empty:
        leading_road = roads.iloc[0]
        road_chart = px.bar(
            roads,
            x="part_grave",
            y="catr_libelle",
            orientation="h",
            text=roads["part_grave"].map(lambda value: f"{value:.0%}"),
            color="part_grave",
            color_continuous_scale="cividis",
            title=(
                f"Route avec la part grave la plus élevée : "
                f"{leading_road['catr_libelle']} · {leading_road['part_grave']:.1%} "
                f"({int(leading_road['graves'])}/{int(leading_road['accidents'])} accidents)"
            ),
            labels={
                "part_grave": "Part d'accidents graves",
                "accidents": "Tous accidents",
                "graves": "Accidents graves",
                "catr_libelle": "",
            },
        )
        road_chart.update_traces(
            customdata=roads[["accidents", "graves"]].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>Part grave : %{x:.1%}<br>"
                "Accidents graves : %{customdata[1]:.0f}<br>"
                "Tous accidents : %{customdata[0]:.0f}<extra></extra>"
            ),
        )
        road_chart.update_layout(coloraxis_showscale=False, xaxis_tickformat=".0%")
        road_chart.update_traces(textposition="outside", cliponaxis=False)
        plotly_layout(road_chart, height=max(300, 58 * len(roads) + 100))
        st.plotly_chart(
            road_chart,
            width="stretch",
            config={"displayModeBar": False},
            alt="Part d’accidents graves comparée selon le type de route.",
        )
    st.markdown(
        '<div class="note">Une part plus élevée ne signifie pas que la météo, la luminosité '
        'ou la route cause l’accident : ces données recensent uniquement les accidents '
        'corporels et ne contiennent pas le volume de circulation.</div>',
        unsafe_allow_html=True,
    )


def render_scenario(data: pd.DataFrame, municipality_data: pd.DataFrame) -> None:
    st.markdown("#### Estimer un score de gravité pour un scénario")
    st.write(
        "Choisissez un contexte de circulation. Le modèle estime la part de cas graves parmi "
        "des accidents corporels historiques comparables — ce n'est pas la probabilité qu'un "
        "accident arrive."
    )

    coordinates = data.groupby("commune")[["lat", "long"]].median()
    cities = sorted(coordinates.index.tolist())
    if not cities:
        st.info("Aucune commune dans les filtres actuels.")
        return

    default_city = municipality_data.iloc[0]["commune"]
    col1, col2, col3 = st.columns(3)
    with col1:
        city = st.selectbox("Commune", cities, index=cities.index(default_city))
        month = st.selectbox(
            "Mois",
            options=range(1, 13),
            format_func=lambda value: MONTH_NAMES[value - 1],
            index=6,
        )
        weekday = st.selectbox(
            "Jour de la semaine",
            options=range(7),
            format_func=lambda value: DAY_NAMES[value],
        )
    with col2:
        hour = st.slider("Heure de départ", min_value=0, max_value=23, value=17)
        lights = sorted(data["lum_libelle"].dropna().unique().tolist())
        lighting_default = lights.index("Plein jour") if "Plein jour" in lights else 0
        lighting = st.selectbox("Luminosité", lights, index=lighting_default)
        weather_options = sorted(data["atm_libelle"].dropna().unique().tolist())
        weather_default = weather_options.index("Normale") if "Normale" in weather_options else 0
        weather = st.selectbox("Météo", weather_options, index=weather_default)
    with col3:
        road_options = sorted(data["catr_libelle"].dropna().unique().tolist())
        road_default = (
            road_options.index("Route départementale")
            if "Route départementale" in road_options
            else 0
        )
        road = st.selectbox("Type de route", road_options, index=road_default)
        speed_limits = sorted(
            int(value)
            for value in data["vma"].dropna().unique()
            if 0 <= value <= 130
        )
        speed_default = speed_limits.index(50) if 50 in speed_limits else 0
        speed_limit = st.selectbox(
            "Vitesse maximale affichée (km/h)", speed_limits, index=speed_default
        )
        st.markdown(
            f'<div class="note">Coordonnées utilisées : centre observé de '
            f'{city} ({coordinates.loc[city, "lat"]:.3f}, '
            f'{coordinates.loc[city, "long"]:.3f}).</div>',
            unsafe_allow_html=True,
        )

    result = score_remote_scenario(
        (
            month,
            hour,
            weekday,
            float(coordinates.loc[city, "lat"]),
            float(coordinates.loc[city, "long"]),
            speed_limit,
            lighting,
            weather,
            road,
        )
    )
    score = result["score"]
    metrics = result["metrics"]
    st.metric(
        "Score estimé d'accident grave parmi les accidents corporels similaires",
        f"{score:.0%}",
    )
    st.caption(
        "Le score n'est pas une probabilité individuelle calibrée et ne mesure pas un risque "
        "par véhicule-kilomètre. Utilisez-le pour comparer des scénarios, jamais seul pour "
        "décider d'un contrôle. Les coordonnées du scénario sont le centre des accidents "
        "recensés de la commune."
    )

    st.markdown("#### Qualité du modèle : test temporel indépendant")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AUC ROC", f"{metrics['auc']:.2f}", help="Pouvoir de classement : 0,5 = hasard.")
    m2.metric("Rappel des cas graves", f"{metrics['rappel']:.0%}")
    m3.metric("Exactitude", f"{metrics['exactitude']:.0%}")
    m4.metric("Année tenue à l'écart", f"{metrics['annee_test']} · n={metrics['n_test']}")
    st.caption(
        f"Apprentissage sur {metrics['n_apprentissage']:,} accidents des années antérieures ; "
        f"exactitude du modèle {metrics['exactitude']:.1%} contre "
        f"{metrics['exactitude_baseline']:.1%} pour la règle majoritaire. "
        f"Précision {metrics['precision']:.1%} · F1 {metrics['f1']:.2f}. "
        "Le modèle final est ensuite réentraîné sur toutes les années disponibles."
        .replace(",", " ")
    )
    importance_labels = {
        "mois": "Mois",
        "heure": "Heure",
        "jour_semaine": "Jour de la semaine",
        "lat": "Latitude",
        "long": "Longitude",
        "vma": "Vitesse maximale affichée",
        "lum_libelle": "Luminosité",
        "atm_libelle": "Météo",
        "catr_libelle": "Type de route",
    }
    importance = pd.DataFrame(metrics["importance_variables"])
    importance["parametre"] = importance["parametre"].map(importance_labels)
    importance = importance.sort_values("importance_moyenne")
    importance_figure = px.bar(
        importance,
        x="importance_moyenne",
        y="parametre",
        orientation="h",
        error_x="ecart_type",
        color="importance_moyenne",
        color_continuous_scale=["#76a9fa", COLORS["teal"]],
        title=f"Importance des variables · test {metrics['annee_test']}",
        labels={
            "importance_moyenne": "Baisse moyenne de l'AUC",
            "parametre": "",
            "ecart_type": "Écart-type",
        },
    )
    importance_figure.update_traces(
        customdata=importance[["ecart_type"]].to_numpy(),
        hovertemplate=(
            "<b>%{y}</b><br>Baisse de l'AUC : %{x:.2%}<br>"
            "Écart-type : %{customdata[0]:.2%}<extra></extra>"
        ),
    )
    importance_figure.update_layout(
        coloraxis_showscale=False,
        xaxis_tickformat=".1%",
        xaxis_title="Baisse moyenne de l'AUC (%)",
    )
    plotly_layout(importance_figure, height=390)
    st.plotly_chart(
        importance_figure,
        width="stretch",
        config={"displayModeBar": False},
        alt=(
            "Importance des paramètres du modèle, classés selon la baisse moyenne "
            "de l’AUC observée après permutation sur l’année de test."
        ),
    )
    st.caption(
        "Importance par permutation mesurée sur l'année de test : plus la baisse moyenne "
        "de l'AUC est grande, plus le modèle s'appuie sur ce paramètre pour classer les cas "
        "graves. Les variables corrélées peuvent se partager cette importance ; ce classement "
        "ne révèle pas de cause et ne mesure pas un effet causal."
    )


def main() -> None:
    st.sidebar.markdown(
        '<div class="eyebrow">Observatoire · Loiret</div>'
        "<h2>Vigie routière</h2>"
        "<p style='color:#a7b3c5'>Choisir où et quand renforcer la prévention.</p>",
        unsafe_allow_html=True,
    )
    options = load_options()
    years = options["years"]
    selected_years = st.sidebar.select_slider(
        "Période analysée",
        options=years,
        value=(years[0], years[-1]),
        format_func=str,
    )
    communes = options["communes"]
    selected_communes = st.sidebar.multiselect(
        "Communes",
        options=communes,
        default=[],
        placeholder="Toutes les communes",
    )
    roads = options["roads"]
    selected_roads = st.sidebar.multiselect(
        "Types de route",
        options=roads,
        default=[],
        placeholder="Tous les types",
    )
    st.sidebar.divider()
    st.sidebar.caption(
        "Source : fichier BAAC / ONISR · accidents corporels, 2019–2025. "
        "Chaque point représente un accident, pas un volume de trafic."
    )

    dashboard = load_dashboard(
        first_year=selected_years[0],
        last_year=selected_years[1],
        communes=tuple(selected_communes),
        roads=tuple(selected_roads),
    )
    filtered = pd.DataFrame(dashboard["records"])
    if filtered.empty:
        st.warning(
            "Aucun accident pour ces filtres. Modifiez la période, les communes ou les routes."
        )
        st.stop()

    municipality_data = pd.DataFrame(dashboard["municipalities"])
    stats = dashboard["summary"]
    st.markdown(
        '<div class="hero"><div class="eyebrow">Décision · service sécurité routière</div>'
        "<h1>Où et quand concentrer les contrôles ?</h1>"
        "<p>Repérer les communes, routes et créneaux qui cumulent le plus d’accidents graves, "
        "puis comparer des scénarios de gravité pour orienter la prévention.</p></div>",
        unsafe_allow_html=True,
    )
    first, last = selected_years
    st.caption(
        f"Vue filtrée · {first}–{last} · {len(filtered):,} accidents corporels".replace(",", " ")
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("Accidents", f"{stats['total']:,}".replace(",", " "))
    k2.metric("Graves", f"{stats['graves']:,}".replace(",", " "))
    k3.metric("Part grave", f"{stats['part_grave']:.1%}")

    overview, planning, scenario = st.tabs(
        ["Explorer la carte", "Choisir les créneaux", "Simuler un scénario"]
    )
    with overview:
        render_overview(filtered, municipality_data)
    with planning:
        render_planning(filtered, dashboard)
    with scenario:
        render_scenario(filtered, municipality_data)


if __name__ == "__main__":
    main()
