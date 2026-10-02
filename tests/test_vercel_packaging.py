"""Vercel packaging contract: services, bundle contents, and production wiring."""

import json
import tomllib
from pathlib import Path

from fastapi import FastAPI

from etl_pipeline.runtime_snapshot import SnapshotStore
from tests.support import PROJECT_ROOT


def vercel_config() -> dict:
    return json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))


def services() -> dict:
    return vercel_config()["services"]


def test_only_the_real_services_exist():
    assert set(services()) == {"web", "api"}


def test_frontend_service_builds_the_vite_application():
    web = services()["web"]
    assert web["root"] == "frontend"
    assert web["framework"] == "vite"


def test_api_service_resolves_to_the_fastapi_application():
    api = services()["api"]
    assert api["root"] == "."
    assert api["runtime"] == "python"
    module_name, attribute = api["entrypoint"].split(":")
    module = __import__(module_name, fromlist=[attribute])
    assert isinstance(getattr(module, attribute), FastAPI)


def test_function_timeout_leaves_headroom_above_the_query_budget():
    max_duration = services()["api"]["functions"]["api/main.py"]["maxDuration"]
    assert isinstance(max_duration, int) and 60 < max_duration <= 300


def test_api_bundle_carries_indexes_but_not_frontend_sources():
    files = services()["api"]["functions"]["api/main.py"]
    assert "deploy/indexes/**" in files["includeFiles"]
    assert "frontend/**" in files["excludeFiles"]


def test_api_routes_win_over_the_spa_fallback():
    rewrites = vercel_config()["rewrites"]
    assert rewrites[0] == {"source": "/api/(.*)", "destination": {"service": "api"}}
    assert rewrites[-1] == {"source": "/(.*)", "destination": {"service": "web"}}


def test_services_need_no_internal_bindings():
    assert all("bindings" not in service for service in services().values())


def test_build_and_runtime_keys_live_inside_services():
    config = vercel_config()
    for key in ("functions", "installCommand", "buildCommand", "outputDirectory", "framework"):
        assert key not in config


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
