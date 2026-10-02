import sys

import pytest

from api import prepare_filings


def test_operator_can_prepare_one_or_all_catalog_filings(monkeypatch, capsys, local_corpus, local_models):
    monkeypatch.setattr(sys, "argv", ["prepare_filings", "--filing-id", "0-0000000000-14-000001"])
    prepare_filings.main(store=local_corpus)
    assert [(filing.ticker, filing.year) for filing in local_corpus.prepared()] == [("F", 2014)]

    monkeypatch.setattr(sys, "argv", ["prepare_filings"])
    prepare_filings.main(store=local_corpus)
    assert {filing.ticker for filing in local_corpus.prepared()} == {"NVDA", "F"}
    assert "Ready" in capsys.readouterr().out


def test_operator_cannot_prepare_an_unknown_filing(monkeypatch, local_corpus, local_models):
    monkeypatch.setattr(sys, "argv", ["prepare_filings", "--filing-id", "test-filing"])
    with pytest.raises(SystemExit):
        prepare_filings.main(store=local_corpus)
    assert not local_models[1].called
