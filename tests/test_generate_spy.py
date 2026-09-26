import unittest
from unittest.mock import patch

import pandas as pd

from generate_spy import _quote_from_frame, get_quotes, parse_holdings


class FakeBook:
    def __init__(self, rows):
        self.active = self
        self.values = rows

    def __contains__(self, name):
        return False

    def close(self):
        pass


class HoldingsTests(unittest.TestCase):
    def test_class_weights_merge_and_non_equity_rows_are_removed(self):
        rows = [
            ("Holdings:", "As of 24-Sep-2026", None, None, None),
            ("Name", "Ticker", "Identifier", "SEDOL", "Weight"),
            ("ALPHABET INC CL A", "GOOGL", "X", "X", 35.0),
            ("ALPHABET INC CL C", "GOOG", "X", "X", 25.0),
            ("FOX CORP CLASS A", "FOXA", "X", "X", 15.0),
            ("FOX CORP CLASS B", "FOX", "X", "X", 5.0),
            ("BERKSHIRE HATHAWAY INC CL B", "BRK.B", "X", "X", 19.999997),
            ("TPG INC", "2602335D", "X", "X", 0.000003),
            ("US DOLLAR", "-", "X", "X", 0.2),
            ("Legal disclaimer", None, None, None, None),
        ]
        with patch("generate_spy.load_workbook", return_value=FakeBook(rows)):
            holdings, date, excluded = parse_holdings(b"unused", min_holdings=3)
        self.assertEqual(date, "24-Sep-2026")
        self.assertEqual([(h.ticker, h.name, h.weight) for h in holdings], [
            ("GOOGL", "ALPHABET INC", 60.0), ("FOXA", "FOX CORP", 20.0),
            ("BRK-B", "BERKSHIRE HATHAWAY INC CL B", 19.999997),
        ])
        self.assertEqual([symbol for _, symbol, _ in excluded], ["2602335D", "-"])

    def test_quotes_use_previous_valid_close_and_handle_missing(self):
        days = pd.to_datetime(["2026-09-23 15:59", "2026-09-24 09:30", "2026-09-24 09:34"]).tz_localize("America/New_York")
        columns = pd.MultiIndex.from_product([["NVDA", "BRK-B"], ["Close"]])
        frame = pd.DataFrame([[120, 310], [None, 309], [117, 305]], index=days, columns=columns)
        self.assertEqual(_quote_from_frame(frame, "NVDA"), {
            "price": 117.0, "change": -3.0, "changePct": -2.5, "priceDate": "2026-09-24 06:34 PDT"
        })
        self.assertEqual(_quote_from_frame(frame, "BRK-B")["changePct"], -1.6129)
        self.assertIsNone(_quote_from_frame(frame, "MISSING"))

    def test_failed_quote_batch_does_not_silently_publish(self):
        with patch("yfinance.download", return_value=pd.DataFrame()):
            with self.assertRaisesRegex(RuntimeError, "existing output was kept"):
                get_quotes([f"TEST{i}" for i in range(15)],
                           batch_size=10, delay=0, retry_delay=0, max_retries=1)


if __name__ == "__main__":
    unittest.main()
