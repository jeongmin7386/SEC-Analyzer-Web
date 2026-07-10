import unittest

from app.providers.opendart_provider import OpenDARTConfigurationError, OpenDARTProvider
from app.services.market_resolver import MarketResolver


class FakeUSProvider:
    def search_stocks(self, query):
        value = query.upper()
        if value in {"AAPL", "APPLE"}:
            return [
                {
                    "market": "US",
                    "symbol": "AAPL",
                    "displaySymbol": "AAPL",
                    "companyName": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "currency": "USD",
                    "cik": "0000320193",
                }
            ]
        return []


class MarketResolverTest(unittest.TestCase):
    def setUp(self):
        self.kr_provider = OpenDARTProvider(api_key="")
        self.resolver = MarketResolver(self.kr_provider, FakeUSProvider())

    def test_resolves_six_digit_code_as_korean_stock(self):
        result = self.resolver.resolve("005930", "AUTO")
        self.assertEqual(result["market"], "KR")
        self.assertEqual(result["symbol"], "005930")
        self.assertEqual(result["currency"], "KRW")

    def test_resolves_kr_suffix_as_korean_stock(self):
        result = self.resolver.resolve("005930.KS", "AUTO")
        self.assertEqual(result["market"], "KR")
        self.assertEqual(result["symbol"], "005930")

    def test_resolves_us_ticker(self):
        result = self.resolver.resolve("AAPL", "AUTO")
        self.assertEqual(result["market"], "US")
        self.assertEqual(result["symbol"], "AAPL")

    def test_opendart_key_missing_is_configuration_error(self):
        with self.assertRaises(OpenDARTConfigurationError):
            self.kr_provider.get_financial_statements("005930", years=1)


if __name__ == "__main__":
    unittest.main()
