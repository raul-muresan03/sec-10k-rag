"""Synthetic dev filings exercised through real preparation and retrieval interfaces."""

from hashlib import sha256
import json

from etl_pipeline.filing_store import FilingIndexStore


def filing_corpus(root, split: str = "dev"):
    entries = []
    for ticker, year in (("NVDA", 2026), ("F", 2014)):
        accession = f"0000000000-{str(year)[-2:]}-000001"
        relative = f"data/sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt"
        source = root / relative
        source.parent.mkdir(parents=True)
        source.write_text(
            f"ACCESSION NUMBER: {accession}\nCONFORMED SUBMISSION TYPE: 10-K\nFILED AS OF DATE: {year}0101\n"
            f"<DOCUMENT><TYPE>10-K\n<TEXT><div>{ticker} evidence</div></TEXT></DOCUMENT>"
        )
        entries.append({
            "ticker": ticker, "filing_year": year, "split": split, "accession": accession,
            "path": relative, "sha256": sha256(source.read_bytes()).hexdigest(),
            "sec_url": f"https://www.sec.gov/Archives/edgar/data/0/{accession.replace('-', '')}/{accession}.txt",
        })
    manifest = root / "eval" / "corpus_manifest.v1.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"version": 1, "filings": entries}))
    return FilingIndexStore(manifest, root / "indexes")
