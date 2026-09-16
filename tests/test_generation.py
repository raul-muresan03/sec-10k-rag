from typing import Any
from unittest.mock import Mock, patch

from etl_pipeline import rag_engine


def test_generation_sends_question_context_and_model_to_ollama():
    response = Mock(status_code=200)
    response.json.return_value = {"response": "NVIDIA evidence-based answer"}
    chunks: Any = [(0.95, "First evidence"), (0.80, "Second evidence")]

    with patch.object(rag_engine.requests, "post", return_value=response) as post:
        result = rag_engine.get_llm_response("What happened?", chunks, "qwen3.5:4b")

    assert result == "NVIDIA evidence-based answer"
    post.assert_called_once()
    payload = post.call_args.kwargs["json"]
    assert post.call_args.kwargs["url"] == "http://localhost:11434/api/generate"
    assert payload["model"] == "qwen3.5:4b"
    assert payload["stream"] is False
    assert "First evidence\nSecond evidence" in payload["prompt"]
    assert "What happened?" in payload["prompt"]
    assert "Information not available in the provided context" in payload["prompt"]


def test_generation_preserves_retrieval_order_in_context():
    response = Mock(status_code=200)
    response.json.return_value = {"response": "answer"}
    chunks: Any = [(0.90, "highest ranked"), (0.70, "lower ranked")]

    with patch.object(rag_engine.requests, "post", return_value=response) as post:
        rag_engine.get_llm_response("question", chunks, "model")

    prompt = post.call_args.kwargs["json"]["prompt"]
    assert prompt.index("highest ranked") < prompt.index("lower ranked")


def test_generation_returns_error_for_failed_ollama_request():
    response = Mock(status_code=503)
    chunks: Any = [(0.95, "evidence")]

    with patch.object(rag_engine.requests, "post", return_value=response):
        result = rag_engine.get_llm_response("question", chunks, "model")

    assert result == "Error"


def test_system_prompt_requires_abstention_and_concise_answers():
    assert "Do not hallucinate numbers" in rag_engine.SYSTEM_PROMPT
    assert "Information not available in the provided context" in rag_engine.SYSTEM_PROMPT
    assert "professional, concise tone" in rag_engine.SYSTEM_PROMPT
