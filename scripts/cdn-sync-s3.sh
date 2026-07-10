#!/usr/bin/env bash
# CDN S3/CloudFront sync helper (CF-17).
set -euo pipefail

DRY_RUN="${1:-true}"

cd "$(dirname "$0")/../backend"

python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.cdn_s3_sync_service import CdnS3SyncService

plugin_registry.load_all()
dry = '${DRY_RUN}'.lower() in ('1', 'true', 'yes')
result = CdnS3SyncService().sync_all(dry_run=dry)
print(result)
"
