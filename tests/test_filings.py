import json

import pytest

from etl_pipeline.filings import filing_id, verify_filings
from tests.eval_helpers import make_question, write_manifest


def test_verified_sec_identity_uses_cik_and_accession(tmp_path):
    manifest_path = write_manifest(tmp_path, [make_question()])
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["filings"][0]
    accession = entry["accession"]
    entry["sec_url"] = (
        f"https://www.sec.gov/Archives/edgar/data/0/{accession.replace('-', '')}/{accession}.txt"
    )
    manifest_path.write_text(json.dumps(manifest))

    filing = verify_filings(manifest_path, {("NVDA", 2026)}, "dev")[2][("NVDA", 2026)]

    assert filing_id(filing) == f"0-{accession}"
    manifest["filings"][0]["sec_url"] = entry["sec_url"].replace("/data/0/", "/data/123/")
    manifest_path.write_text(json.dumps(manifest))
    wrong = verify_filings(manifest_path, {("NVDA", 2026)}, "dev")[2][("NVDA", 2026)]
    with pytest.raises(ValueError, match="Invalid SEC identity"):
        filing_id(wrong)
