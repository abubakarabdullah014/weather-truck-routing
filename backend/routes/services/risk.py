"""Weather risk classification and load-based overrides."""
from __future__ import annotations

from typing import Literal

RiskLevel = Literal["Low", "Moderate", "High", "Severe", "No Travel"]

RISK_SCORE = {
    "Low": 1,
    "Moderate": 2,
    "High": 3,
    "Severe": 4,
    "No Travel": 5,
}


def _band(
    value: float,
    thresholds: list[tuple[float, RiskLevel]],
) -> RiskLevel:
    """
    thresholds are upper-bounds (exclusive of next), ordered ascending,
    last entry is the catch-all.
    """
    for upper, level in thresholds:
        if value < upper:
            return level
    return thresholds[-1][1]


def classify_wind(mph: float) -> RiskLevel:
    # <25 Low, 25–34 Mod, 35–44 High, 45–54 Severe, ≥55 No Travel
    if mph < 25:
        return "Low"
    if mph < 35:
        return "Moderate"
    if mph < 45:
        return "High"
    if mph < 55:
        return "Severe"
    return "No Travel"


def classify_rain(in_hr: float) -> RiskLevel:
    # <0.10 Low, 0.10–0.25 Mod, 0.25–0.50 High, 0.50–1.00 Severe, >1.00 No Travel
    if in_hr < 0.10:
        return "Low"
    if in_hr <= 0.25:
        return "Moderate"
    if in_hr <= 0.50:
        return "High"
    if in_hr <= 1.00:
        return "Severe"
    return "No Travel"


def classify_snow(in_hr: float) -> RiskLevel:
    # <0.5 Low, 0.5–1.0 Mod, 1.0–2.0 High, 2.0–3.0 Severe, >3.0 No Travel
    if in_hr < 0.5:
        return "Low"
    if in_hr <= 1.0:
        return "Moderate"
    if in_hr <= 2.0:
        return "High"
    if in_hr <= 3.0:
        return "Severe"
    return "No Travel"


def apply_load_rules(wind_mph: float, load_lb: float, base: RiskLevel) -> RiskLevel:
    """
    Load rules:
      • ≥55 mph → No Travel for any load
      • 45–54 mph + >30,000 lb → No Travel
      • 35–44 mph + >40,000 lb → Severe
    """
    if wind_mph >= 55:
        return "No Travel"
    if 45 <= wind_mph < 55 and load_lb > 30_000:
        return "No Travel"
    if 35 <= wind_mph < 45 and load_lb > 40_000:
        # Escalate at least to Severe
        if RISK_SCORE[base] < RISK_SCORE["Severe"]:
            return "Severe"
    return base


def worst_level(*levels: RiskLevel) -> RiskLevel:
    return max(levels, key=lambda lvl: RISK_SCORE[lvl])


def assess_checkpoint(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_lb: float,
) -> dict:
    wind_r = classify_wind(wind_mph)
    rain_r = classify_rain(rain_in_hr)
    snow_r = classify_snow(snow_in_hr)
    combined = worst_level(wind_r, rain_r, snow_r)
    final = apply_load_rules(wind_mph, load_lb, combined)
    return {
        "wind_risk": wind_r,
        "rain_risk": rain_r,
        "snow_risk": snow_r,
        "risk": final,
        "risk_score": RISK_SCORE[final],
    }
