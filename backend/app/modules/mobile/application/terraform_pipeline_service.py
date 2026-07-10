"""
TerraformPipelineService — pipeline multi-ambiente dev → staging → prod (CF-21).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.terraform_export_service import TerraformExportService

logger = get_logger("terraform_pipeline")

TERRAFORM_DIR = Path(__file__).resolve().parents[5] / "infra" / "terraform"

ENVIRONMENT_ORDER = ("dev", "staging", "prod")

ENV_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "dev": {
        "bucket_suffix": "-dev",
        "price_class": "PriceClass_100",
        "require_approval": False,
    },
    "staging": {
        "bucket_suffix": "-staging",
        "price_class": "PriceClass_100",
        "require_approval": True,
    },
    "prod": {
        "bucket_suffix": "-prod",
        "price_class": "PriceClass_All",
        "require_approval": True,
    },
}


class TerraformPipelineService:
    """
    Orquestra export e promoção Terraform entre ambientes.

    Gera tfvars/backend por ambiente e manifest de pipeline CI
    com ordem dev → staging → prod.
    """

    def __init__(
        self,
        terraform_dir: Optional[Path] = None,
        export_service: Optional[TerraformExportService] = None,
    ):
        """
        Args:
            terraform_dir: Raiz infra/terraform.
            export_service: Serviço de export opcional.
        """
        self.terraform_dir = terraform_dir or TERRAFORM_DIR
        self.export = export_service or TerraformExportService(terraform_dir=self.terraform_dir)

    def tfvars_for_environment(self, environment: str) -> Dict[str, Any]:
        """
        Monta tfvars com overrides por ambiente.

        Args:
            environment: dev | staging | prod.

        Returns:
            Documento tfvars completo.

        Raises:
            ValueError: Ambiente desconhecido.
        """
        if environment not in ENV_OVERRIDES:
            raise ValueError(f"Ambiente inválido: {environment}")

        base = self.export.tfvars_document()
        overrides = ENV_OVERRIDES[environment]
        base["bucket_name"] = f"{settings.CDN_S3_BUCKET}{overrides['bucket_suffix']}"
        base["cloudfront_price_class"] = overrides["price_class"]
        base["tags"] = {
            **base.get("tags", {}),
            "Environment": environment,
            "CostCenter": settings.TERRAFORM_SENTINEL_COST_CENTER,
            "Owner": settings.TERRAFORM_SENTINEL_OWNER,
        }
        return base

    def export_environment(self, environment: str) -> Dict[str, str]:
        """
        Exporta tfvars + backend.hcl + main.tf symlink para um ambiente.

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict com paths exportados.
        """
        env_dir = self.terraform_dir / "environments" / environment
        env_dir.mkdir(parents=True, exist_ok=True)

        document = self.tfvars_for_environment(environment)
        tfvars_path = env_dir / "terraform.tfvars.json"
        tfvars_path.write_text(json.dumps(document, indent=2), encoding="utf-8")

        backend = self.export.export_backend_config(environment)
        self._ensure_env_main_files(environment)

        logger.info(f"[terraform-pipeline] Ambiente {environment} exportado")
        return {
            "environment": environment,
            "terraform_tfvars": str(tfvars_path),
            **backend,
        }

    def export_all_environments(self) -> List[Dict[str, str]]:
        """
        Exporta todos os ambientes do pipeline.

        Returns:
            Lista de resultados por ambiente.
        """
        plugin_registry.load_all()
        return [self.export_environment(env) for env in ENVIRONMENT_ORDER]

    def pipeline_manifest(self) -> Dict[str, Any]:
        """
        Manifest do pipeline de promoção multi-ambiente.

        Returns:
            Dict com ordem, gates de aprovação e comandos sugeridos.
        """
        stages = []
        for env in ENVIRONMENT_ORDER:
            overrides = ENV_OVERRIDES[env]
            stages.append(
                {
                    "environment": env,
                    "require_approval": overrides["require_approval"],
                    "bucket_name": f"{settings.CDN_S3_BUCKET}{overrides['bucket_suffix']}",
                    "plan_command": f"./scripts/terraform-cdn.sh {env} plan",
                    "apply_command": f"./scripts/terraform-cdn.sh {env} apply",
                }
            )
        return {
            "version": settings.APP_VERSION,
            "promotion_order": list(ENVIRONMENT_ORDER),
            "remote_state_bucket": settings.TERRAFORM_STATE_BUCKET,
            "stages": stages,
            "usage": "./scripts/terraform-pipeline.sh plan-all",
        }

    def export_pipeline_manifest(self) -> Dict[str, str]:
        """
        Grava ``pipeline.json`` na raiz infra/terraform/.

        Returns:
            Dict com path do manifest exportado.
        """
        target = self.terraform_dir / "pipeline.json"
        target.write_text(
            json.dumps(self.pipeline_manifest(), indent=2),
            encoding="utf-8",
        )
        logger.info(f"[terraform-pipeline] pipeline.json → {target}")
        return {"pipeline_manifest": str(target)}

    def _ensure_env_main_files(self, environment: str) -> None:
        """
        Garante main.tf e variables.tf no diretório do ambiente.

        Args:
            environment: Nome do ambiente.

        Returns:
            None
        """
        env_dir = self.terraform_dir / "environments" / environment
        dev_main = self.terraform_dir / "environments" / "dev" / "main.tf"
        dev_vars = self.terraform_dir / "environments" / "dev" / "variables.tf"

        for src, name in ((dev_main, "main.tf"), (dev_vars, "variables.tf")):
            if not src.is_file():
                continue
            target = env_dir / name
            if environment == "dev" or target.exists():
                continue
            target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
