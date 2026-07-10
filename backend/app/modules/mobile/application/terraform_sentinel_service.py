"""
TerraformSentinelService — políticas enterprise Sentinel-like (CF-24).

Estende validação OPA (CF-23) com regras enterprise: tags obrigatórias,
governança prod, aliases CloudFront e metadados de aprovação.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.mobile.application.terraform_pipeline_service import (
    ENVIRONMENT_ORDER,
    TerraformPipelineService,
)
from app.modules.mobile.application.terraform_export_service import TerraformExportService

logger = get_logger("terraform_sentinel")

SENTINEL_DIR = Path(__file__).resolve().parents[5] / "infra" / "terraform" / "policies" / "sentinel"

REQUIRED_PROD_TAGS = ("Environment", "Component", "Version", "CostCenter", "Owner")


class TerraformSentinelService:
    """
    Avalia tfvars contra políticas enterprise estilo HashiCorp Sentinel.

    Modo embarcado (Python) para CI; arquivos ``.sentinel`` documentam
    as regras para integração Terraform Cloud Enterprise.
    """

    def __init__(
        self,
        pipeline_service: Optional[TerraformPipelineService] = None,
        export_service: Optional[TerraformExportService] = None,
        sentinel_dir: Optional[Path] = None,
    ):
        """
        Args:
            pipeline_service: Serviço pipeline multi-ambiente.
            export_service: Export backend config.
            sentinel_dir: Diretório policies/sentinel/.
        """
        self.pipeline = pipeline_service or TerraformPipelineService()
        self.export = export_service or TerraformExportService()
        self.sentinel_dir = sentinel_dir or SENTINEL_DIR

    def evaluate(self, environment: str) -> Dict[str, Any]:
        """
        Avalia políticas Sentinel embarcadas para um ambiente.

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict passed, violations, policy_level=enterprise.

        Raises:
            ValueError: Ambiente inválido.
        """
        if environment not in ENVIRONMENT_ORDER:
            raise ValueError(f"Ambiente inválido: {environment}")

        document = self.pipeline.tfvars_for_environment(environment)
        backend = self.export.backend_config(environment)
        violations: List[Dict[str, str]] = []

        violations.extend(self._check_required_tags(document, environment))
        violations.extend(self._check_cloudfront_governance(document, environment))
        violations.extend(self._check_backend_security(backend, environment))
        violations.extend(self._check_tenant_behaviors(document, environment))

        return {
            "environment": environment,
            "engine": "sentinel-embedded",
            "policy_level": "enterprise",
            "passed": len(violations) == 0,
            "violations": violations,
            "rules_checked": 4,
        }

    def evaluate_all(self) -> Dict[str, Any]:
        """
        Avalia Sentinel em todos ambientes do pipeline.

        Returns:
            Dict all_passed e results por ambiente.
        """
        results = [self.evaluate(env) for env in ENVIRONMENT_ORDER]
        return {
            "all_passed": all(r["passed"] for r in results),
            "policy_level": "enterprise",
            "results": results,
        }

    def policy_manifest(self) -> Dict[str, Any]:
        """
        Manifest das políticas Sentinel enterprise.

        Returns:
            Dict com regras, paths e usage.
        """
        sentinel_files = list(self.sentinel_dir.glob("*.sentinel")) if self.sentinel_dir.is_dir() else []
        return {
            "version": settings.APP_VERSION,
            "policy_level": "enterprise",
            "sentinel_dir": str(self.sentinel_dir),
            "sentinel_files": [f.name for f in sentinel_files],
            "required_prod_tags": list(REQUIRED_PROD_TAGS),
            "environments": list(ENVIRONMENT_ORDER),
            "usage": "./scripts/terraform-sentinel.sh all",
        }

    def _check_required_tags(
        self, document: Dict[str, Any], environment: str
    ) -> List[Dict[str, str]]:
        """
        Valida tags obrigatórias por ambiente.

        Args:
            document: Tfvars exportado.
            environment: Ambiente alvo.

        Returns:
            Lista de violações encontradas.
        """
        violations = []
        tags = document.get("tags", {})

        if environment == "prod":
            for tag in REQUIRED_PROD_TAGS:
                if not tags.get(tag):
                    violations.append(
                        {
                            "rule_id": "sentinel_required_tag",
                            "message": f"prod requer tag '{tag}'",
                        }
                    )
        elif not tags.get("Environment"):
            violations.append(
                {
                    "rule_id": "sentinel_environment_tag",
                    "message": f"{environment} requer tags.Environment",
                }
            )

        return violations

    def _check_cloudfront_governance(
        self, document: Dict[str, Any], environment: str
    ) -> List[Dict[str, str]]:
        """
        Regras de governança CloudFront por ambiente.

        Args:
            document: Tfvars.
            environment: Ambiente.

        Returns:
            Violações CloudFront.
        """
        violations = []
        aliases = document.get("cloudfront_aliases") or []

        if environment == "prod":
            if not aliases:
                violations.append(
                    {
                        "rule_id": "sentinel_prod_aliases",
                        "message": "prod requer cloudfront_aliases não vazio",
                    }
                )
            if document.get("cloudfront_price_class") != "PriceClass_All":
                violations.append(
                    {
                        "rule_id": "sentinel_prod_price_class",
                        "message": "prod deve usar PriceClass_All (enterprise SLA)",
                    }
                )

        if environment in ("staging", "prod") and len(aliases) > settings.TERRAFORM_SENTINEL_MAX_ALIASES:
            violations.append(
                {
                    "rule_id": "sentinel_max_aliases",
                    "message": (
                        f"{environment} excede máximo de "
                        f"{settings.TERRAFORM_SENTINEL_MAX_ALIASES} aliases"
                    ),
                }
            )

        return violations

    def _check_backend_security(
        self, backend: Dict[str, Any], environment: str
    ) -> List[Dict[str, str]]:
        """
        Valida remote state seguro (encrypt, dynamodb lock).

        Args:
            backend: Config backend S3.
            environment: Ambiente.

        Returns:
            Violações de backend.
        """
        violations = []

        if not backend.get("encrypt"):
            violations.append(
                {
                    "rule_id": "sentinel_state_encrypt",
                    "message": f"{environment} remote state deve ter encrypt=true",
                }
            )

        if environment in ("staging", "prod") and not backend.get("dynamodb_table"):
            violations.append(
                {
                    "rule_id": "sentinel_state_lock",
                    "message": f"{environment} requer dynamodb_table para state lock",
                }
            )

        return violations

    def _check_tenant_behaviors(
        self, document: Dict[str, Any], environment: str
    ) -> List[Dict[str, str]]:
        """
        Limites de tenant_behaviors e TTL mínimo prod.

        Args:
            document: Tfvars.
            environment: Ambiente.

        Returns:
            Violações de behaviors.
        """
        violations = []
        behaviors = document.get("tenant_behaviors") or []

        if len(behaviors) > settings.TERRAFORM_SENTINEL_MAX_BEHAVIORS:
            violations.append(
                {
                    "rule_id": "sentinel_max_behaviors",
                    "message": (
                        f"{environment} excede máximo de "
                        f"{settings.TERRAFORM_SENTINEL_MAX_BEHAVIORS} tenant_behaviors"
                    ),
                }
            )

        if environment == "prod":
            for behavior in behaviors:
                ttl = behavior.get("default_ttl", 0)
                if ttl < settings.TERRAFORM_SENTINEL_PROD_MIN_TTL:
                    violations.append(
                        {
                            "rule_id": "sentinel_prod_min_ttl",
                            "message": (
                                f"prod behavior {behavior.get('plugin_id')} "
                                f"default_ttl < {settings.TERRAFORM_SENTINEL_PROD_MIN_TTL}"
                            ),
                        }
                    )
                    break

        return violations
