import sys
from unittest.mock import Mock

import pytest

import ask


def create_vector_store(data_directory):
    (data_directory / "all_chunks_embeddings.json").write_text("{}")


def test_main_retrieves_chunks_and_generates_answer(data_directory, monkeypatch, capsys):
    create_vector_store(data_directory)
    chunks = [(0.95, "relevant evidence")]
    retrieve = Mock(return_value=chunks)
    generate = Mock(return_value="Grounded answer")
    monkeypatch.setattr(ask, "get_most_similar_chunks", retrieve)
    monkeypatch.setattr(ask, "get_llm_response", generate)
    monkeypatch.setattr(sys, "argv", ["ask.py", "What happened?"])

    ask.main()

    retrieve.assert_called_once_with("What happened?", ask.DEFAULT_TOP_N)
    generate.assert_called_once_with("What happened?", chunks, ask.DEFAULT_MODEL)
    output = capsys.readouterr().out
    assert "Retrieved 1 chunks" in output
    assert "Grounded answer" in output


def test_main_accepts_retrieval_and_model_options(data_directory, monkeypatch):
    create_vector_store(data_directory)
    retrieve = Mock(return_value=[])
    generate = Mock(return_value="answer")
    monkeypatch.setattr(ask, "get_most_similar_chunks", retrieve)
    monkeypatch.setattr(ask, "get_llm_response", generate)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ask.py", "What happened?", "--top-n", "3", "--model", "custom-model"],
    )

    ask.main()

    retrieve.assert_called_once_with("What happened?", 3)
    generate.assert_called_once_with("What happened?", [], "custom-model")


def test_main_stops_when_vector_store_is_missing(data_directory, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ask.py", "What happened?"])

    with pytest.raises(SystemExit) as error:
        ask.main()

    assert error.value.code == 2
    assert "vector store not found" in capsys.readouterr().err
