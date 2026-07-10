"""
TerraformExportService — export IaC CDN/CloudFront a partir dos plugins (CF-19).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.cloudfront_behaviors_service import CloudFrontBehaviorsService

logger = get_logger("terraform_export")

TERRAFORM_DIR = Path(__file__).resolve().parents[5] / "infra" / "terraform"


class TerraformExportService:
    """
    Gera arquivos Terraform (tfvars + behaviors) para CDN multi-tenant.

    Consome ``CloudFrontBehaviorsService`` e exporta variáveis consumíveis
    pelo módulo ``infra/terraform/modules/coreflow-cdn``.
    """

    def __init__(
        self,
        terraform_dir: Optional[Path] = None,
        behaviors_service: Optional[CloudFrontBehaviorsService] = None,
    ):
        """
        Args:
            terraform_dir: Raiz infra/terraform.
            behaviors_service: Serviço CloudFront opcional (para testes).
        """
        self.terraform_dir = terraform_dir or TERRAFORM_DIR
        self.behaviors = behaviors_service or CloudFrontBehaviorsService()

    def tenant_behaviors(self) -> List[Dict[str, Any]]:
        """
        Lista behaviors formatados para variável Terraform ``tenant_behaviors``.

        Returns:
            Lista de dicts com plugin_id, path_pattern, cdn_host e ttl.
        """
        behaviors = []
        for manifest in plugin_registry.list_all():
            behavior = self.behaviors.behavior_for_plugin(manifest.plugin_id)
            behaviors.append(
                {
                    "plugin_id": manifest.plugin_id,
                    "path_pattern": behavior["PathPattern"],
                    "cdn_host": behavior["cdn_host"],
                    "default_ttl": behavior["DefaultTTL"],
                    "compress": behavior["Compress"],
                }
            )
        return behaviors

    def tfvars_document(self) -> Dict[str, Any]:
        """
        Monta documento completo de tfvars para ambiente dev/prod.

        Returns:
            Dict com bucket, aliases, behaviors e tags.
        """
        dist = self.behaviors.distribution_config()
        return {
            "aws_region": settings.CDN_S3_REGION,
            "bucket_name": settings.CDN_S3_BUCKET,
            "cdn_prefix": settings.CDN_S3_PREFIX,
            "cloudfront_price_class": settings.CDN_CLOUDFRONT_PRICE_CLASS,
            "cloudfront_aliases": dist["Aliases"],
            "tenant_behaviors": self.tenant_behaviors(),
            "well_known_cache_seconds": settings.MOBILE_WELL_KNOWN_CACHE_SECONDS,
            "tags": {
                "Project": "CoreFlow",
                "Component": "CDN",
                "Version": settings.APP_VERSION,
            },
        }

    def export_tfvars(self, environment: str = "dev") -> Dict[str, str]:
        """
        Exporta ``terraform.tfvars.json`` para environments/{env}/.

        Args:
            environment: Nome do ambiente (dev, staging, prod).

        Returns:
            Dict com path do arquivo exportado.
        """
        env_dir = self.terraform_dir / "environments" / environment
        env_dir.mkdir(parents=True, exist_ok=True)
        document = self.tfvars_document()
        target = env_dir / "terraform.tfvars.json"
        target.write_text(json.dumps(document, indent=2), encoding="utf-8")
        logger.info(f"[terraform] tfvars exportado → {target}")
        return {"terraform_tfvars": str(target), "environment": environment}

    def export_all(self, environments: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        Exporta tfvars para múltiplos ambientes.

        Args:
            environments: Lista de ambientes ou default [dev].

        Returns:
            Lista de paths exportados.
        """
        envs = environments or ["dev"]
        return [self.export_tfvars(env) for env in envs]

    def backend_config(self, environment: str = "dev") -> Dict[str, Any]:
        """
        Monta configuração de remote state S3 para Terraform.

        Args:
            environment: Ambiente (dev, staging, prod).

        Returns:
            Dict com bucket, key, region e dynamodb_table.
        """
        key = f"{settings.TERRAFORM_STATE_KEY_PREFIX}/{environment}/terraform.tfstate"
        return {
            "backend": "s3",
            "bucket": settings.TERRAFORM_STATE_BUCKET,
            "key": key,
            "region": settings.TERRAFORM_STATE_REGION,
            "dynamodb_table": settings.TERRAFORM_STATE_DYNAMODB_TABLE,
            "encrypt": True,
        }

    def export_backend_config(self, environment: str = "dev") -> Dict[str, str]:
        """
        Exporta ``backend.hcl`` para init Terraform com remote state.

        Args:
            environment: Ambiente alvo.

        Returns:
            Dict com path do backend.hcl exportado.
        """
        env_dir = self.terraform_dir / "environments" / environment
        env_dir.mkdir(parents=True, exist_ok=True)
        cfg = self.backend_config(environment)
        lines = [
            f'bucket         = "{cfg["bucket"]}"',
            f'key            = "{cfg["key"]}"',
            f'region         = "{cfg["region"]}"',
            f'dynamodb_table = "{cfg["dynamodb_table"]}"',
            "encrypt        = true",
        ]
        target = env_dir / "backend.hcl"
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"[terraform] backend.hcl exportado → {target}")
        return {"backend_hcl": str(target), "environment": environment}
