"""
CdnS3SyncService — sync automatizado CDN → S3 + invalidação CloudFront (CF-17).
"""
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.mobile.application.plugin_cdn_service import PluginCdnService, CDN_DIR

logger = get_logger("cdn_s3_sync")

WELL_KNOWN_CONTENT_TYPES = {
    "apple-app-site-association": "application/json",
    "assetlinks.json": "application/json",
}


class CdnS3SyncService:
    """
    Sincroniza arquivos ``backend/cdn/`` para S3 e invalida CloudFront.

    Em modo dry-run (default sem bucket) apenas simula uploads.
    """

    def __init__(self, cdn_dir: Optional[Path] = None):
        """
        Args:
            cdn_dir: Raiz local do CDN (default backend/cdn).
        """
        self.cdn_dir = cdn_dir or CDN_DIR
        self.plugin_cdn = PluginCdnService(cdn_dir=self.cdn_dir)

    def _s3_client(self):
        """
        Lazy init boto3 S3 client.

        Returns:
            Instância boto3.client('s3').

        Raises:
            ImportError: Se boto3 não estiver instalado.
        """
        try:
            import boto3
        except ImportError as exc:
            raise ImportError("boto3 necessário para sync S3 — pip install boto3") from exc

        return boto3.client("s3", region_name=settings.CDN_S3_REGION)

    def _cloudfront_client(self):
        """
        Lazy init boto3 CloudFront client.

        Returns:
            Instância boto3.client('cloudfront').
        """
        try:
            import boto3
        except ImportError as exc:
            raise ImportError("boto3 necessário para CloudFront") from exc

        return boto3.client("cloudfront", region_name=settings.CDN_S3_REGION)

    def collect_files(self) -> List[Dict[str, Any]]:
        """
        Lista arquivos locais prontos para upload.

        Returns:
            Lista de dicts com local_path, s3_key, content_type, cache_control.
        """
        if not self.cdn_dir.is_dir():
            return []

        cache = f"public, max-age={settings.MOBILE_WELL_KNOWN_CACHE_SECONDS}"
        files: List[Dict[str, Any]] = []

        for path in sorted(self.cdn_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.cdn_dir).as_posix()
            s3_key = f"{settings.CDN_S3_PREFIX.rstrip('/')}/{relative}"
            content_type = self._content_type(path)
            files.append(
                {
                    "local_path": str(path),
                    "relative_path": relative,
                    "s3_key": s3_key,
                    "content_type": content_type,
                    "cache_control": cache,
                }
            )
        return files

    def sync_all(self, dry_run: Optional[bool] = None) -> Dict[str, Any]:
        """
        Exporta CDN local (se necessário) e sincroniza para S3.

        Args:
            dry_run: Simular sem upload; default settings.CDN_S3_DRY_RUN ou sem bucket.

        Returns:
            Resumo com uploaded, skipped e paths invalidados.
        """
        from app.core.plugin.registry import plugin_registry

        plugin_registry.load_all()
        self.plugin_cdn.export_all_plugins()

        files = self.collect_files()
        is_dry = dry_run if dry_run is not None else self._is_dry_run()
        uploaded: List[str] = []
        errors: List[str] = []

        if is_dry:
            for item in files:
                uploaded.append(item["s3_key"])
            logger.info(f"[cdn-s3] Dry-run: {len(uploaded)} arquivos simulados")
            return {
                "dry_run": True,
                "bucket": settings.CDN_S3_BUCKET or None,
                "uploaded": uploaded,
                "uploaded_count": len(uploaded),
                "errors": errors,
                "cloudfront_invalidation": None,
            }

        client = self._s3_client()
        bucket = settings.CDN_S3_BUCKET

        for item in files:
            try:
                with open(item["local_path"], "rb") as handle:
                    client.put_object(
                        Bucket=bucket,
                        Key=item["s3_key"],
                        Body=handle.read(),
                        ContentType=item["content_type"],
                        CacheControl=item["cache_control"],
                    )
                uploaded.append(item["s3_key"])
            except Exception as exc:
                errors.append(f"{item['s3_key']}: {exc}")
                logger.error(f"[cdn-s3] Falha upload {item['s3_key']}: {exc}")

        invalidation = None
        if settings.CDN_CLOUDFRONT_DISTRIBUTION_ID and uploaded:
            invalidation = self.invalidate_cloudfront(
                paths=[f"/{p.split('/', 1)[-1]}" if '/' in p else f"/{p}" for p in uploaded]
            )

        return {
            "dry_run": False,
            "bucket": bucket,
            "uploaded": uploaded,
            "uploaded_count": len(uploaded),
            "errors": errors,
            "cloudfront_invalidation": invalidation,
        }

    def invalidate_cloudfront(self, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Cria invalidação CloudFront para paths do CDN.

        Args:
            paths: Paths relativos (ex.: /.well-known/assetlinks.json).

        Returns:
            Resposta da API create_invalidation ou dict dry-run.
        """
        dist_id = settings.CDN_CLOUDFRONT_DISTRIBUTION_ID
        if not dist_id:
            return {"status": "skipped", "reason": "CDN_CLOUDFRONT_DISTRIBUTION_ID não configurado"}

        normalized = paths or ["/*"]
        cf_paths = []
        for path in normalized:
            if not path.startswith("/"):
                path = f"/{path}"
            cf_paths.append(path)

        if self._is_dry_run():
            return {
                "status": "dry_run",
                "distribution_id": dist_id,
                "paths": cf_paths,
            }

        client = self._cloudfront_client()
        import uuid

        response = client.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={
                "Paths": {"Quantity": len(cf_paths), "Items": cf_paths},
                "CallerReference": str(uuid.uuid4()),
            },
        )
        inv = response.get("Invalidation", {})
        logger.info(f"[cdn-s3] CloudFront invalidation {inv.get('Id')} paths={cf_paths}")
        return {
            "status": "created",
            "invalidation_id": inv.get("Id"),
            "paths": cf_paths,
        }

    def _is_dry_run(self) -> bool:
        """
        Determina se sync deve rodar em dry-run.

        Returns:
            True se S3 desabilitado, dry_run explícito ou bucket vazio.
        """
        if settings.CDN_S3_DRY_RUN:
            return True
        if not settings.CDN_S3_ENABLED:
            return True
        if not settings.CDN_S3_BUCKET:
            return True
        return False

    @staticmethod
    def _content_type(path: Path) -> str:
        """
        Resolve Content-Type para arquivo CDN.

        Args:
            path: Caminho local do arquivo.

        Returns:
            MIME type adequado.
        """
        if path.name in WELL_KNOWN_CONTENT_TYPES:
            return WELL_KNOWN_CONTENT_TYPES[path.name]
        guessed, _ = mimetypes.guess_type(str(path))
        return guessed or "application/octet-stream"
