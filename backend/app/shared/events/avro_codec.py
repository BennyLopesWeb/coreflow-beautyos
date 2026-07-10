"""
AvroEventCodec — serialização Avro compatível com Confluent wire format (CF-16/17).
"""
import io
import json
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging_config import get_logger

logger = get_logger("avro_codec")

AVRO_DIR = Path(__file__).resolve().parents[3] / "schemas" / "events" / "avro"
CONFLUENT_MAGIC_BYTE = 0


class AvroEventCodec:
    """
    Codifica/decodifica payloads Avro com header Confluent (magic + schema_id).

    Usa fastavro quando disponível; fallback para JSON em dev.
    """

    def __init__(self, avro_dir: Optional[Path] = None):
        """
        Args:
            avro_dir: Diretório de arquivos .avsc.
        """
        self.avro_dir = avro_dir or AVRO_DIR
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._load_avro_schemas()

    def _load_avro_schemas(self) -> None:
        """
        Carrega arquivos .avsc do disco.

        Returns:
            None
        """
        if not self.avro_dir.is_dir():
            return
        for path in self.avro_dir.glob("*.avsc"):
            self._schemas[path.stem] = json.loads(path.read_text(encoding="utf-8"))

    def list_schemas(self) -> List[Dict[str, Any]]:
        """
        Lista schemas Avro locais carregados.

        Returns:
            Lista com schema_id e record name.
        """
        result = []
        for schema_id, schema in sorted(self._schemas.items()):
            result.append(
                {
                    "schema_id": schema_id,
                    "name": schema.get("name"),
                    "namespace": schema.get("namespace"),
                }
            )
        return result

    def get_avro_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém parsed Avro schema por ID local (ex.: booking.approved.v1).

        Args:
            schema_id: Identificador do schema.

        Returns:
            Avro schema dict ou None.
        """
        return self._schemas.get(schema_id)

    def encode(
        self,
        schema_id: str,
        record: Dict[str, Any],
        confluent_schema_id: int,
    ) -> bytes:
        """
        Serializa record Avro com wire format Confluent.

        Args:
            schema_id: ID local do schema (.avsc stem).
            record: Dados a serializar.
            confluent_schema_id: ID numérico do Confluent Schema Registry.

        Returns:
            Bytes prontos para Kafka value.

        Raises:
            ValueError: Schema não encontrado ou fastavro indisponível.
        """
        parsed = self.get_avro_schema(schema_id)
        if not parsed:
            raise ValueError(f"Avro schema não encontrado: {schema_id}")

        try:
            import fastavro
        except ImportError as exc:
            raise ImportError("fastavro necessário para encoding Avro") from exc

        buffer = io.BytesIO()
        buffer.write(struct.pack(">bI", CONFLUENT_MAGIC_BYTE, confluent_schema_id))
        fastavro.schemaless_writer(buffer, parsed, record)
        return buffer.getvalue()

    def decode(self, data: bytes) -> tuple[int, Dict[str, Any]]:
        """
        Deserializa wire format Confluent Avro.

        Args:
            data: Bytes da mensagem Kafka.

        Returns:
            Tupla (confluent_schema_id, record dict).
        """
        try:
            import fastavro
        except ImportError as exc:
            raise ImportError("fastavro necessário para decoding Avro") from exc

        buffer = io.BytesIO(data)
        header = buffer.read(5)
        if len(header) != 5:
            raise ValueError("Payload Avro inválido")
        magic, schema_id = struct.unpack(">bI", header)
        if magic != CONFLUENT_MAGIC_BYTE:
            raise ValueError(f"Magic byte inválido: {magic}")

        parsed = next(iter(self._schemas.values()), None)
        if not parsed:
            raise ValueError("Nenhum schema Avro local carregado")

        record = fastavro.schemaless_reader(buffer, parsed)
        return schema_id, record
