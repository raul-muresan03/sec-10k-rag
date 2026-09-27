import json
from unittest.mock import patch

import pytest

from etl_pipeline import vector_store


def write_vector_store(data_directory):
    payload = {
        "chunks": ["horizontal evidence", "vertical evidence", "diagonal evidence"],
        "embeddings": [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
    }
    (data_directory / "all_chunks_embeddings.json").write_text(json.dumps(payload))


@pytest.fixture(autouse=True)
def clear_prompt_cache():
    vector_store.prompt_cache.clear()
    yield
    vector_store.prompt_cache.clear()


def test_retrieval_returns_highest_similarity_chunks_first(data_directory, monkeypatch):
    write_vector_store(data_directory)
    monkeypatch.setattr(vector_store, "text_to_embedding", lambda _: [0.0, 1.0])

    results = vector_store.get_most_similar_chunks("question", top_n=2)

    assert [result[1] for result in results] == ["vertical evidence", "diagonal evidence"]
    assert results[0][0] == pytest.approx(1.0)
    assert results[0][0] > results[1][0]


def test_retrieval_uses_only_the_selected_filing_index(data_directory, monkeypatch):
    first = data_directory / "first.json"
    second = data_directory / "second.json"
    for path, text in ((first, "first filing"), (second, "second filing")):
        path.write_text(json.dumps({"chunks": [text], "embeddings": [[1.0, 0.0]]}))
    monkeypatch.setattr(vector_store, "text_to_embedding", lambda _: [1.0, 0.0])

    for path, expected in ((first, "first filing"), (second, "second filing"), (first, "first filing")):
        results = vector_store.get_most_similar_chunks("same question", top_n=1, index_path=path)
        assert [text for _, text in results] == [expected]


def test_retrieval_normalizes_prompt_before_embedding(data_directory, monkeypatch):
    write_vector_store(data_directory)
    embed = patch.object(vector_store, "text_to_embedding", return_value=[1.0, 0.0])

    with embed as mock_embed:
        vector_store.get_most_similar_chunks("  NVIDIA Revenue  ", top_n=1)

    mock_embed.assert_called_once_with("nvidia revenue")


def test_retrieval_reuses_cached_prompt_embedding(data_directory):
    write_vector_store(data_directory)

    with patch.object(vector_store, "text_to_embedding", return_value=[1.0, 0.0]) as embed:
        first = vector_store.get_most_similar_chunks(" NVIDIA Revenue ", top_n=1)
        second = vector_store.get_most_similar_chunks("nvidia revenue", top_n=1)

    assert first == second
    embed.assert_called_once_with("nvidia revenue")
    assert "nvidia revenue" in vector_store.prompt_cache


def test_retrieval_uses_existing_prompt_cache_entry(data_directory):
    write_vector_store(data_directory)
    vector_store.prompt_cache["cached question"] = [0.0, 1.0]

    with patch.object(vector_store, "text_to_embedding") as embed:
        results = vector_store.get_most_similar_chunks("cached question", top_n=1)

    embed.assert_not_called()
    assert results[0][1] == "vertical evidence"


def test_retrieval_rejects_inconsistent_index_dimensions(data_directory, monkeypatch):
    path = data_directory / "bad.json"
    path.write_text(json.dumps({"chunks": ["one", "two"], "embeddings": [[1.0, 0.0], [1.0]]}))
    monkeypatch.setattr(vector_store, "text_to_embedding", lambda _: [1.0, 0.0])

    with pytest.raises(ValueError, match="embedding dimensions"):
        vector_store.get_most_similar_chunks("question", 1, path)


def test_retrieval_rejects_inconsistent_question_dimension(data_directory, monkeypatch):
    path = data_directory / "all_chunks_embeddings.json"
    write_vector_store(data_directory)
    monkeypatch.setattr(vector_store, "text_to_embedding", lambda _: [1.0])

    with pytest.raises(ValueError, match="Question embedding dimension"):
        vector_store.get_most_similar_chunks("question", 1, path)
