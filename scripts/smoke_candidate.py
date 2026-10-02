"""Pre-promotion smoke checks for a staged production candidate.

Reads nothing but the candidate URL and the repository snapshot manifest.
Never prints credentials: only the candidate host appears in output.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEV_FILING_ID = "1045810-0001045810-26-000021"
DEV_QUESTION = "How does NVIDIA assign revenue geographically?"
EXPECTED_MODEL = "openai/gpt-oss-20b"
TIMEOUT_SECONDS = 30


def candidate_url(base: str, path: str, bypass_token: str = "") -> str:
    url = base.rstrip("/") + path
    if not bypass_token:
        return url
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query)
    query.append(("x-vercel-protection-bypass", bypass_token))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def fetch(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read())
        except ValueError:
            return error.code, {"unparsed": True}


def validate_health(payload: object) -> None:
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise ValueError("Candidate health check failed")


def validate_ready(payload: object, snapshot_id: str) -> None:
    if not isinstance(payload, dict) or payload.get("status") != "ready":
        raise ValueError("Candidate is not ready")
    if payload.get("snapshot_id") != snapshot_id:
        raise ValueError("Candidate snapshot does not match the repository export")


def validate_filings(payload: object) -> list[str]:
    if not isinstance(payload, list) or len(payload) != 6:
        raise ValueError("Candidate catalog must contain exactly six filings")
    if any(not isinstance(entry, dict) or entry.get("status") != "ready" for entry in payload):
        raise ValueError("Candidate catalog contains an unprepared filing")
    filing_ids = [entry["filing_id"] for entry in payload]
    if len(set(filing_ids)) != 6:
        raise ValueError("Candidate catalog contains duplicate filings")
    return filing_ids


def validate_prepare_refused(status: int) -> None:
    if status != 403:
        raise ValueError(f"Candidate preparation endpoint returned {status}, expected 403")


def validate_chat(payload: object, filing_id: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Candidate chat returned an invalid payload")
    if payload.get("filing_id") != filing_id or payload.get("model") != EXPECTED_MODEL:
        raise ValueError("Candidate chat identity or model mismatch")
    if not isinstance(payload.get("answer"), str) or not payload["answer"].strip():
        raise ValueError("Candidate chat returned a blank answer")


def validate_private(status: int, path: str) -> None:
    if status != 404:
        raise ValueError(f"Candidate exposes {path} with HTTP {status}")


def repository_snapshot_id() -> str:
    manifest = json.loads((PROJECT_ROOT / "deploy" / "indexes" / "manifest.json").read_text())
    return manifest["snapshot_id"]


def run_checks(base: str, snapshot_id: str, bypass_token: str, quick: bool) -> None:
    host = urllib.parse.urlsplit(base).netloc
    url = lambda path: candidate_url(base, path, bypass_token)  # noqa: E731

    status, payload = fetch(url("/api/health"))
    validate_health(payload)
    print(f"PASS health on {host}")

    status, payload = fetch(url("/api/ready"))
    validate_ready(payload, snapshot_id)
    print(f"PASS ready with snapshot {snapshot_id[:12]} on {host}")

    status, payload = fetch(url("/api/filings"))
    filing_ids = validate_filings(payload)
    print(f"PASS six ready filings on {host}")

    status, _ = fetch(url(f"/api/filings/{filing_ids[0]}/prepare"), method="POST", payload={})
    validate_prepare_refused(status)
    print(f"PASS preparation refused on {host}")

    status, _ = fetch(url("/deploy/indexes/manifest.json"))
    validate_private(status, "/deploy/indexes/manifest.json")
    print(f"PASS snapshot export is not a web asset on {host}")

    if quick:
        return
    status, payload = fetch(url("/api/chat"), method="POST",
                            payload={"filing_id": DEV_FILING_ID, "question": DEV_QUESTION})
    if status != 200:
        raise ValueError(f"Candidate chat returned HTTP {status}")
    validate_chat(payload, DEV_FILING_ID)
    print(f"PASS live dev chat on {host}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a staged production candidate.")
    parser.add_argument("--url", required=True, help="Staged candidate base URL (no traffic until promoted)")
    parser.add_argument("--snapshot", default="",
                        help="Expected snapshot ID (default: the repository export manifest)")
    parser.add_argument("--bypass-token", default="",
                        help="Vercel protection-bypass token for candidates behind deployment protection")
    parser.add_argument("--quick", action="store_true", help="Skip the live chat check to preserve quota")
    args = parser.parse_args(argv)
    try:
        run_checks(args.url, args.snapshot or repository_snapshot_id(), args.bypass_token, args.quick)
    except (OSError, ValueError) as error:
        print(f"FAIL {error}")
        return 1
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
