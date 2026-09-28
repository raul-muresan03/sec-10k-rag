"""Verify manifest-listed SEC submissions before indexing."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "eval" / "corpus_manifest.v1.json"
ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
SEC_URL = re.compile(
    r"https://www\.sec\.gov/Archives/edgar/data/(?P<cik>[0-9]+)/(?P<archive>[0-9]{18})/"
    r"(?P<accession>[0-9]{10}-[0-9]{2}-[0-9]{6})\.txt"
)


@dataclass(frozen=True)
class VerifiedFiling:
    ticker: str
    year: int
    split: str
    accession: str
    path: Path
    sha256: str
    sec_url: str | None = None


def filing_id(filing: VerifiedFiling) -> str:
    match = SEC_URL.fullmatch(filing.sec_url or "")
    if (
        match is None
        or match["accession"] != filing.accession
        or match["archive"] != filing.accession.replace("-", "")
        or int(match["cik"]) != int(filing.accession[:10])
    ):
        raise ValueError(f"Invalid SEC identity for {filing.ticker} {filing.year}")
    return f"{match['cik']}-{filing.accession}"


def hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def catalog_filings(manifest_path: Path, split: str = "dev") -> dict[str, VerifiedFiling]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or not isinstance(manifest.get("filings"), list):
        raise ValueError("Invalid v1 corpus manifest")
    catalog = {}
    for entry in manifest["filings"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid filing in corpus manifest")
        if entry.get("split") != split:
            continue
        try:
            ticker, year, accession = entry["ticker"], entry["filing_year"], entry["accession"]
            path, digest, url = entry["path"], entry["sha256"], entry["sec_url"]
        except KeyError as error:
            raise ValueError(f"Missing manifest field: {error.args[0]}") from error
        expected = f"data/sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt"
        if (
            not isinstance(ticker, str) or type(year) is not int
            or not isinstance(accession, str) or not ACCESSION.fullmatch(accession)
            or path != expected or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not isinstance(url, str)
        ):
            raise ValueError(f"Invalid manifest entry for {ticker} {year}")
        filing = VerifiedFiling(ticker, year, split, accession, manifest_path.parent.parent / path, digest, url)
        selected_id = filing_id(filing)
        if selected_id in catalog:
            raise ValueError(f"Duplicate filing ID: {selected_id}")
        catalog[selected_id] = filing
    if not catalog:
        raise ValueError(f"No {split} filings in corpus manifest")
    return catalog


def verify_file(filing: VerifiedFiling, path: Path) -> None:
    if hash_file(path) != filing.sha256:
        raise ValueError(f"Filing SHA-256 mismatch for {filing.ticker} {filing.year}: {path}")
    with path.open("r", encoding="utf-8", errors="replace") as source:
        header = source.read(16_384)
    fields = {
        label: re.search(rf"^{label}:\s*([^\r\n]+)", header, flags=re.MULTILINE)
        for label in ("ACCESSION NUMBER", "CONFORMED SUBMISSION TYPE", "FILED AS OF DATE")
    }
    if (
        any(match is None for match in fields.values())
        or fields["ACCESSION NUMBER"].group(1).strip() != filing.accession
        or fields["CONFORMED SUBMISSION TYPE"].group(1).strip() != "10-K"
        or fields["FILED AS OF DATE"].group(1).strip()[:4] != str(filing.year)
    ):
        raise ValueError(f"SEC header accession/form/filing year mismatch for {filing.ticker} {filing.year}: {path}")


def verify_filings(
    manifest_path: Path, keys: set[tuple[str, int]], split: str,
) -> tuple[int, str, dict[tuple[str, int], VerifiedFiling]]:
    manifest_path = manifest_path.resolve()
    manifest_hash = hash_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("version")) is not int
        or manifest["version"] != 1
        or not isinstance(manifest.get("filings"), list)
    ):
        raise ValueError(f"Invalid v1 corpus manifest: {manifest_path}")

    root = manifest_path.parent.parent
    selected = {}
    for entry in manifest["filings"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid filing in corpus manifest")
        try:
            ticker, year = entry["ticker"], entry["filing_year"]
            accession, entry_split = entry["accession"], entry["split"]
            relative_path, expected_hash = entry["path"], entry["sha256"]
        except KeyError as error:
            raise ValueError(f"Missing manifest field: {error.args[0]}") from error
        if not isinstance(ticker, str) or type(year) is not int:
            raise ValueError("Invalid ticker/year in corpus manifest")
        key = (ticker, year)
        if key not in keys:
            continue
        if key in selected:
            raise ValueError(f"Duplicate filing in corpus manifest: {key}")
        if entry_split != split:
            raise ValueError(f"Split mismatch for {ticker} {year}: manifest has {entry_split}, expected {split}")
        expected_path = f"data/sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt"
        if (
            not isinstance(accession, str)
            or not ACCESSION.fullmatch(accession)
            or relative_path != expected_path
            or not isinstance(expected_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        ):
            raise ValueError(f"Invalid accession/path/hash in manifest for {ticker} {year}")
        path = root / relative_path
        if not path.is_file():
            raise ValueError(f"Filing missing for {ticker} {year}: {path}")
        sec_url = entry.get("sec_url")
        if sec_url is not None and (not isinstance(sec_url, str) or not SEC_URL.fullmatch(sec_url)):
            raise ValueError(f"Invalid SEC source URL for {ticker} {year}")
        filing = VerifiedFiling(ticker, year, split, accession, path, expected_hash, sec_url)
        verify_file(filing, path)
        selected[key] = filing

    missing = keys - selected.keys()
    if missing:
        raise ValueError(f"No manifest filing for: {sorted(missing)}")
    if hash_file(manifest_path) != manifest_hash:
        raise ValueError(f"Corpus manifest changed while verifying: {manifest_path}")
    return manifest["version"], manifest_hash, selected
