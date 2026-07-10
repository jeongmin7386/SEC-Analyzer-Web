import unittest

from app.metric_calculator import INSUFFICIENT_DATA, analyze_normalized_financials


class MetricCalculatorTest(unittest.TestCase):
    def test_zero_and_negative_denominators_do_not_create_infinite_values(self):
        result = analyze_normalized_financials(
            [
                {
                    "fiscalYear": 2023,
                    "periodType": "ANNUAL",
                    "currency": "USD",
                    "revenue": 0,
                    "netIncome": 10,
                    "totalLiabilities": 50,
                    "totalEquity": -10,
                    "currentAssets": 20,
                    "currentLiabilities": 0,
                    "sharesOutstanding": 100,
                    "eps": 1,
                    "sourceType": "SEC",
                },
                {
                    "fiscalYear": 2024,
                    "periodType": "ANNUAL",
                    "currency": "USD",
                    "revenue": 100,
                    "netIncome": 12,
                    "totalLiabilities": 40,
                    "totalEquity": 60,
                    "currentAssets": 30,
                    "currentLiabilities": 20,
                    "sharesOutstanding": 102,
                    "eps": 1.1,
                    "sourceType": "SEC",
                },
            ],
            preset_id="default",
        )
        metric_by_key = {row["key"]: row for row in result["metrics"]}
        self.assertNotEqual(metric_by_key["net_profit_margin"]["status"], INSUFFICIENT_DATA)
        self.assertTrue(all(row["mean"] is None or row["mean"] == row["mean"] for row in result["metrics"]))


if __name__ == "__main__":
    unittest.main()
