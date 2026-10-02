"""Vercel packaging contract: configuration, bundle contents, and production wiring."""

import json
import tomllib
from pathlib import Path

from fastapi import FastAPI

from etl_pipeline.runtime_snapshot import SnapshotStore
from tests.support import PROJECT_ROOT


def vercel_config() -> dict:
    return json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))


def test_function_timeout_leaves_headroom_above_the_query_budget():
    max_duration = vercel_config()["functions"]["api/main.py"]["maxDuration"]
    assert isinstance(max_duration, int) and 60 < max_duration <= 300


def test_build_produces_only_static_web_output():
    build = vercel_config()["buildCommand"]
    assert "frontend" in build and "public" in build
    assert "deploy/indexes" not in build


def test_entrypoint_resolves_to_the_fastapi_application():
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        entrypoint = tomllib.load(source)["tool"]["vercel"]["entrypoint"]
    module_name, attribute = entrypoint.split(":")
    module = __import__(module_name, fromlist=[attribute])
    assert isinstance(getattr(module, attribute), FastAPI)


def test_root_requirements_pin_every_runtime_dependency():
    root = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "etl_pipeline/requirements.txt" in root and "requirements-api.txt" in root
    for name in ("etl_pipeline/requirements.txt", "requirements-api.txt"):
        for line in (PROJECT_ROOT / name).read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith(("-r", "#")):
                assert "==" in line, f"Unpinned runtime dependency in {name}: {line}"


def test_deployment_excludes_local_data_but_keeps_the_snapshot():
    ignored = (PROJECT_ROOT / ".vercelignore").read_text(encoding="utf-8")
    assert "deploy" not in ignored
    for entry in ("data/", "resurse/", "tests/", "demo/"):
        assert entry in ignored


def test_snapshot_directory_is_selectable_without_code_changes(runtime_export, monkeypatch):
    monkeypatch.setenv("RAG_SNAPSHOT_DIR", str(runtime_export))
    assert SnapshotStore.from_env().snapshot_id == SnapshotStore(runtime_export).snapshot_id
