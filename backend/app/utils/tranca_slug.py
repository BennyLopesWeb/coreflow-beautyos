"""
Helpers para slugs e nomes de arquivos de tranças.
"""
import re
import unicodedata


def nome_para_slug(nome: str) -> str:
    """
    Converte nome da trança em slug para arquivos (ex: 'Box Braids' → 'box-braids').

    Args:
        nome: Nome exibido da trança.

    Returns:
        Slug em minúsculas com hífens.
    """
    texto = unicodedata.normalize("NFKD", nome)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")
