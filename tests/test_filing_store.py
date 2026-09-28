import json

import pytest

from etl_pipeline import filing_store
from etl_pipeline import vector_store
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


def test_catalog_remains_available_with_missing_sources_and_preserves_ready_filing(store):
    _, filings = store.dev_filings()
    nvda = filings[("NVDA", 2026)]
    filings[("AMZN", 2021)].path.unlink()
    write_prepared(store, nvda, filing_store._configuration())

    assert {filing.ticker for filing in store.catalog().values()} == {"NVDA", "AMZN"}
    assert [filing.ticker for filing in store.prepared()] == ["NVDA"]
    assert store.resolve_id(filing_id(nvda)).ticker == "NVDA"
    with pytest.raises(ValueError, match="Filing missing"):
        store.resolve("AMZN", 2021)


def test_resolve_id_selects_only_a_prepared_dev_filing(store):
    _, filings = store.dev_filings()
    filing = filings[("NVDA", 2026)]
    path = write_prepared(store, filing, filing_store._configuration())

    assert store.resolve_id(filing_id(filing)).index_path == path
    with pytest.raises(KeyError):
        store.resolve_id("unknown-filing")
    with pytest.raises(KeyError):
        store.resolve_id("0-0000000000-24-000001")


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


def test_prepare_dev_isolates_interleaved_queries_and_reuses_indexes(store, monkeypatch):
    built = []

    def build(filing, directory):
        built.append(filing.ticker)
        path = directory / "all_chunks_embeddings.json"
        path.write_text(json.dumps({"chunks": [filing.ticker], "embeddings": [[1.0, 0.0]]}))
        return {"sha256": hash_file(path), "chunk_count": 1}

    monkeypatch.setattr(filing_store, "build_index", build)
    first, second = store.prepare_dev()
    assert built == ["AMZN", "NVDA"]
    assert first.index_path != second.index_path
    assert {item.ticker for item in store.prepared()} == {"AMZN", "NVDA"}
    monkeypatch.setattr(vector_store, "text_to_embedding", lambda _: [1.0, 0.0])
    for filing in (first, second, first):
        assert vector_store.get_most_similar_chunks("question", 1, filing.index_path)[0][1] == filing.ticker

    reopened = filing_store.FilingIndexStore(store.manifest_path, store.index_root)
    assert [item.index_path for item in reopened.prepare_dev()] == [first.index_path, second.index_path]
    assert reopened.prepare_selected("nvda", 2026).index_path == second.index_path
    with pytest.raises(ValueError, match="Split mismatch"):
        reopened.prepare_selected("AAPL", 2024)
    assert built == ["AMZN", "NVDA"]


def test_failed_build_leaves_existing_filing_ready_and_no_partial_index(store, monkeypatch):
    _, filings = store.dev_filings()
    config = filing_store._configuration()
    existing = write_prepared(store, filings[("NVDA", 2026)], config)

    def fail(filing, directory):
        (directory / "partial.txt").write_text("unfinished")
        raise RuntimeError("interrupted")

    monkeypatch.setattr(filing_store, "build_index", fail)
    with pytest.raises(RuntimeError, match="interrupted"):
        store.prepare_dev()
    assert store.resolve("NVDA", 2026).index_path == existing
    with pytest.raises(RuntimeError, match="not prepared"):
        store.resolve("AMZN", 2021)
    assert not list(store.index_root.rglob(".building-*"))


def test_model_change_during_build_cannot_publish_index(store, monkeypatch):
    _, filings = store.dev_filings()
    config = filing_store._configuration()
    path = store._directory(filings[("NVDA", 2026)], config)

    def build(filing, directory):
        index_path = directory / "all_chunks_embeddings.json"
        index_path.write_text(json.dumps({"chunks": ["NVDA"], "embeddings": [[1.0]]}))
        monkeypatch.setattr(filing_store, "embedding_model_digest", lambda _: "b" * 64)
        return {"sha256": hash_file(index_path), "chunk_count": 1}

    monkeypatch.setattr(filing_store, "build_index", build)
    with pytest.raises(RuntimeError, match="model changed"):
        store.prepare(filings[("NVDA", 2026)], "manifest-sha", config)
    assert not path.exists()


def test_replacing_model_under_the_same_tag_builds_another_version(store, monkeypatch):
    def build(filing, directory):
        path = directory / "all_chunks_embeddings.json"
        path.write_text(json.dumps({"chunks": [filing.ticker], "embeddings": [[1.0, 0.0]]}))
        return {"sha256": hash_file(path), "chunk_count": 1}

    monkeypatch.setattr(filing_store, "build_index", build)
    old = store.prepare_selected("NVDA", 2026)
    monkeypatch.setattr(filing_store, "embedding_model_digest", lambda _: "b" * 64)
    new = store.prepare_selected("NVDA", 2026)

    assert new.index_path != old.index_path
    assert old.index_path.is_file() and new.index_path.is_file()
    assert store.resolve("NVDA", 2026).index_path == new.index_path
    metadata = json.loads((new.index_path.parent / "filing.json").read_text())
    assert metadata["index_configuration"]["embedding_model"] == {
        "tag": "nomic-embed-text", "digest": "b" * 64,
    }
