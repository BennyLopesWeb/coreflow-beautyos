"""
Service para upload e gestão de comprovantes de depósito.
"""
import uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.agendamento import Agendamento
from app.services.agendamento_service import AgendamentoService
from app.core.exceptions import ValidationError

COMPROVANTES_DIR = Path(__file__).resolve().parents[1] / "static" / "comprovantes"
TIPOS_PERMITIDOS = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
}
EXTENSOES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
TAMANHO_MAX_BYTES = 5 * 1024 * 1024


class ComprovanteService:
    """
    Gerencia envio e armazenamento de comprovantes de depósito do sinal.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service com sessão do banco.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db
        self.agendamento_service = AgendamentoService(db)
        COMPROVANTES_DIR.mkdir(parents=True, exist_ok=True)

    async def salvar_comprovante(
        self,
        agendamento_id: int,
        arquivo: UploadFile,
        base_url: str = "http://localhost:8000",
    ) -> Agendamento:
        """
        Salva comprovante de depósito vinculado a um agendamento.

        Args:
            agendamento_id: ID do agendamento.
            arquivo: Arquivo enviado (imagem ou PDF).
            base_url: URL base da API para montar link público.

        Returns:
            Agendamento atualizado com comprovante_url.

        Raises:
            ValidationError: Se tipo ou tamanho do arquivo forem inválidos.
        """
        agendamento = self.agendamento_service.obter_agendamento(agendamento_id)

        if agendamento.sinal_pago:
            raise ValidationError("Sinal já foi confirmado para este agendamento")

        content_type = (arquivo.content_type or "").lower()
        if content_type not in TIPOS_PERMITIDOS:
            raise ValidationError(
                "Formato não permitido. Envie JPG, PNG, WEBP ou PDF."
            )

        conteudo = await arquivo.read()
        if len(conteudo) > TAMANHO_MAX_BYTES:
            raise ValidationError("Arquivo muito grande. Máximo: 5 MB.")

        if len(conteudo) == 0:
            raise ValidationError("Arquivo vazio.")

        ext = EXTENSOES.get(content_type, ".jpg")
        nome_arquivo = f"agendamento_{agendamento_id}_{uuid.uuid4().hex[:10]}{ext}"
        caminho = COMPROVANTES_DIR / nome_arquivo

        with open(caminho, "wb") as f:
            f.write(conteudo)

        agendamento.comprovante_url = f"{base_url}/static/comprovantes/{nome_arquivo}"
        self.db.commit()
        self.db.refresh(agendamento)
        return agendamento
