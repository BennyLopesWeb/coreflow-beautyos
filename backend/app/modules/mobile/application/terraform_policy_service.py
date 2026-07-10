"""
TerraformPolicyService — policy-as-code OPA para tfvars CDN (CF-23).

Avalia documentos tfvars contra regras Rego em ``infra/terraform/policies/``.
Modo embarcado (Python) para CI/testes; modo live via ``opa eval`` opcional.
"""
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

logger = get_logger("terraform_policy")

POLICIES_DIR = Path(__file__).resolve().parents[5] / "infra" / "terraform" / "policies"


class TerraformPolicyService:
    """
    Valida tfvars Terraform contra políticas OPA/Sentinel-like.

    Regras embarcadas garantem CI sem binário OPA; ``TERRAFORM_OPA_LIVE=true``
    delega para ``opa eval`` com ``cdn.rego``.
    """

    EMBEDDED_RULES: List[Dict[str, Any]] = [
        {
            "id": "prod_price_class_all",
            "environments": ["prod"],
            "check": lambda doc, env: doc.get("cloudfront_price_class") == "PriceClass_All",
            "message": "prod deve usar cloudfront_price_class=PriceClass_All",
        },
        {
            "id": "prod_bucket_suffix",
            "environments": ["prod"],
            "check": lambda doc, env: str(doc.get("bucket_name", "")).endswith("-prod"),
            "message": "prod bucket_name deve terminar com -prod",
        },
        {
            "id": "staging_bucket_suffix",
            "environments": ["staging"],
            "check": lambda doc, env: str(doc.get("bucket_name", "")).endswith("-staging"),
            "message": "staging bucket_name deve terminar com -staging",
        },
        {
            "id": "dev_bucket_suffix",
            "environments": ["dev"],
            "check": lambda doc, env: str(doc.get("bucket_name", "")).endswith("-dev"),
            "message": "dev bucket_name deve terminar com -dev",
        },
        {
            "id": "tags_environment",
            "environments": list(ENVIRONMENT_ORDER),
            "check": lambda doc, env: doc.get("tags", {}).get("Environment") == env,
            "message": "tags.Environment deve corresponder ao ambiente",
        },
        {
            "id": "tenant_behaviors_non_empty",
            "environments": list(ENVIRONMENT_ORDER),
            "check": lambda doc, env: len(doc.get("tenant_behaviors", [])) >= 1,
            "message": "tenant_behaviors não pode ser vazio",
        },
    ]

    def __init__(
        self,
        pipeline_service: Optional[TerraformPipelineService] = None,
        policies_dir: Optional[Path] = None,
    ):
        """
        Args:
            pipeline_service: Serviço pipeline multi-ambiente.
            policies_dir: Diretório com arquivos .rego.
        """
        self.pipeline = pipeline_service or TerraformPipelineService()
        self.policies_dir = policies_dir or POLICIES_DIR

    def evaluate_embedded(self, environment: str) -> Dict[str, Any]:
        """
        Avalia tfvars com regras Python embarcadas (sem OPA CLI).

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict passed, violations e environment.

        Raises:
            ValueError: Ambiente inválido.
        """
        if environment not in ENVIRONMENT_ORDER:
            raise ValueError(f"Ambiente inválido: {environment}")

        document = self.pipeline.tfvars_for_environment(environment)
        violations = []

        for rule in self.EMBEDDED_RULES:
            if environment not in rule["environments"]:
                continue
            if not rule["check"](document, environment):
                violations.append({"rule_id": rule["id"], "message": rule["message"]})

        return {
            "environment": environment,
            "engine": "embedded",
            "passed": len(violations) == 0,
            "violations": violations,
            "rules_checked": len(
                [r for r in self.EMBEDDED_RULES if environment in r["environments"]]
            ),
        }

    def evaluate_opa(self, environment: str) -> Dict[str, Any]:
        """
        Avalia tfvars via ``opa eval`` com cdn.rego.

        Args:
            environment: dev | staging | prod.

        Returns:
            Dict passed, violations, engine=opa.

        Raises:
            ValueError: OPA live desabilitado ou ambiente inválido.
            RuntimeError: opa CLI falhou.
        """
        if not settings.TERRAFORM_OPA_LIVE:
            raise ValueError("TERRAFORM_OPA_LIVE=false — use evaluate_embedded()")

        if environment not in ENVIRONMENT_ORDER:
            raise ValueError(f"Ambiente inválido: {environment}")

        rego_path = self.policies_dir / "cdn.rego"
        if not rego_path.is_file():
            raise RuntimeError(f"Policy não encontrada: {rego_path}")

        document = self.pipeline.tfvars_for_environment(environment)
        input_payload = {"environment": environment, "tfvars": document}

        result = subprocess.run(
            [
                "opa", "eval",
                "--data", str(rego_path),
                "--input", "-",
                "data.coreflow.cdn.deny",
                "--format", "raw",
            ],
            input=json.dumps(input_payload).encode("utf-8"),
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"opa eval falhou: {result.stderr.decode()[:500]}")

        deny_list = json.loads(result.stdout.decode() or "[]")
        violations = [{"rule_id": "opa", "message": msg} for msg in (deny_list or [])]

        return {
            "environment": environment,
            "engine": "opa",
            "passed": len(violations) == 0,
            "violations": violations,
            "rules_checked": "cdn.rego",
        }

    def evaluate(self, environment: str) -> Dict[str, Any]:
        """
        Avalia políticas usando engine configurado (embedded ou opa).

        Args:
            environment: dev | staging | prod.

        Returns:
            Resultado da avaliação de políticas.
        """
        if settings.TERRAFORM_OPA_LIVE:
            return self.evaluate_opa(environment)
        return self.evaluate_embedded(environment)

    def evaluate_all(self) -> Dict[str, Any]:
        """
        Avalia todos ambientes do pipeline.

        Returns:
            Dict all_passed e resultados por ambiente.
        """
        results = [self.evaluate(env) for env in ENVIRONMENT_ORDER]
        return {
            "all_passed": all(r["passed"] for r in results),
            "results": results,
        }

    def policy_manifest(self) -> Dict[str, Any]:
        """
        Manifest das políticas disponíveis.

        Returns:
            Dict com regras embarcadas e path rego.
        """
        return {
            "version": settings.APP_VERSION,
            "opa_live": settings.TERRAFORM_OPA_LIVE,
            "policies_dir": str(self.policies_dir),
            "embedded_rules": [r["id"] for r in self.EMBEDDED_RULES],
            "environments": list(ENVIRONMENT_ORDER),
            "usage": "./scripts/terraform-policy.sh all",
        }
