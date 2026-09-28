"""Fetch a manifest-pinned SEC submission without publishing partial or unverified bytes."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

from etl_pipeline.filings import VerifiedFiling, verify_file


def download_verified(filing: VerifiedFiling) -> Path:
    if filing.path.exists():
        try:
            verify_file(filing, filing.path)
            return filing.path
        except ValueError:
            pass
    email = os.getenv("SEC_API_EMAIL", "").strip()
    if not email or email == "your_email@example.com":
        raise ValueError("Set SEC_API_EMAIL to your contact address in .env before preparing a filing")
    filing.path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with requests.get(
            filing.sec_url, headers={"User-Agent": f"SEC RAG Tool {email}"}, stream=True, timeout=(10, 60),
        ) as response:
            response.raise_for_status()
            with NamedTemporaryFile(dir=filing.path.parent, prefix=".download-", delete=False) as target:
                temporary = Path(target.name)
                size = 0
                for block in response.iter_content(chunk_size=1024 * 1024):
                    size += len(block)
                    if size > 150 * 1024 * 1024:
                        raise ValueError("SEC filing exceeds the 150 MiB download limit")
                    target.write(block)
        verify_file(filing, temporary)
        os.replace(temporary, filing.path)
        return filing.path
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
