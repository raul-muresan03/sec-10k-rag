import sys
from types import SimpleNamespace

import pytest

from api import prepare_filings


def test_operator_can_prepare_one_or_all_catalog_filings(monkeypatch, capsys):
    calls = []
    catalog = {
        "first": SimpleNamespace(ticker="NVDA", year=2026),
        "second": SimpleNamespace(ticker="F", year=2014),
    }

    class Store:
        def catalog(self):
            return catalog

        def prepare_selected(self, ticker, year):
            calls.append((ticker, year))
            return SimpleNamespace(ticker=ticker, year=year, chunk_count=10)

    monkeypatch.setattr(prepare_filings, "FilingIndexStore", Store)
    monkeypatch.setattr(prepare_filings, "download_verified", lambda filing: None)
    monkeypatch.setattr(sys, "argv", ["prepare_filings", "--filing-id", "second"])
    prepare_filings.main()
    assert calls == [("F", 2014)]

    monkeypatch.setattr(sys, "argv", ["prepare_filings"])
    prepare_filings.main()
    assert calls == [("F", 2014), ("NVDA", 2026), ("F", 2014)]
    assert "Ready" in capsys.readouterr().out


def test_operator_cannot_prepare_an_unknown_filing(monkeypatch):
    class Store:
        def catalog(self):
            return {}

    monkeypatch.setattr(prepare_filings, "FilingIndexStore", Store)
    monkeypatch.setattr(sys, "argv", ["prepare_filings", "--filing-id", "test-filing"])
    with pytest.raises(SystemExit):
        prepare_filings.main()
