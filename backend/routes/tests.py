from django.test import SimpleTestCase

from routes.services.recommendation import recommend
from routes.services.risk import assess_checkpoint, classify_rain, classify_snow, classify_wind


class RiskRulesTests(SimpleTestCase):
    def test_wind_bands(self):
        self.assertEqual(classify_wind(24.9), "Low")
        self.assertEqual(classify_wind(25), "Moderate")
        self.assertEqual(classify_wind(34.9), "Moderate")
        self.assertEqual(classify_wind(35), "High")
        self.assertEqual(classify_wind(44.9), "High")
        self.assertEqual(classify_wind(45), "Severe")
        self.assertEqual(classify_wind(54.9), "Severe")
        self.assertEqual(classify_wind(55), "No Travel")

    def test_rain_bands(self):
        self.assertEqual(classify_rain(0.09), "Low")
        self.assertEqual(classify_rain(0.10), "Moderate")
        self.assertEqual(classify_rain(0.25), "Moderate")
        self.assertEqual(classify_rain(0.26), "High")
        self.assertEqual(classify_rain(0.50), "High")
        self.assertEqual(classify_rain(0.51), "Severe")
        self.assertEqual(classify_rain(1.00), "Severe")
        self.assertEqual(classify_rain(1.01), "No Travel")

    def test_snow_bands(self):
        self.assertEqual(classify_snow(0.49), "Low")
        self.assertEqual(classify_snow(0.5), "Moderate")
        self.assertEqual(classify_snow(1.0), "Moderate")
        self.assertEqual(classify_snow(1.1), "High")
        self.assertEqual(classify_snow(2.0), "High")
        self.assertEqual(classify_snow(2.1), "Severe")
        self.assertEqual(classify_snow(3.0), "Severe")
        self.assertEqual(classify_snow(3.1), "No Travel")

    def test_load_rules(self):
        # ≥55 any load
        self.assertEqual(
            assess_checkpoint(55, 0, 0, 1000)["risk"], "No Travel"
        )
        # 45–54 + >30k
        self.assertEqual(
            assess_checkpoint(50, 0, 0, 30001)["risk"], "No Travel"
        )
        self.assertEqual(
            assess_checkpoint(50, 0, 0, 30000)["risk"], "Severe"
        )
        # 35–44 + >40k → Severe
        self.assertEqual(
            assess_checkpoint(40, 0, 0, 40001)["risk"], "Severe"
        )
        self.assertEqual(
            assess_checkpoint(40, 0, 0, 40000)["risk"], "High"
        )


class RecommendationTests(SimpleTestCase):
    def _route(self, rid, severe_seg, high_seg, avg_scores, duration_s, miles=100.0):
        """Build a minimal route with two segments of known risk."""
        cps = [
            {"distance_miles": 0, "risk": "Low", "risk_score": 1},
            {
                "distance_miles": severe_seg,
                "risk": "Severe",
                "risk_score": 4,
            },
            {
                "distance_miles": severe_seg + high_seg,
                "risk": "High",
                "risk_score": 3,
            },
            {
                "distance_miles": miles,
                "risk": "Low",
                "risk_score": 1,
            },
        ]
        # Override scores for avg_risk if provided
        if avg_scores:
            for cp, score in zip(cps, avg_scores):
                cp["risk_score"] = score
                inv = {1: "Low", 2: "Moderate", 3: "High", 4: "Severe", 5: "No Travel"}
                cp["risk"] = inv[score]
        return {
            "id": rid,
            "label": f"Route {rid}",
            "duration_s": duration_s,
            "distance_miles": miles,
            "checkpoints": cps,
        }

    def test_prefers_fewest_severe_miles(self):
        routes = [
            self._route(1, severe_seg=40, high_seg=10, avg_scores=None, duration_s=3600),
            self._route(2, severe_seg=10, high_seg=40, avg_scores=None, duration_s=4000),
        ]
        result = recommend(routes)
        self.assertEqual(result["recommended_route_id"], 2)

    def test_then_fewest_high_then_time(self):
        # Equal severe (0), route 1 has more high miles → pick 2
        r1 = {
            "id": 1,
            "duration_s": 3000,
            "distance_miles": 100,
            "checkpoints": [
                {"distance_miles": 0, "risk": "Low", "risk_score": 1},
                {"distance_miles": 50, "risk": "High", "risk_score": 3},
                {"distance_miles": 100, "risk": "Low", "risk_score": 1},
            ],
        }
        r2 = {
            "id": 2,
            "duration_s": 5000,
            "distance_miles": 100,
            "checkpoints": [
                {"distance_miles": 0, "risk": "Low", "risk_score": 1},
                {"distance_miles": 10, "risk": "High", "risk_score": 3},
                {"distance_miles": 100, "risk": "Low", "risk_score": 1},
            ],
        }
        self.assertEqual(recommend([r1, r2])["recommended_route_id"], 2)
