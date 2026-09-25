import json
from hashlib import sha256


def make_question(
    question_id="q1",
    question_type="narrative",
    evidence=None,
    answer="expected",
    ticker="NVDA",
    year=2026,
    split="dev",
):
    return {
        "id": question_id,
        "split": split,
        "ticker": ticker,
        "year": year,
        "type": question_type,
        "question": f"Question {question_id}?",
        "answer": answer,
        "section": "Item 1" if answer is not None else None,
        "evidence": evidence if evidence is not None else ["Expected evidence"],
    }


def write_questions(path, questions):
    path.write_text("".join(json.dumps(question) + "\n" for question in questions))


def write_manifest(tmp_path, questions):
    entries = []
    for ticker, year, split in {(q["ticker"], q["year"], q["split"]) for q in questions}:
        accession = f"0000000000-{str(year)[-2:]}-000001"
        relative = f"data/sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt"
        source = tmp_path / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            f"ACCESSION NUMBER: {accession}\nCONFORMED SUBMISSION TYPE: 10-K\n"
            f"FILED AS OF DATE: {year}0101\n<DOCUMENT>10-K</DOCUMENT>\n"
        )
        entries.append({
            "ticker": ticker, "filing_year": year, "split": split,
            "accession": accession, "path": relative,
            "sha256": sha256(source.read_bytes()).hexdigest(),
        })
    manifest_path = tmp_path / "eval" / "corpus_manifest.v1.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"version": 1, "filings": entries}))
    return manifest_path
