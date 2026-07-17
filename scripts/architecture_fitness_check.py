#!/usr/bin/env python3
"""
Architecture Fitness Check — R2-F5 ERROR gate (ArchitectureFitnessFunctions v2).

Exit 0 = PASS · Exit 1 = FAIL (merge bloqueado quando usado no CI).
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
MODULES = BACKEND / "app" / "modules"


def _fail(violations: List[str]) -> int:
    """
    Imprime violações e retorna código de saída.

    Args:
        violations: Lista de mensagens.

    Returns:
        1 se houver violações, senão 0.
    """
    if not violations:
        print("architecture_fitness_check: PASS (F5)")
        return 0
    print("architecture_fitness_check: FAIL")
    for item in violations:
        print(f"  - {item}")
    return 1


def check_ff_cpl_001() -> List[str]:
    """
    FF-CPL-001: coupling ≤ 3.

    Returns:
        Lista de violações.
    """
    sys.path.insert(0, str(BACKEND))
    from app.core.architecture_metrics import identified_couplings

    n = len(identified_couplings())
    if n > 3:
        return [f"FF-CPL-001: identified_couplings={n} > 3"]
    return []


def check_ff_plg_005() -> List[str]:
    """
    FF-PLG-005: zero imports beauty em modules/ (exceto tests).

    Returns:
        Lista de violações.
    """
    violations: List[str] = []
    pattern = re.compile(
        r"from\s+app\.plugins\.beauty|import\s+app\.plugins\.beauty|modules\.ai\.beauty_agent"
    )
    for path in MODULES.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            rel = path.relative_to(REPO_ROOT)
            violations.append(f"FF-PLG-005: beauty import em {rel}")
    return violations


def check_ff_bkg_commands() -> List[str]:
    """
    FF-BKG-001/002: commands booking não importam ReservationService/LegacySyncService.

    Returns:
        Lista de violações.
    """
    violations: List[str] = []
    commands = BACKEND / "app" / "modules" / "booking" / "application" / "commands"
    if not commands.is_dir():
        return ["FF-BKG: pasta commands ausente"]
    forbidden = ("ReservationService", "LegacySyncService", "reservation_service")
    for path in commands.glob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text and "LegacyBookingAdapter" not in token:
                # permite menção em docstring se for só comentário — grepa imports
                if re.search(rf"(from|import).*{re.escape(token)}", text):
                    violations.append(f"FF-BKG: {path.name} importa {token}")
    return violations


def check_ff_hex_006() -> List[str]:
    """
    FF-HEX-006: Catalog + Customer repository ports existem.

    Returns:
        Lista de violações.
    """
    violations: List[str] = []
    catalog = (
        MODULES / "catalog" / "application" / "ports" / "catalog_repository.py"
    )
    customer = (
        MODULES / "customer" / "application" / "ports" / "customer_repository.py"
    )
    if not catalog.is_file():
        violations.append("FF-HEX-006: CatalogRepository ausente")
    if not customer.is_file():
        violations.append("FF-HEX-006: CustomerRepository ausente")
    return violations


def check_ff_obs_001() -> List[str]:
    """
    FF-OBS-001: span booking.create.core no create path.

    Returns:
        Lista de violações.
    """
    create_path = (
        MODULES
        / "booking"
        / "application"
        / "commands"
        / "create_booking.py"
    )
    text = create_path.read_text(encoding="utf-8", errors="ignore")
    if "booking.create.core" not in text and "booking_create_core_span" not in text:
        return ["FF-OBS-001: span booking.create.core ausente em create_booking"]
    telemetry = BACKEND / "app" / "core" / "telemetry.py"
    ttext = telemetry.read_text(encoding="utf-8", errors="ignore")
    if "booking.create.core" not in ttext:
        return ["FF-OBS-001: booking.create.core não definido em telemetry.py"]
    return []


def check_ff_obs_002() -> List[str]:
    """
    FF-OBS-002: métrica drift_count registrada.

    Returns:
        Lista de violações.
    """
    violations: List[str] = []
    prom = (BACKEND / "app" / "core" / "prometheus_metrics.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    if "coreflow_booking_legacy_sync_drift_count" not in prom:
        violations.append("FF-OBS-002: gauge Prometheus drift ausente")
    metrics = (BACKEND / "app" / "core" / "architecture_metrics.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    if "record_booking_drift_count" not in metrics:
        violations.append("FF-OBS-002: ArchitectureMetricsStore.record_booking_drift_count ausente")
    worker = BACKEND / "app" / "workers" / "booking_reconciliation_worker.py"
    if not worker.is_file():
        violations.append("FF-OBS-002: booking_reconciliation_worker ausente")
    return violations


def check_ff_tst_001() -> List[str]:
    """
    FF-TST-001: coleta de testes ≥ 300.

    Returns:
        Lista de violações.
    """
    # Contagem estática de arquivos test_*.py * funções def test_ (rápida, sem pytest)
    tests_root = BACKEND / "tests"
    count = 0
    for path in tests_root.rglob("test_*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                count += 1
    if count < 300:
        return [f"FF-TST-001: test functions={count} < 300"]
    return []


def run_phase_f5() -> List[str]:
    """
    Executa regras ERROR do gate F5.

    Returns:
        Lista consolidada de violações.
    """
    checks = [
        check_ff_cpl_001,
        check_ff_plg_005,
        check_ff_bkg_commands,
        check_ff_hex_006,
        check_ff_obs_001,
        check_ff_obs_002,
        check_ff_tst_001,
    ]
    violations: List[str] = []
    for check in checks:
        violations.extend(check())
    return violations


def main() -> int:
    """
    Entry point CLI.

    Returns:
        Código de saída 0/1.
    """
    parser = argparse.ArgumentParser(description="CoreFlow architecture fitness (R2-F5)")
    parser.add_argument("--phase", default="f5", choices=["f5"])
    args = parser.parse_args()
    if args.phase == "f5":
        return _fail(run_phase_f5())
    return _fail([f"phase desconhecida: {args.phase}"])


if __name__ == "__main__":
    sys.exit(main())
