from __future__ import annotations

from backend.api import dashboard, health, options


def test_health_options_and_filtered_dashboard() -> None:
    assert health() == {"status": "ok"}
    assert 2025 in options()["years"]
    result = dashboard(first_year=2025, last_year=2025)
    assert result["summary"]["total"] == 413
    assert result["summary"]["graves"] == sum(row["grave"] for row in result["records"])
    assert result["control_slots"]
