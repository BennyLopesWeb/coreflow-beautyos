"""
Canary Rollback Worker — scan automático de degradação canary (CF-24).

Executa ``EasUpdateCanaryRollbackService.scan_and_rollback`` em loop
para reverter deployments OTA quando health cai após promote.
"""
import argparse
import time

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_rollback_service import (
    EasUpdateCanaryRollbackService,
)

logger = get_logger("canary_rollback_worker")


def run_once() -> dict:
    """
    Executa um ciclo de scan + rollback canary.

    Returns:
        Resumo do scan com counts e results.
    """
    from app.db.session import SessionLocal

    plugin_registry.load_all()
    db = SessionLocal()
    try:
        return EasUpdateCanaryRollbackService(db=db).scan_and_rollback()
    finally:
        db.close()


def run_loop(interval_seconds: float = 120.0) -> None:
    """
    Loop contínuo de monitoramento canary com intervalo fixo.

    Args:
        interval_seconds: Segundos entre scans.

    Returns:
        None
    """
    logger.info(f"[canary-rollback-worker] Loop — intervalo {interval_seconds}s")
    while True:
        try:
            result = run_once()
            if result.get("scanned", 0) or result.get("counts", {}).get("rollback"):
                logger.info(f"[canary-rollback-worker] Scan: {result.get('counts')}")
        except Exception as exc:
            logger.error(f"[canary-rollback-worker] Erro: {exc}")
        time.sleep(interval_seconds)


def main() -> None:
    """
    CLI entrypoint do worker de rollback canary.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="CoreFlow Canary Rollback Worker (CF-24)")
    parser.add_argument(
        "--mode",
        choices=["once", "loop"],
        default="once",
        help="Executar uma vez ou loop contínuo",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=settings.MOBILE_EAS_UPDATE_CANARY_ROLLBACK_INTERVAL_SECONDS,
        help="Intervalo loop (s)",
    )
    args = parser.parse_args()

    if args.mode == "loop":
        run_loop(args.interval)
        return

    result = run_once()
    print(f"✅ Canary rollback scan: {result}")


if __name__ == "__main__":
    main()
