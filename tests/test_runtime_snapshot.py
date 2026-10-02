import json
from copy import deepcopy
import gzip
from hashlib import sha256

import httpx
import pytest

from etl_pipeline.cloud_indexing import prepare_snapshot
from etl_pipeline.runtime_snapshot import SnapshotStore


def test_cloud_export_can_be_read_without_raw_filings_or_model_calls(local_corpus, cloud_config, cloud_http, tmp_path):
    cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"data": [
            [1.0] + [0.0] * 383 for _ in json.loads(request.content)["text"]
        ]},
    }))
    export = tmp_path / "export"
    prepare_snapshot(local_corpus.manifest_path, tmp_path / "cloud-indexes", export, cloud_config)
    for filing in local_corpus.catalog().values():
        filing.path.unlink()
    calls = cloud_http(lambda request: (_ for _ in ()).throw(AssertionError("Reader contacted a model")))
    store = SnapshotStore(export)
    assert [item.ticker for item in store.prepared()] == ["F", "NVDA"]
    selected = next(iter(store.catalog()))
    assert store.resolve_id(selected).chunk_count == 1
    assert store.resolve("NVDA", 2026).filing_id in store.catalog()
    assert len(store.snapshot_id) == 64
    assert not calls


@pytest.fixture
def runtime_export(local_corpus, cloud_config, cloud_http, tmp_path):
    cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"data": [
            [1.0] + [0.0] * 383 for _ in json.loads(request.content)["text"]
        ]},
    }))
    export = tmp_path / "export"
    prepare_snapshot(local_corpus.manifest_path, tmp_path / "cloud-indexes", export, cloud_config)
    return export


def reseal(manifest):
    from etl_pipeline.cloud_identity import configuration_id

    manifest["embedding_config_id"] = configuration_id(manifest["embedding_configuration"])
    manifest["index_config_id"] = configuration_id(manifest["index_configuration"])
    manifest["snapshot_id"] = configuration_id({key: value for key, value in manifest.items() if key != "snapshot_id"})


@pytest.mark.parametrize("change", ["dimension", "pooling", "tokenizer", "split", "duplicate", "path", "size"])
def test_runtime_rejects_incompatible_or_unsafe_manifest_before_http(runtime_export, cloud_http, change):
    path = runtime_export / "manifest.json"
    manifest = json.loads(path.read_text())
    if change == "dimension":
        manifest["embedding_configuration"]["dimension"] = 768
    elif change == "pooling":
        manifest["embedding_configuration"]["pooling"] = "cls"
    elif change == "tokenizer":
        manifest["embedding_configuration"]["tokenizer"]["revision"] = "unknown"
    elif change == "split":
        manifest["filings"][0]["split"] = "test"
    elif change == "duplicate":
        manifest["filings"].append(deepcopy(manifest["filings"][0]))
    elif change == "path":
        manifest["filings"][0]["filename"] = "../outside.json.gz"
    else:
        manifest["filings"][0]["expanded_bytes"] = 65 * 1024 * 1024
    reseal(manifest)
    path.write_text(json.dumps(manifest))
    calls = cloud_http(lambda request: pytest.fail("Invalid snapshot contacted a model"))
    with pytest.raises(ValueError):
        SnapshotStore(runtime_export)
    assert not calls


@pytest.mark.parametrize("vector", [[1.0] * 768, [0.0] * 384, [True] + [1.0] * 383])
def test_runtime_checks_actual_vectors_even_with_valid_file_hashes(runtime_export, vector):
    manifest_path = runtime_export / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["filings"][0]
    path = runtime_export / entry["filename"]
    index = json.loads(gzip.decompress(path.read_bytes()))
    index["embeddings"][0] = vector
    expanded = json.dumps(index).encode()
    content = gzip.compress(expanded, mtime=0)
    path.write_bytes(content)
    entry.update(sha256=sha256(content).hexdigest(), compressed_bytes=len(content), expanded_bytes=len(expanded))
    reseal(manifest)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="vector"):
        SnapshotStore(runtime_export)


def test_export_is_deterministic_and_reuses_only_compatible_cloud_cache(
    local_corpus, cloud_config, cloud_http, runtime_export, tmp_path,
):
    calls = cloud_http(lambda request: pytest.fail("Compatible cache contacted a model"))
    second = tmp_path / "second-export"
    prepare_snapshot(local_corpus.manifest_path, tmp_path / "cloud-indexes", second, cloud_config)
    assert {path.name: path.read_bytes() for path in second.iterdir()} == {
        path.name: path.read_bytes() for path in runtime_export.iterdir()
    }
    assert not calls
