from hashlib import sha256

import pytest

import etl_pipeline
from etl_pipeline import chunker, indexing, vector_store
from etl_pipeline.filings import VerifiedFiling


def make_filing(tmp_path):
    source = tmp_path / "submission.txt"
    source.write_text(
        "ACCESSION NUMBER: 0001045810-26-000021\n"
        "CONFORMED SUBMISSION TYPE: 10-K\n"
        "FILED AS OF DATE: 20260125\n"
        "<DOCUMENT><TYPE>10-K\n<TEXT><html><body>"
        "<div>Revenue was $10 billion.</div><div>Gross margin rose.</div>"
        "</body></html></TEXT></DOCUMENT>"
    )
    return VerifiedFiling(
        "NVDA", 2026, "dev", "0001045810-26-000021", source,
        sha256(source.read_bytes()).hexdigest(),
    )


def test_build_index_writes_only_to_selected_workspace(tmp_path, monkeypatch):
    filing = make_filing(tmp_path)
    workspace = tmp_path / "nvda-workspace"
    workspace.mkdir()
    active_dir = etl_pipeline.DATA_DIR
    monkeypatch.setattr(chunker, "_get_all_vector_embeddings", lambda texts: [[1.0, 0.0] for _ in texts])

    metadata = indexing.build_index(filing, workspace)

    assert etl_pipeline.DATA_DIR == active_dir
    assert metadata["sha256"] == sha256((workspace / indexing.INDEX_FILENAME).read_bytes()).hexdigest()
    assert metadata["chunk_count"] > 0
    chunks, embeddings = vector_store.load_index(workspace / indexing.INDEX_FILENAME)
    assert len(chunks) == len(embeddings)
    assert "Revenue was $10 billion" in " ".join(chunks)
    assert (workspace / "output_parser.txt").exists()
    assert (workspace / "output_cleaner.txt").exists()


def test_build_index_stops_when_verified_source_changes(tmp_path):
    filing = make_filing(tmp_path)
    filing.path.write_text(filing.path.read_text() + "tampered")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with pytest.raises(ValueError, match="changed before indexing"):
        indexing.build_index(filing, workspace)
    assert not list(workspace.iterdir())
