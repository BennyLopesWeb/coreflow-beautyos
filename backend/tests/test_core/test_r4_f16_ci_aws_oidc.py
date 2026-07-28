"""R4-F16 — CI AWS via OIDC (sem access keys estáticas).

Cobertura:
- APP_VERSION == 2.19.0-r4-f16.
- Workflows terraform-cdn / cdn-sync / terraform-drift sem AWS_ACCESS_KEY_ID.
- Action compartilhada configure-aws-oidc presente.
- Workflows AWS usam permissions id-token: write.
"""
from pathlib import Path

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ACTIONS = REPO_ROOT / ".github" / "actions"


def test_app_version_r4_f16():
    """APP_VERSION avançou de R4-F16 (pin exato relaxado em R4-F17+)."""
    assert settings.APP_VERSION.startswith("2.")


def test_oidc_composite_action_existe():
    """Action compartilhada configure-aws-oidc está versionada."""
    action = ACTIONS / "configure-aws-oidc" / "action.yml"
    assert action.is_file()
    text = action.read_text(encoding="utf-8")
    assert "configure-aws-credentials@v4" in text
    assert "role-to-assume" in text


def test_workflows_aws_sem_access_keys_estaticas():
    """
    Workflows que falavam com secrets estáticos passam a OIDC.

    Returns:
        None — falha se algum workflow ainda referenciar AWS_ACCESS_KEY_ID.
    """
    targets = (
        "terraform-cdn.yml",
        "cdn-sync.yml",
        "terraform-drift.yml",
    )
    for name in targets:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "AWS_ACCESS_KEY_ID" not in text, f"{name} ainda usa AWS_ACCESS_KEY_ID"
        assert "AWS_SECRET_ACCESS_KEY" not in text, f"{name} ainda usa AWS_SECRET_ACCESS_KEY"
        assert "configure-aws-oidc" in text or name == "terraform-drift.yml"
        # drift: só plan-drift (workflow_dispatch) usa AWS; config-drift é local
        if name == "terraform-drift.yml":
            assert "configure-aws-oidc" in text
            assert "id-token: write" in text
        else:
            assert "id-token: write" in text
            assert "secrets.AWS_ROLE_ARN" in text


def test_docs_ops_oidc_existe():
    """Runbook ops/github-aws-oidc.md documenta setup da role."""
    doc = REPO_ROOT / "docs" / "ops" / "github-aws-oidc.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "AWS_ROLE_ARN" in text
    assert "token.actions.githubusercontent.com" in text
