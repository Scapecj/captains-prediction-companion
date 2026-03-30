import unittest

from core.scrapers.kalshi_fetcher import _mid_price


class KalshiFetcherPriceTests(unittest.TestCase):
    def test_mid_price_uses_last_trade_when_one_sided_book_shows_placeholder_ask(self):
        market = {
            "response_price_units": "usd_cent",
            "yes_bid_dollars": "0.0000",
            "yes_ask_dollars": "1.0000",
            "yes_bid_size_fp": "0.00",
            "yes_ask_size_fp": "0.00",
            "last_price_dollars": "0.0500",
        }

        self.assertEqual(_mid_price(market), 0.05)


if __name__ == "__main__":
    unittest.main()
