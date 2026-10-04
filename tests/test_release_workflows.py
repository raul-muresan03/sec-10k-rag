"""Guardrails of the release automation: scope, staging, and gating."""

import yaml

from tests.support import PROJECT_ROOT


def workflows() -> dict[str, dict]:
    return {
        name: yaml.safe_load((PROJECT_ROOT / ".github" / "workflows" / name).read_text())
        for name in ("deploy.yml", "rollback.yml")
    }


def test_promotion_resolves_the_team_scope():
    for name, workflow in workflows().items():
        text = str(workflow)
        assert "--scope" in text, f"{name} promotes without a team scope"


def test_candidates_stage_without_production_traffic():
    deploy = str(workflows()["deploy.yml"])
    assert "--prod --skip-domain" in deploy


def test_releases_gate_on_green_main_ci_and_serialize():
    release = workflows()["deploy.yml"]
    assert release["concurrency"]["group"] == "production-release"
    assert release["concurrency"]["cancel-in-progress"] is False
    job_if = release["jobs"]["release"]["if"]
    assert "workflow_run.conclusion == 'success'" in job_if
    assert "head_branch == 'main'" in job_if
