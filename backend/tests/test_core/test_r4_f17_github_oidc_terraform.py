"""R4-F17 — Módulo Terraform GitHub OIDC IAM.

Cobertura:
- APP_VERSION == 2.20.0-r4-f17.
- Módulo ``infra/terraform/modules/github-oidc`` e stack ``ci-oidc``.
- Script ``scripts/terraform-ci-oidc.sh`` executável.
"""
from pathlib import Path

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_app_version_r4_f17():
    """APP_VERSION marca R4-F17 (Terraform GitHub OIDC)."""
    assert settings.APP_VERSION == "2.20.0-r4-f17"


def test_modulo_github_oidc_existe():
    """
    Módulo Terraform github-oidc está versionado com main/variables/outputs.

    Returns:
        None — falha se algum arquivo obrigatório faltar.
    """
    mod = REPO_ROOT / "infra" / "terraform" / "modules" / "github-oidc"
    for name in ("main.tf", "variables.tf", "outputs.tf"):
        assert (mod / name).is_file(), f"faltando {name}"
    text = (mod / "main.tf").read_text(encoding="utf-8")
    assert "aws_iam_openid_connect_provider" in text
    assert "aws_iam_role" in text
    assert "AssumeRoleWithWebIdentity" in text


def test_stack_ci_oidc_existe():
    """Stack environments/ci-oidc referencia o módulo e exporta role ARN."""
    env = REPO_ROOT / "infra" / "terraform" / "environments" / "ci-oidc"
    assert (env / "main.tf").is_file()
    assert (env / "terraform.tfvars.json").is_file()
    assert (env / "backend.hcl").is_file()
    main = (env / "main.tf").read_text(encoding="utf-8")
    assert 'source = "../../modules/github-oidc"' in main
    assert "aws_role_arn" in main


def test_script_terraform_ci_oidc():
    """Script de plan/apply do stack CI OIDC existe e é executável."""
    script = REPO_ROOT / "scripts" / "terraform-ci-oidc.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111, "script precisa ser executável"
    text = script.read_text(encoding="utf-8")
    assert "ci-oidc" in text
