"""Recommend the best route: fewest Severe → High → avg risk → shortest time."""
from __future__ import annotations

from .risk import RISK_SCORE


def summarize_route(route: dict) -> dict:
    checkpoints = route.get("checkpoints") or []
    miles_by_risk = {
        "Low": 0.0,
        "Moderate": 0.0,
        "High": 0.0,
        "Severe": 0.0,
        "No Travel": 0.0,
    }
    scores: list[float] = []

    for i, cp in enumerate(checkpoints):
        risk = cp.get("risk", "Low")
        scores.append(float(cp.get("risk_score", RISK_SCORE.get(risk, 1))))
        # Attribute segment miles from previous checkpoint to this one's risk
        if i == 0:
            continue
        seg = max(
            0.0,
            float(cp["distance_miles"]) - float(checkpoints[i - 1]["distance_miles"]),
        )
        miles_by_risk[risk] = miles_by_risk.get(risk, 0.0) + seg

    avg_risk = sum(scores) / len(scores) if scores else 1.0
    has_no_travel = any(cp.get("risk") == "No Travel" for cp in checkpoints)

    summary = {
        "severe_miles": round(miles_by_risk["Severe"] + miles_by_risk["No Travel"], 2),
        "high_miles": round(miles_by_risk["High"], 2),
        "moderate_miles": round(miles_by_risk["Moderate"], 2),
        "low_miles": round(miles_by_risk["Low"], 2),
        "no_travel_miles": round(miles_by_risk["No Travel"], 2),
        "avg_risk": round(avg_risk, 3),
        "max_risk": max((cp.get("risk", "Low") for cp in checkpoints), key=lambda r: RISK_SCORE[r])
        if checkpoints
        else "Low",
        "has_no_travel": has_no_travel,
        "travel_time_s": route.get("duration_s", 0),
        "distance_miles": route.get("distance_miles", 0),
        "checkpoint_count": len(checkpoints),
    }
    route["summary"] = summary
    return summary


def recommend(routes: list[dict]) -> dict:
    """
    Prefer:
      1. Fewest Severe miles (No Travel counted as Severe+)
      2. Fewest High miles
      3. Lowest average risk
      4. Shortest travel time
    Routes with any No Travel are ranked last within ties via a large penalty.
    """
    for route in routes:
        summarize_route(route)

    def sort_key(r: dict):
        s = r["summary"]
        no_travel_penalty = 1e9 if s["has_no_travel"] else 0.0
        return (
            no_travel_penalty + s["severe_miles"],
            s["high_miles"],
            s["avg_risk"],
            s["travel_time_s"],
        )

    ranked = sorted(routes, key=sort_key)
    best = ranked[0]
    for r in routes:
        r["recommended"] = r["id"] == best["id"]

    reasons = []
    s = best["summary"]
    reasons.append(f"Fewest severe/no-travel miles ({s['severe_miles']} mi)")
    reasons.append(f"High-risk miles: {s['high_miles']} mi")
    reasons.append(f"Average risk score: {s['avg_risk']}")
    hours = s["travel_time_s"] / 3600
    reasons.append(f"Travel time: {hours:.1f} h")

    return {
        "recommended_route_id": best["id"],
        "reasons": reasons,
        "ranking": [r["id"] for r in ranked],
    }
