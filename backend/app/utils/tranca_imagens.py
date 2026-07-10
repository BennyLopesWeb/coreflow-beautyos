"""
Utilitários para galeria de imagens de tranças.
"""
from pathlib import Path
from typing import List
import re

STATIC_TRANCAS = Path(__file__).resolve().parents[2] / "static" / "trancas"


def slug_para_arquivos(slug: str) -> List[str]:
    """
    Retorna caminhos de arquivos de imagem para um slug, ordenados (Foto 1, 2, ...).

    Convenção de nomes:
    - {slug}.png ou {slug}.jpg  → Foto 1
    - {slug}-2.png, {slug}-3.png → Fotos seguintes
    - {slug}-1.png também aceito como Foto 1

    Args:
        slug: Identificador do arquivo (ex: 'nago', 'fulani-braids').

    Returns:
        Lista de Paths existentes, ordenados para exibição.
    """
    if not STATIC_TRANCAS.is_dir():
        return []

    extensoes = {".png", ".jpg", ".jpeg", ".webp"}
    encontrados: dict[int, Path] = {}

    for path in STATIC_TRANCAS.iterdir():
        if path.suffix.lower() not in extensoes:
            continue
        stem = path.stem
        # slug-2, slug-3
        match = re.match(rf"^{re.escape(slug)}-(\d+)$", stem)
        if match:
            encontrados[int(match.group(1))] = path
            continue
        # slug (foto 1)
        if stem == slug:
            encontrados[1] = path
        # slug-1 explicit
        if stem == f"{slug}-1":
            encontrados[1] = path

    return [encontrados[k] for k in sorted(encontrados.keys())]


def urls_galeria(slug: str, base_url: str = "http://localhost:8000") -> List[str]:
    """
    Monta URLs públicas da galeria a partir dos arquivos no disco.

    Args:
        slug: Identificador do estilo (ex: 'nago').
        base_url: URL base da API.

    Returns:
        Lista de URLs ordenadas (Foto 1, Foto 2, ...).
    """
    arquivos = slug_para_arquivos(slug)
    base = base_url.rstrip("/")
    return [f"{base}/static/trancas/{p.name}" for p in arquivos]


def url_imagem_principal(slug: str, base_url: str = "http://localhost:8000") -> str | None:
    """
    Retorna URL da foto principal ({slug}.png) se existir no disco.

    Args:
        slug: Slug da trança.
        base_url: URL base da API.

    Returns:
        URL da foto principal ou None.
    """
    arquivos = slug_para_arquivos(slug)
    if not arquivos:
        return None
    base = base_url.rstrip("/")
    return f"{base}/static/trancas/{arquivos[0].name}"


def url_pertence_ao_slug(url: str, slug: str) -> bool:
    """
    Verifica se a URL aponta para arquivo deste slug (ex: box-braids, box-braids-2).

    Args:
        url: URL pública da imagem.
        slug: Slug da trança.

    Returns:
        True se o arquivo pertence exclusivamente a este tipo.
    """
    marker = "/static/trancas/"
    idx = url.find(marker)
    if idx < 0:
        return False
    nome = url[idx + len(marker):].split("?")[0]
    if not nome or ".." in nome:
        return False
    stem = Path(nome).stem
    return stem == slug or stem.startswith(f"{slug}-")


def url_para_arquivo(url: str) -> Path | None:
    """
    Extrai Path local a partir de URL pública /static/trancas/{arquivo}.

    Args:
        url: URL completa ou relativa da imagem.

    Returns:
        Path do arquivo se estiver em static/trancas, senão None.
    """
    marker = "/static/trancas/"
    idx = url.find(marker)
    if idx < 0:
        return None
    nome = url[idx + len(marker):].split("?")[0]
    if not nome or ".." in nome:
        return None
    path = STATIC_TRANCAS / nome
    return path if path.is_file() else None
