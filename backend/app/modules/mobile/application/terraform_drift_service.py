"""
TerraformDriftService — detecção de drift infra CDN (CF-22).

Compara tfvars exportados com snapshot commitado e opcionalmente
executa ``terraform plan -detailed-exitcode`` para drift real.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.mobile.application.terraform_pipeline_service import (
    ENVIRONMENT_ORDER,
    TerraformPipelineService,
)

logger = get_logger("terraform_drift")


class TerraformDriftService:
    """
    Detecta drift de configuração Terraform entre export atual e disco/CI.

    Modo ``config`` compara hash do tfvars exportado vs arquivo commitado.
    Modo ``plan`` executa terraform plan -detailed-exitcode quando live.
    """

    def __init__(
        self,
        pipeline_service: Optional[TerraformPipelineService] = None,
        terraform_dir: Optional[Path] = None,
    ):
        """
        Args:
            pipeline_service: Serviço pipeline multi-ambiente.
            terraform_dir: Raiz infra/terraform.
        """
        self.pipeline = pipeline_service or TerraformPipelineService()
        self.terraform_dir = terraform_dir or self.pipeline.terraform_dir

    def tfvars_hash(self, document: Dict[str, Any]) -> str:
        """
        Calcula hash SHA256 estável de um documento tfvars.

        Args:
            document: Dict tfvars serializável.

        Returns:
            Hex digest SHA256.
        """
        normalized = json.dumps(document, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def config_drift(self, environment: str) -> Dict[str, Any]:
        """
        Compara tfvars exportado agora vs arquivo em environments/{env}/.

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict has_drift, hashes e paths.

        Raises:
            ValueError: Ambiente inválido.
        """
        if environment not in ENVIRONMENT_ORDER:
            raise ValueError(f"Ambiente inválido: {environment}")

        current = self.pipeline.tfvars_for_environment(environment)
        current_hash = self.tfvars_hash(current)

        committed_path = self.terraform_dir / "environments" / environment / "terraform.tfvars.json"
        committed_hash = None
        has_committed = committed_path.is_file()

        if has_committed:
            committed_doc = json.loads(committed_path.read_text(encoding="utf-8"))
            committed_hash = self.tfvars_hash(committed_doc)

        has_drift = has_committed and committed_hash != current_hash

        return {
            "environment": environment,
            "drift_type": "config",
            "has_drift": has_drift,
            "current_hash": current_hash,
            "committed_hash": committed_hash,
            "committed_path": str(committed_path),
            "has_committed_file": has_committed,
        }

    def detect_all_config_drift(self) -> Dict[str, Any]:
        """
        Verifica config drift em todos ambientes do pipeline.

        Returns:
            Dict com lista de ambientes e flag has_any_drift.
        """
        results = [self.config_drift(env) for env in ENVIRONMENT_ORDER]
        return {
            "drift_type": "config",
            "has_any_drift": any(r["has_drift"] for r in results),
            "environments": results,
        }

    def plan_drift(self, environment: str) -> Dict[str, Any]:
        """
        Executa terraform plan -detailed-exitcode para drift de infra.

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict has_drift, exit_code, stdout snippet.

        Raises:
            ValueError: Ambiente inválido ou drift live desabilitado.
            RuntimeError: terraform não encontrado ou init falhou.
        """
        if not settings.TERRAFORM_DRIFT_LIVE:
            raise ValueError("TERRAFORM_DRIFT_LIVE=false — use config_drift()")

        if environment not in ENVIRONMENT_ORDER:
            raise ValueError(f"Ambiente inválido: {environment}")

        self.pipeline.export_environment(environment)
        env_dir = self.terraform_dir / "environments" / environment

        init = subprocess.run(
            ["terraform", "init", "-backend-config=backend.hcl", "-input=false"],
            cwd=str(env_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if init.returncode != 0:
            raise RuntimeError(f"terraform init falhou: {init.stderr[:500]}")

        plan = subprocess.run(
            [
                "terraform", "plan",
                "-detailed-exitcode",
                "-var-file=terraform.tfvars.json",
                "-input=false",
                "-no-color",
            ],
            cwd=str(env_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        # 0 = no changes, 2 = changes present (drift), 1 = error
        has_drift = plan.returncode == 2
        if plan.returncode not in (0, 2):
            raise RuntimeError(f"terraform plan falhou (code={plan.returncode}): {plan.stderr[:500]}")

        return {
            "environment": environment,
            "drift_type": "plan",
            "has_drift": has_drift,
            "exit_code": plan.returncode,
            "plan_summary": self._summarize_plan(plan.stdout),
            "stdout_lines": len(plan.stdout.splitlines()),
        }

    def drift_report(self, environment: str) -> Dict[str, Any]:
        """
        Relatório combinado config + plan (quando live habilitado).

        Args:
            environment: Ambiente alvo.

        Returns:
            Dict com config_drift e plan_drift opcional.
        """
        report: Dict[str, Any] = {
            "environment": environment,
            "config": self.config_drift(environment),
        }
        if settings.TERRAFORM_DRIFT_LIVE:
            try:
                report["plan"] = self.plan_drift(environment)
            except Exception as exc:
                report["plan"] = {"error": str(exc), "has_drift": None}
        report["has_drift"] = report["config"]["has_drift"] or (
            report.get("plan", {}).get("has_drift") is True
        )
        return report

    @staticmethod
    def _summarize_plan(stdout: str) -> str:
        """
        Extrai linha resumo do terraform plan.

        Args:
            stdout: Saída completa do plan.

        Returns:
            Linha Plan: ou trecho final relevante.
        """
        for line in stdout.splitlines():
            if line.strip().startswith("Plan:"):
                return line.strip()
        lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
        return lines[-1] if lines else "no output"
