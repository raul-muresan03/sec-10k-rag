from unittest.mock import Mock

from etl_pipeline import pipeline


def test_cli_prepares_selected_filing_and_returns_its_index(tmp_path, monkeypatch):
    selected = tmp_path / "indexes" / "selected" / "all_chunks_embeddings.json"
    store = Mock()
    store.prepare_selected.return_value.index_path = selected
    monkeypatch.setattr(pipeline, "FilingIndexStore", lambda: store)

    assert pipeline.ensure_index("NVDA", 2026) == selected
    store.prepare_selected.assert_called_once_with("NVDA", 2026)
