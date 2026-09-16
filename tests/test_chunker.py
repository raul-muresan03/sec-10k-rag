import json
from unittest.mock import Mock, call, patch

import pytest

from etl_pipeline import chunker


def test_similarity_score_handles_equal_orthogonal_and_zero_vectors():
    assert chunker.get_similarity_score([1.0, 2.0], [1.0, 2.0]) == pytest.approx(1.0)
    assert chunker.get_similarity_score([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert chunker.get_similarity_score([0.0, 0.0], [1.0, 0.0]) == -2


def test_paragraphs_to_embeddings_sends_batch_to_ollama():
    response = Mock(status_code=200)
    response.json.return_value = {"embeddings": [[1.0, 0.0], [0.0, 1.0]]}

    with patch.object(chunker.requests, "post", return_value=response) as post:
        embeddings = chunker.paragraphs_to_embeddings(["first", "second"])

    assert embeddings == [[1.0, 0.0], [0.0, 1.0]]
    post.assert_called_once_with(
        url="http://localhost:11434/api/embed",
        json={"model": "nomic-embed-text", "input": ["first", "second"]},
    )


def test_paragraphs_to_embeddings_rejects_failed_request():
    response = Mock(status_code=500)

    with patch.object(chunker.requests, "post", return_value=response):
        with pytest.raises(RuntimeError, match="status 500"):
            chunker.paragraphs_to_embeddings(["paragraph"])


def test_paragraphs_to_embeddings_rejects_incomplete_response():
    response = Mock(status_code=200)
    response.json.return_value = {"embeddings": [[1.0, 0.0]]}

    with patch.object(chunker.requests, "post", return_value=response):
        with pytest.raises(RuntimeError, match="does not match batch size"):
            chunker.paragraphs_to_embeddings(["first", "second"])


def test_embedding_batches_include_final_partial_batch(monkeypatch):
    paragraphs = ["one", "two", "three", "four", "five"]
    embed = Mock(side_effect=lambda batch: [[float(len(text))] for text in batch])
    monkeypatch.setattr(chunker, "EMBEDDING_BATCH_SIZE", 2)
    monkeypatch.setattr(chunker, "paragraphs_to_embeddings", embed)
    monkeypatch.setattr("builtins.print", Mock())

    embeddings = chunker._get_all_vector_embeddings(paragraphs)

    assert embeddings == [[3.0], [3.0], [5.0], [4.0], [4.0]]
    assert embed.call_args_list == [call(["one", "two"]), call(["three", "four"]), call(["five"])]


def test_chunk_10k_groups_similar_adjacent_paragraphs(data_directory, monkeypatch):
    source = data_directory / "cleaned.txt"
    source.write_text("first\n\nsecond\n\nthird")
    monkeypatch.setattr(
        chunker,
        "_get_all_vector_embeddings",
        Mock(side_effect=[
            [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
            [[1.0, 0.0], [0.0, 1.0]],
        ]),
    )

    chunks = chunker.chunk_10K(str(source))
    paragraph_embeddings = json.loads((data_directory / "all_embeddings.json").read_text())
    chunk_data = json.loads((data_directory / "all_chunks_embeddings.json").read_text())

    assert chunks == ["first second", "third"]
    assert paragraph_embeddings == [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    assert chunk_data["chunks"] == chunks
    assert chunk_data["embeddings"] == [[1.0, 0.0], [0.0, 1.0]]


@pytest.mark.xfail(strict=True, reason="Current chunker can exceed the 10,000 character limit")
def test_chunk_10k_does_not_exceed_character_limit(data_directory, monkeypatch):
    first = "a" * 6_000
    second = "b" * 6_000
    source = data_directory / "cleaned.txt"
    source.write_text(f"{first}\n\n{second}")
    monkeypatch.setattr(
        chunker,
        "_get_all_vector_embeddings",
        Mock(side_effect=lambda texts: [[1.0, 0.0] for _ in texts]),
    )

    chunks = chunker.chunk_10K(str(source))

    assert all(len(chunk) <= 10_000 for chunk in chunks)


@pytest.mark.xfail(strict=True, reason="Current chunker raises IndexError for empty documents")
def test_chunk_10k_returns_empty_list_for_empty_document(data_directory, monkeypatch):
    source = data_directory / "empty.txt"
    source.write_text("")
    monkeypatch.setattr(chunker, "_get_all_vector_embeddings", Mock(return_value=[]))

    assert chunker.chunk_10K(str(source)) == []
