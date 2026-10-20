from django.test import SimpleTestCase

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
