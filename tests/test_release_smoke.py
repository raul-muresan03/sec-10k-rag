"""Validator seams of the pre-promotion candidate smoke script."""

import pytest

from scripts.smoke_candidate import (
    candidate_url, validate_chat, validate_filings, validate_health,
    validate_prepare_refused, validate_private, validate_ready,
)


def test_health_and_ready_accept_only_matching_payloads():
    validate_health({"status": "ok"})
    validate_ready({"status": "ready", "snapshot_id": "a" * 64}, "a" * 64)
    with pytest.raises(ValueError):
        validate_health({"status": " broken"})
    with pytest.raises(ValueError):
        validate_ready({"status": "ready", "snapshot_id": "b" * 64}, "a" * 64)


def test_filings_require_six_unique_ready_entries():
    entries = [{"filing_id": f"id-{number}", "status": "ready"} for number in range(6)]
    assert validate_filings(entries) == [f"id-{number}" for number in range(6)]
    for broken in (entries[:5], entries[:-1] + [{"filing_id": "id-0", "status": "ready"}],
                   entries[:-1] + [{"filing_id": "id-5", "status": "queued"}]):
        with pytest.raises(ValueError):
            validate_filings(broken)


def test_prepare_chat_and_privacy_gates():
    validate_prepare_refused(403)
    validate_private(404, "/deploy/indexes/manifest.json")
    validate_chat({"filing_id": "filing", "model": "openai/gpt-oss-20b", "answer": "Grounded"}, "filing")
    with pytest.raises(ValueError):
        validate_prepare_refused(200)
    with pytest.raises(ValueError):
        validate_private(200, "/deploy/indexes/manifest.json")
    with pytest.raises(ValueError):
        validate_chat({"filing_id": "other", "model": "openai/gpt-oss-20b", "answer": "x"}, "filing")


def test_bypass_token_never_leaks_into_plain_urls():
    plain = candidate_url("https://candidate.example", "/api/health")
    assert plain == "https://candidate.example/api/health"
    assert "token" not in plain
