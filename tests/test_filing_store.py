import json

import pytest

from etl_pipeline import filing_store
from etl_pipeline.filings import filing_id, hash_file
from tests.eval_helpers import make_question, write_manifest


@pytest.fixture
def store(tmp_path, monkeypatch):
    questions = [
        make_question("nvda-dev"),
        make_question("amzn-dev", ticker="AMZN", year=2021),
        make_question("aapl-test", ticker="AAPL", year=2024, split="test"),
    ]
    manifest_path = write_manifest(tmp_path, questions)
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["filings"]:
        accession = entry["accession"]
        entry["sec_url"] = (
            f"https://www.sec.gov/Archives/edgar/data/0/{accession.replace('-', '')}/{accession}.txt"
        )
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(filing_store, "embedding_model_digest", lambda _: "a" * 64)
    return filing_store.FilingIndexStore(manifest_path, tmp_path / "indexes")


def write_prepared(store, filing, config):
    directory = store._directory(filing, config)
    directory.mkdir(parents=True)
    index_path = directory / "all_chunks_embeddings.json"
    index_path.write_text(json.dumps({"chunks": [filing.ticker], "embeddings": [[1.0, 0.0]]}))
    metadata = {
        "schema_version": 1, "filing_id": filing_id(filing), "ticker": filing.ticker,
        "filing_year": filing.year, "accession": filing.accession, "sec_url": filing.sec_url,
        "source_sha256": filing.sha256, "index_version": directory.name,
        "index_configuration": config, "index_sha256": hash_file(index_path), "chunk_count": 1,
    }
    (directory / "filing.json").write_text(json.dumps(metadata))
    return index_path


def test_catalog_lists_only_verified_dev_indexes(store):
    digest, filings = store.dev_filings()
    assert digest
    assert set(filings) == {("NVDA", 2026), ("AMZN", 2021)}
    assert store.prepared() == []
    filing = filings[("NVDA", 2026)]
    index_path = write_prepared(store, filing, filing_store._configuration())

    assert [item.filing_id for item in store.prepared()] == [filing_id(filing)]
    assert store.resolve("nvda", 2026).index_path == index_path
    with pytest.raises(ValueError, match="Split mismatch"):
        store.resolve("AAPL", 2024)


def test_catalog_rejects_tampered_index_and_metadata(store):
    _, filings = store.dev_filings()
    filing = filings[("NVDA", 2026)]
    path = write_prepared(store, filing, filing_store._configuration())
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        store.resolve("NVDA", 2026)

    metadata_path = path.parent / "filing.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["ticker"] = "AMZN"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="metadata does not match"):
        store.resolve("NVDA", 2026)


def test_changed_model_digest_selects_a_distinct_index(store, monkeypatch):
    _, filings = store.dev_filings()
    filing = filings[("NVDA", 2026)]
    path = write_prepared(store, filing, filing_store._configuration())
    monkeypatch.setattr(filing_store, "embedding_model_digest", lambda _: "b" * 64)

    assert store.prepared() == []
    with pytest.raises(RuntimeError, match="not prepared"):
        store.resolve("NVDA", 2026)
    assert path.exists()
