import json
import sys
from unittest.mock import Mock, patch

import pytest
import requests

import ask


@pytest.fixture
def ensure_index(monkeypatch, data_directory):
    ensure = Mock(return_value=data_directory / "indexes" / "selected" / "all_chunks_embeddings.json")
    monkeypatch.setattr(ask, "ensure_index", ensure)
    return ensure


def test_main_retrieves_chunks_and_generates_answer(data_directory, monkeypatch, capsys, ensure_index):
    chunks = [(0.95, "relevant evidence")]
    retrieve = Mock(return_value=chunks)
    generate = Mock(return_value=("Grounded answer", {"eval_count": 12}))
    monkeypatch.setattr(ask, "get_most_similar_chunks", retrieve)
    monkeypatch.setattr(ask, "get_llm_response", generate)
    monkeypatch.setattr(ask.time, "perf_counter", Mock(side_effect=[1.0, 2.0, 3.0, 5.0]))
    monkeypatch.setattr(
        sys,
        "argv",
        ["ask.py", "What happened?", "--ticker", "nvda", "--year", "2026"],
    )

    ask.main()

    ensure_index.assert_called_once_with("NVDA", 2026)
    retrieve.assert_called_once_with("What happened?", ask.DEFAULT_TOP_N, ensure_index.return_value)
    generate.assert_called_once_with("What happened?", chunks, ask.DEFAULT_MODEL)
    output = capsys.readouterr().out
    assert "Retrieved 1 chunks" in output
    assert "Grounded answer" in output
    record = json.loads((data_directory / ask.QUERY_LOG_FILENAME).read_text())
    assert record["timestamp"].endswith("+00:00")
    assert record["ticker"] == "NVDA"
    assert record["filing_year"] == 2026
    assert record["question"] == "What happened?"
    assert record["answer"] == "Grounded answer"
    assert record["model"] == ask.DEFAULT_MODEL
    assert record["chunks"] == [{"score": 0.95, "text": "relevant evidence"}]
    assert record["latency_seconds"] == {"retrieval": 1.0, "generation": 2.0, "total": 3.0}
    assert record["ollama"] == {"eval_count": 12}


def test_query_log_appends_one_json_object_per_line(data_directory):
    ask._append_query_log({"question": "first"})
    ask._append_query_log({"question": "second"})

    lines = (data_directory / ask.QUERY_LOG_FILENAME).read_text().splitlines()
    assert [json.loads(line) for line in lines] == [
        {"question": "first"},
        {"question": "second"},
    ]


def test_query_log_failure_warns_without_raising(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ask.etl_pipeline, "DATA_DIR", tmp_path / "missing")

    ask._append_query_log({"question": "still answered"})

    assert "Warning: query could not be logged" in capsys.readouterr().out


def test_main_accepts_retrieval_and_model_options(data_directory, monkeypatch, ensure_index):
    retrieve = Mock(return_value=[])
    generate = Mock(return_value=("answer", {}))
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
    retrieve.assert_called_once_with("What happened?", 3, ensure_index.return_value)
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


@pytest.mark.parametrize("quota", [True, False])
def test_cli_reports_provider_failure_without_saving_a_partial_answer(
    data_directory, monkeypatch, capsys, ensure_index, quota,
):
    index_path = ensure_index.return_value
    index_path.parent.mkdir(parents=True)
    index_path.write_text(json.dumps({"chunks": ["evidence"], "embeddings": [[1.0, 0.0]]}))
    monkeypatch.setattr(sys, "argv", ["ask.py", "Revenue?", "--ticker", "NVDA", "--year", "2026"])
    upstream = Mock(status_code=429, headers={"Retry-After": "12"}) if quota else requests.Timeout()
    with patch("requests.post", **({"return_value": upstream} if quota else {"side_effect": upstream})) as post:
        with pytest.raises(SystemExit) as failure:
            ask.main()
    assert failure.value.code == 2
    assert ("retry in 12s" if quota else "timed out") in capsys.readouterr().err
    assert not (data_directory / ask.QUERY_LOG_FILENAME).exists()
    assert post.call_count == 1
