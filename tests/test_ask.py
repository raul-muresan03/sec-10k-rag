import sys
from unittest.mock import Mock

import pytest

import ask


def create_vector_store(data_directory):
    (data_directory / "all_chunks_embeddings.json").write_text("{}")


@pytest.fixture
def ensure_index(monkeypatch):
    ensure = Mock()
    monkeypatch.setattr(ask, "ensure_index", ensure)
    return ensure


def test_main_retrieves_chunks_and_generates_answer(data_directory, monkeypatch, capsys, ensure_index):
    create_vector_store(data_directory)
    chunks = [(0.95, "relevant evidence")]
    retrieve = Mock(return_value=chunks)
    generate = Mock(return_value="Grounded answer")
    monkeypatch.setattr(ask, "get_most_similar_chunks", retrieve)
    monkeypatch.setattr(ask, "get_llm_response", generate)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ask.py", "What happened?", "--ticker", "nvda", "--year", "2026"],
    )

    ask.main()

    ensure_index.assert_called_once_with("NVDA", 2026)
    retrieve.assert_called_once_with("What happened?", ask.DEFAULT_TOP_N)
    generate.assert_called_once_with("What happened?", chunks, ask.DEFAULT_MODEL)
    output = capsys.readouterr().out
    assert "Retrieved 1 chunks" in output
    assert "Grounded answer" in output


def test_main_accepts_retrieval_and_model_options(data_directory, monkeypatch, ensure_index):
    create_vector_store(data_directory)
    retrieve = Mock(return_value=[])
    generate = Mock(return_value="answer")
    monkeypatch.setattr(ask, "get_most_similar_chunks", retrieve)
    monkeypatch.setattr(ask, "get_llm_response", generate)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ask.py",
            "What happened?",
            "--ticker",
            "NVDA",
            "--year",
            "2025",
            "--top-n",
            "3",
            "--model",
            "custom-model",
        ],
    )

    ask.main()

    ensure_index.assert_called_once_with("NVDA", 2025)
    retrieve.assert_called_once_with("What happened?", 3)
    generate.assert_called_once_with("What happened?", [], "custom-model")


def test_main_requires_ticker(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ask.py", "What happened?", "--year", "2026"])

    with pytest.raises(SystemExit) as error:
        ask.main()

    assert error.value.code == 2
    assert "--ticker" in capsys.readouterr().err


def test_main_requires_year(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ask.py", "What happened?", "--ticker", "NVDA"])

    with pytest.raises(SystemExit) as error:
        ask.main()

    assert error.value.code == 2
    assert "--year" in capsys.readouterr().err


def test_main_rejects_year_outside_edgar_range(monkeypatch, capsys, ensure_index):
    monkeypatch.setattr(
        sys,
        "argv",
        ["ask.py", "What happened?", "--ticker", "NVDA", "--year", "1993"],
    )

    with pytest.raises(SystemExit) as error:
        ask.main()

    assert error.value.code == 2
    assert "year must be between" in capsys.readouterr().err
    ensure_index.assert_not_called()
