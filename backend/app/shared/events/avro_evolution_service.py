"""
AvroEvolutionService — evolução de schemas Avro com compatibilidade backward (CF-18).
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging_config import get_logger
from app.shared.events.avro_codec import AVRO_DIR

logger = get_logger("avro_evolution")

VERSION_PATTERN = re.compile(r"^(.+)\.v(\d+)$")


class AvroEvolutionService:
    """
    Valida evolução backward de schemas Avro entre versões (v1 → v2).

    Regras BACKWARD: consumidores com schema novo leem dados do schema antigo;
    campos novos devem ter default; campos removidos são proibidos.
    """

    def __init__(self, avro_dir: Optional[Path] = None):
        """
        Args:
            avro_dir: Diretório de arquivos .avsc.
        """
        self.avro_dir = avro_dir or AVRO_DIR
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self) -> None:
        """
        Carrega todos os .avsc indexados por stem (ex.: booking.approved.v2).

        Returns:
            None
        """
        self._schemas.clear()
        if not self.avro_dir.is_dir():
            return
        for path in self.avro_dir.glob("*.avsc"):
            self._schemas[path.stem] = json.loads(path.read_text(encoding="utf-8"))

    def list_event_versions(self, event_type: str) -> List[Dict[str, Any]]:
        """
        Lista versões Avro disponíveis para um event_type.

        Args:
            event_type: Ex.: booking.approved

        Returns:
            Lista ordenada por versão com schema_id e field count.
        """
        prefix = f"{event_type}.v"
        versions = []
        for schema_id, schema in self._schemas.items():
            if not schema_id.startswith(prefix):
                continue
            match = VERSION_PATTERN.match(schema_id)
            if not match:
                continue
            versions.append(
                {
                    "schema_id": schema_id,
                    "version": int(match.group(2)),
                    "field_count": len(schema.get("fields", [])),
                    "name": schema.get("name"),
                }
            )
        return sorted(versions, key=lambda item: item["version"])

    def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém schema Avro por ID.

        Args:
            schema_id: Ex.: booking.approved.v1

        Returns:
            Schema dict ou None.
        """
        return self._schemas.get(schema_id)

    def latest_schema_id(self, event_type: str) -> Optional[str]:
        """
        Retorna schema_id da versão mais recente de um event_type.

        Args:
            event_type: Nome do evento.

        Returns:
            schema_id ou None.
        """
        versions = self.list_event_versions(event_type)
        return versions[-1]["schema_id"] if versions else None

    def check_backward_compatible(
        self,
        old_schema_id: str,
        new_schema_id: str,
    ) -> Dict[str, Any]:
        """
        Verifica compatibilidade BACKWARD entre duas versões Avro.

        Args:
            old_schema_id: Schema anterior (ex.: booking.approved.v1).
            new_schema_id: Schema novo (ex.: booking.approved.v2).

        Returns:
            Dict com compatible (bool), errors e new_fields.

        Raises:
            ValueError: Schema não encontrado.
        """
        old_schema = self.get_schema(old_schema_id)
        new_schema = self.get_schema(new_schema_id)
        if not old_schema or not new_schema:
            raise ValueError(f"Schemas não encontrados: {old_schema_id}, {new_schema_id}")

        old_fields = {field["name"]: field for field in old_schema.get("fields", [])}
        new_fields = {field["name"]: field for field in new_schema.get("fields", [])}
        errors: List[str] = []
        added_fields: List[str] = []

        for name, old_field in old_fields.items():
            if name not in new_fields:
                errors.append(f"Campo removido: {name}")
                continue
            if not self._types_compatible(old_field.get("type"), new_fields[name].get("type")):
                errors.append(f"Tipo incompatível em '{name}'")

        for name, new_field in new_fields.items():
            if name in old_fields:
                continue
            added_fields.append(name)
            if "default" not in new_field:
                errors.append(f"Campo novo sem default: {name}")

        compatible = len(errors) == 0
        return {
            "old_schema_id": old_schema_id,
            "new_schema_id": new_schema_id,
            "compatibility": "BACKWARD",
            "compatible": compatible,
            "errors": errors,
            "new_fields": added_fields,
        }

    def evolution_report(self) -> List[Dict[str, Any]]:
        """
        Relatório de evolução para todos event_types com múltiplas versões.

        Returns:
            Lista com pares de versões e status de compatibilidade.
        """
        event_types = set()
        for schema_id in self._schemas:
            match = VERSION_PATTERN.match(schema_id)
            if match:
                event_types.add(match.group(1))

        report = []
        for event_type in sorted(event_types):
            versions = self.list_event_versions(event_type)
            if len(versions) < 2:
                report.append(
                    {
                        "event_type": event_type,
                        "versions": [v["schema_id"] for v in versions],
                        "evolved": False,
                        "compatible": True,
                    }
                )
                continue

            old_id = versions[-2]["schema_id"]
            new_id = versions[-1]["schema_id"]
            check = self.check_backward_compatible(old_id, new_id)
            report.append(
                {
                    "event_type": event_type,
                    "versions": [v["schema_id"] for v in versions],
                    "evolved": True,
                    "compatible": check["compatible"],
                    "latest": new_id,
                    "check": check,
                }
            )
        return report

    def register_evolved_schema(
        self,
        event_type: str,
        schema_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra versão evoluída no Confluent com check de compatibilidade.

        Args:
            event_type: Ex.: booking.approved
            schema_id: Versão específica ou latest.

        Returns:
            Resultado do registro com compat check.

        Raises:
            RuntimeError: Mode != confluent ou incompatível.
        """
        if settings.KAFKA_SCHEMA_REGISTRY_MODE != "confluent":
            raise RuntimeError("Confluent mode necessário para register_evolved_schema")

        target_id = schema_id or self.latest_schema_id(event_type)
        if not target_id:
            raise ValueError(f"Nenhum schema Avro para {event_type}")

        versions = self.list_event_versions(event_type)
        if len(versions) >= 2:
            old_id = versions[-2]["schema_id"]
            check = self.check_backward_compatible(old_id, target_id)
            if not check["compatible"]:
                raise RuntimeError(f"Incompatível BACKWARD: {check['errors']}")
        else:
            check = {"compatible": True, "new_schema_id": target_id}

        from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient

        client = ConfluentSchemaRegistryClient()
        subject = client.subject_for_event(event_type)
        schema = self.get_schema(target_id)
        if not schema:
            raise ValueError(f"Schema não encontrado: {target_id}")

        compat = client.check_compatibility(subject, json.dumps(schema))
        if not compat.get("is_compatible", False):
            raise RuntimeError(f"Confluent rejeitou compatibilidade: {compat}")

        confluent_id = client.register_avro_schema(subject, json.dumps(schema))
        return {
            "event_type": event_type,
            "schema_id": target_id,
            "subject": subject,
            "confluent_schema_id": confluent_id,
            "local_check": check,
            "confluent_check": compat,
        }

    @staticmethod
    def _types_compatible(old_type: Any, new_type: Any) -> bool:
        """
        Compara tipos Avro de forma simplificada.

        Args:
            old_type: Tipo do campo antigo.
            new_type: Tipo do campo novo.

        Returns:
            True se tipos são compatíveis para evolução backward.
        """
        return json.dumps(old_type, sort_keys=True) == json.dumps(new_type, sort_keys=True)
