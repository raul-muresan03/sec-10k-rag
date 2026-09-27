from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from unittest.mock import Mock, patch

import pytest
import requests

from etl_pipeline import ollama


def test_post_json_uses_configured_ollama_url_and_timeout(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "3")
    response = Mock(status_code=200)
    response.json.return_value = {"response": "answer"}

    with patch.object(ollama.requests, "post", return_value=response) as post:
        assert ollama.post_json("/api/generate", {"stream": False}) == {"response": "answer"}

    post.assert_called_once_with(
        url="http://ollama:11434/api/generate", json={"stream": False}, timeout=3.0,
    )


def test_post_json_classifies_timeouts_and_unavailable_service():
    with patch.object(ollama.requests, "post", side_effect=requests.Timeout):
        with pytest.raises(ollama.OllamaTimeout):
            ollama.post_json("/api/generate", {})

    response = Mock(status_code=503)
    with patch.object(ollama.requests, "post", return_value=response):
        with pytest.raises(ollama.OllamaUnavailable, match="503"):
            ollama.post_json("/api/generate", {})


def test_post_json_rejects_malformed_success_payload():
    response = Mock(status_code=200)
    response.json.return_value = []
    with patch.object(ollama.requests, "post", return_value=response):
        with pytest.raises(ollama.OllamaInvalidResponse):
            ollama.post_json("/api/generate", {})


def test_ollama_classifies_timeout_while_reading_response_body(monkeypatch):
    release = Event()

    class DelayedBody(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.flush()
            release.wait(timeout=2)

        do_POST = do_GET

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), DelayedBody)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("OLLAMA_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        with pytest.raises(ollama.OllamaTimeout):
            ollama.post_json("/api/embed", {}, timeout=0.05)
        with pytest.raises(ollama.OllamaTimeout):
            ollama.get_json("/api/tags", timeout=0.05)
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
