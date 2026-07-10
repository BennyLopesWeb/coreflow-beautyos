"""
TerraformCloudPolicyService — policy sets Terraform Cloud (CF-25).

Gera manifest de policy set para TFC integrando OPA + Sentinel,
com validação embarcada para CI e export JSON para API TFC.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.mobile.application.terraform_pipeline_service import ENVIRONMENT_ORDER
from app.modules.mobile.application.terraform_policy_service import TerraformPolicyService
from app.modules.mobile.application.terraform_sentinel_service import TerraformSentinelService

logger = get_logger("terraform_cloud_policy")

TFC_DIR = Path(__file__).resolve().parents[5] / "infra" / "terraform" / "cloud"


class TerraformCloudPolicyService:
    """
    Orquestra policy sets Terraform Cloud a partir de OPA + Sentinel.

    Exporta ``policy-set.json`` consumível pela API TFC ou CLI
    ``terraform cloud policy-set create``.
    """

    POLICY_KINDS = ("opa", "sentinel")

    def __init__(
        self,
        opa_service: Optional[TerraformPolicyService] = None,
        sentinel_service: Optional[TerraformSentinelService] = None,
        tfc_dir: Optional[Path] = None,
    ):
        """
        Args:
            opa_service: Serviço OPA (CF-23).
            sentinel_service: Serviço Sentinel (CF-24).
            tfc_dir: Diretório infra/terraform/cloud/.
        """
        self.opa = opa_service or TerraformPolicyService()
        self.sentinel = sentinel_service or TerraformSentinelService()
        self.tfc_dir = tfc_dir or TFC_DIR

    def policy_set_document(self) -> Dict[str, Any]:
        """
        Monta documento policy set para Terraform Cloud.

        Returns:
            Dict name, description, policies, workspaces, enforcement.
        """
        policies = []
        for env in ENVIRONMENT_ORDER:
            policies.append(
                {
                    "name": f"coreflow-cdn-{env}-opa",
                    "kind": "opa",
                    "environment": env,
                    "path": "infra/terraform/policies/cdn.rego",
                    "enforcement_level": self._enforcement_level(env),
                }
            )
            policies.append(
                {
                    "name": f"coreflow-cdn-{env}-sentinel",
                    "kind": "sentinel",
                    "environment": env,
                    "path": "infra/terraform/policies/sentinel/cdn.sentinel",
                    "enforcement_level": self._enforcement_level(env),
                }
            )

        return {
            "version": settings.APP_VERSION,
            "name": settings.TERRAFORM_CLOUD_POLICY_SET_NAME,
            "description": "CoreFlow CDN — OPA + Sentinel enterprise policies",
            "organization": settings.TERRAFORM_CLOUD_ORGANIZATION,
            "workspace_prefix": settings.TERRAFORM_CLOUD_WORKSPACE_PREFIX,
            "policies": policies,
            "policy_kind_order": list(self.POLICY_KINDS),
        }

    def evaluate_workspace(self, environment: str) -> Dict[str, Any]:
        """
        Avalia OPA + Sentinel para um ambiente (pre-flight TFC).

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict all_passed, opa, sentinel results.

        Raises:
            ValueError: Ambiente inválido.
        """
        opa_result = self.opa.evaluate(environment)
        sentinel_result = self.sentinel.evaluate(environment)
        return {
            "environment": environment,
            "all_passed": opa_result["passed"] and sentinel_result["passed"],
            "opa": opa_result,
            "sentinel": sentinel_result,
        }

    def evaluate_all(self) -> Dict[str, Any]:
        """
        Avalia policy set completo em todos ambientes.

        Returns:
            Dict all_passed e results por ambiente.
        """
        results = [self.evaluate_workspace(env) for env in ENVIRONMENT_ORDER]
        return {
            "all_passed": all(r["all_passed"] for r in results),
            "policy_set": settings.TERRAFORM_CLOUD_POLICY_SET_NAME,
            "results": results,
        }

    def export_policy_set(self) -> Dict[str, str]:
        """
        Grava ``policy-set.json`` em infra/terraform/cloud/.

        Returns:
            Dict com path exportado.
        """
        self.tfc_dir.mkdir(parents=True, exist_ok=True)
        target = self.tfc_dir / "policy-set.json"
        document = self.policy_set_document()
        target.write_text(json.dumps(document, indent=2), encoding="utf-8")
        logger.info(f"[tfc-policy] policy-set.json → {target}")
        return {"policy_set": str(target)}

    def sync_manifest(self) -> Dict[str, Any]:
        """
        Preview do policy set + status de validação local.

        Returns:
            Dict document + evaluate_all summary.
        """
        return {
            **self.policy_set_document(),
            "validation": self.evaluate_all(),
            "tfc_api_url": (
                f"https://app.terraform.io/api/v2/organizations/"
                f"{settings.TERRAFORM_CLOUD_ORGANIZATION}/policy-sets"
            ),
        }

    @staticmethod
    def _enforcement_level(environment: str) -> str:
        """
        Nível de enforcement TFC por ambiente.

        Args:
            environment: dev | staging | prod.

        Returns:
            advisory | soft-mandatory | mandatory.
        """
        if environment == "dev":
            return "advisory"
        if environment == "staging":
            return "soft-mandatory"
        return "mandatory"
