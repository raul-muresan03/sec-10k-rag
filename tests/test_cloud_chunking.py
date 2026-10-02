import json

import httpx
import pytest

from etl_pipeline.cloud_chunker import chunk_document


def test_cloud_chunks_split_a_long_paragraph_before_embedding(cloud_config, cloud_http):
    def respond(request):
        texts = json.loads(request.content)["text"]
        assert all(len(text.split()) <= 480 for text in texts)
        return httpx.Response(200, json={
            "success": True, "result": {"data": [[1.0] + [0.0] * 383 for _ in texts]},
        })

    cloud_http(respond)
    chunks, vectors = chunk_document("revenue " * 481, cloud_config)
    assert [len(chunk.split()) for chunk in chunks] == [480, 1]
    assert "".join(chunks) == "revenue " * 481
    assert len(vectors) == 2


@pytest.mark.parametrize("first, second, expected", [(240, 240, [480]), (240, 241, [240, 241])])
def test_cloud_semantic_merges_also_obey_the_token_budget(cloud_config, cloud_http, first, second, expected):
    cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"data": [
            [1.0] + [0.0] * 383 for _ in json.loads(request.content)["text"]
        ]},
    }))
    chunks, _ = chunk_document("revenue " * first + "\n\n" + "income " * second, cloud_config)
    assert [len(chunk.split()) for chunk in chunks] == expected


@pytest.mark.parametrize("text, count", [("revenue", 101), ("revenue " * 480, 30), ("中" * 481, 1)])
def test_cloud_chunking_bounds_batches_and_preserves_unicode(cloud_config, cloud_http, text, count):
    from etl_pipeline.cloud_tokens import token_count

    def respond(request):
        texts = json.loads(request.content)["text"]
        assert len(texts) <= 100
        assert sum(token_count(item) for item in texts) <= 8192
        assert all(token_count(item) <= 482 for item in texts)
        return httpx.Response(200, json={
            "success": True, "result": {"data": [[1.0] + [0.0] * 383 for _ in texts]},
        })

    calls = cloud_http(respond)
    chunks, vectors = chunk_document("\n\n".join([text] * count), cloud_config)
    assert len(chunks) == len(vectors)
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "") * count
    assert calls
