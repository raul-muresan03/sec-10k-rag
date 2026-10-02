from dataclasses import replace
import json
import time

import httpx
import pytest

from etl_pipeline.cloud_indexing import prepare_snapshot
from etl_pipeline.model_errors import ModelTimeout
from etl_pipeline.runtime_snapshot import SnapshotStore
from etl_pipeline.snapshot_query import query_snapshot


def test_expired_query_budget_is_rejected_before_embedding_or_cache(runtime_export, cloud_config, cloud_http):
    store = SnapshotStore(runtime_export)
    calls = cloud_http(lambda request: pytest.fail("Expired query contacted a provider"))
    with pytest.raises(ModelTimeout):
        query_snapshot(store, store.resolve("F", 2014).filing_id, "Expired?", 5, cloud_config,
                       deadline=time.monotonic() - 1)
    assert not calls


def test_question_embedding_cache_is_isolated_by_snapshot(
    runtime_export, local_corpus, cloud_config, cloud_http, tmp_path,
):
    cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"data": [
            [0.0, 1.0] + [0.0] * 382 for _ in json.loads(request.content)["text"]
        ]},
    }))
    second = prepare_snapshot(local_corpus.manifest_path, tmp_path / "other-cache", tmp_path / "other", cloud_config)
    first = SnapshotStore(runtime_export)
    assert first.snapshot_id != second.snapshot_id
    calls = cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"data": [[1.0] + [0.0] * 383]},
    }))
    results = [query_snapshot(store, store.resolve("F", 2014).filing_id, "Cache isolation probe?", 5,
                              cloud_config, generate=False) for store in (first, first, second)]
    assert [result.chunks[0][0] for result in results] == [1.0, 1.0, 0.0]
    assert len(calls) == 2
