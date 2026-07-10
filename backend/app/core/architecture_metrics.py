"""
ArchitectureMetrics — métricas de qualidade arquitetural (R1-F2).

Complementa Prometheus HTTP com agregações para Platform Health e Readiness.
"""
from collections import defaultdict
from threading import Lock
from typing import Any, Dict, List, Optional


class ArchitectureMetricsStore:
    """
    Store thread-safe de métricas arquiteturais in-process.

    Attributes:
        _lock: Mutex para contadores.
        _http_by_layer: Contagem requests por layer.
        _http_duration_sum: Soma durações por layer.
        _http_errors: Erros 4xx/5xx por layer.
        _events_published: Contagem por event_type.
        _events_consumed: Contagem handlers executados.
        _plugin_requests: Contagem por plugin_id.
        _acl_invocations: Contagem adapter ACL.
    """

    _instance: Optional["ArchitectureMetricsStore"] = None

    def __init__(self) -> None:
        """Inicializa contadores zerados."""
        self._lock = Lock()
        self._http_by_layer: Dict[str, int] = defaultdict(int)
        self._http_duration_sum: Dict[str, float] = defaultdict(float)
        self._http_errors: Dict[str, int] = defaultdict(int)
        self._events_published: Dict[str, int] = defaultdict(int)
        self._events_consumed: Dict[str, int] = defaultdict(int)
        self._plugin_requests: Dict[str, int] = defaultdict(int)
        self._acl_invocations: int = 0

    @classmethod
    def get(cls) -> "ArchitectureMetricsStore":
        """
        Retorna singleton do store.

        Returns:
            Instância global ArchitectureMetricsStore.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reseta métricas (testes).

        Returns:
            None
        """
        cls._instance = None

    def record_http(
        self,
        layer: str,
        duration_seconds: float,
        is_error: bool,
    ) -> None:
        """
        Registra requisição HTTP por camada.

        Args:
            layer: legacy | beautyos | core | identity | platform | other.
            duration_seconds: Latência da requisição.
            is_error: True se status 4xx ou 5xx.

        Returns:
            None
        """
        with self._lock:
            self._http_by_layer[layer] += 1
            self._http_duration_sum[layer] += duration_seconds
            if is_error:
                self._http_errors[layer] += 1

    def record_event_published(self, event_type: str, handler_count: int = 0) -> None:
        """
        Registra publicação de evento.

        Args:
            event_type: Tipo do evento.
            handler_count: Handlers invocados (consumos).

        Returns:
            None
        """
        with self._lock:
            self._events_published[event_type] += 1
            if handler_count:
                self._events_consumed[event_type] += handler_count

    def record_plugin_access(self, plugin_id: str) -> None:
        """
        Registra acesso a plugin.

        Args:
            plugin_id: ID do plugin.

        Returns:
            None
        """
        with self._lock:
            self._plugin_requests[plugin_id] += 1

    def record_acl_invocation(self) -> None:
        """
        Incrementa contador de invocações ACL.

        Returns:
            None
        """
        with self._lock:
            self._acl_invocations += 1

    def record_booking_create_core_path(self) -> None:
        """
        Incrementa contador de creates via domain core path (R2-F1).

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_booking_create_core"):
                self._booking_create_core = 0
            self._booking_create_core += 1

    def record_booking_create_legacy_path(self) -> None:
        """
        Incrementa contador de creates via ACL legado (R2-F1).

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_booking_create_legacy"):
                self._booking_create_legacy = 0
            self._booking_create_legacy += 1

    def record_booking_projection_failure(self) -> None:
        """
        Incrementa falhas de projeção legado no dual-write.

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_booking_projection_failures"):
                self._booking_projection_failures = 0
            self._booking_projection_failures += 1

    def record_idempotency_hit(self) -> None:
        """
        Incrementa cache hit de Idempotency-Key (R2-F1b).

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_idempotency_hits"):
                self._idempotency_hits = 0
            self._idempotency_hits += 1

    def record_idempotency_miss(self) -> None:
        """
        Incrementa primeira execução idempotente (R2-F1b).

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_idempotency_misses"):
                self._idempotency_misses = 0
            self._idempotency_misses += 1

    def record_idempotency_conflict(self) -> None:
        """
        Incrementa conflito idempotency key reutilizada com body diferente.

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_idempotency_conflicts"):
                self._idempotency_conflicts = 0
            self._idempotency_conflicts += 1

    def record_idempotency_missing_key(self) -> None:
        """
        Incrementa requests rejeitados sem Idempotency-Key.

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_idempotency_missing_key"):
                self._idempotency_missing_key = 0
            self._idempotency_missing_key += 1

    def record_event_correlation_id(self) -> None:
        """
        Incrementa eventos publicados com correlation_id (FF-EVT-006).

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_event_correlation_id"):
                self._event_correlation_id = 0
            self._event_correlation_id += 1

    def record_outbox_defer_commit(self) -> None:
        """
        Incrementa registros outbox com defer_commit (R2-F2 / TD-R2-F1b-001).

        Returns:
            None
        """
        with self._lock:
            if not hasattr(self, "_outbox_defer_commit"):
                self._outbox_defer_commit = 0
            self._outbox_defer_commit += 1

    def record_booking_approve_core_path(self) -> None:
        """Incrementa approve via domain core path (R2-F2)."""
        with self._lock:
            if not hasattr(self, "_booking_approve_core"):
                self._booking_approve_core = 0
            self._booking_approve_core += 1

    def record_booking_approve_legacy_path(self) -> None:
        """Incrementa approve via ACL legado (R2-F2)."""
        with self._lock:
            if not hasattr(self, "_booking_approve_legacy"):
                self._booking_approve_legacy = 0
            self._booking_approve_legacy += 1

    def record_booking_reject_core_path(self) -> None:
        """Incrementa reject via domain core path (R2-F2)."""
        with self._lock:
            if not hasattr(self, "_booking_reject_core"):
                self._booking_reject_core = 0
            self._booking_reject_core += 1

    def record_booking_reject_legacy_path(self) -> None:
        """Incrementa reject via ACL legado (R2-F2)."""
        with self._lock:
            if not hasattr(self, "_booking_reject_legacy"):
                self._booking_reject_legacy = 0
            self._booking_reject_legacy += 1

    def record_booking_version_conflict(self) -> None:
        """Incrementa conflitos optimistic lock (R2-F2)."""
        with self._lock:
            if not hasattr(self, "_booking_version_conflict"):
                self._booking_version_conflict = 0
            self._booking_version_conflict += 1

    def record_booking_deposit_required(self) -> None:
        """Incrementa approve bloqueado por sinal (P04)."""
        with self._lock:
            if not hasattr(self, "_booking_deposit_required"):
                self._booking_deposit_required = 0
            self._booking_deposit_required += 1

    def record_booking_cancel_core_path(self) -> None:
        """Incrementa cancel flag ON (R2-F2b)."""
        with self._lock:
            if not hasattr(self, "_booking_cancel_core_path"):
                self._booking_cancel_core_path = 0
            self._booking_cancel_core_path += 1

    def record_booking_cancel_legacy_path(self) -> None:
        """Incrementa cancel flag OFF (R2-F2b)."""
        with self._lock:
            if not hasattr(self, "_booking_cancel_legacy_path"):
                self._booking_cancel_legacy_path = 0
            self._booking_cancel_legacy_path += 1

    def record_booking_cancel_policy_violation(self) -> None:
        """Incrementa cancel bloqueado por policy 24h (P07)."""
        with self._lock:
            if not hasattr(self, "_booking_cancel_policy_violation"):
                self._booking_cancel_policy_violation = 0
            self._booking_cancel_policy_violation += 1

    def snapshot(self) -> Dict[str, Any]:
        """
        Snapshot JSON das métricas arquiteturais.

        Returns:
            Dict com http, events, plugins, acl e percentuais legacy/core.
        """
        with self._lock:
            total_http = sum(self._http_by_layer.values()) or 1
            legacy_count = (
                self._http_by_layer.get("legacy", 0)
                + self._http_by_layer.get("beautyos", 0)
            )
            core_count = self._http_by_layer.get("core", 0)
            avg_duration = {
                layer: (
                    self._http_duration_sum[layer] / self._http_by_layer[layer]
                    if self._http_by_layer[layer]
                    else 0.0
                )
                for layer in set(
                    list(self._http_by_layer.keys()) + list(self._http_duration_sum.keys())
                )
            }
            return {
                "http": {
                    "total": total_http,
                    "by_layer": dict(self._http_by_layer),
                    "errors_by_layer": dict(self._http_errors),
                    "avg_duration_seconds": avg_duration,
                    "legacy_percentage": round(legacy_count / total_http * 100, 2),
                    "core_percentage": round(core_count / total_http * 100, 2),
                },
                "events": {
                    "published": dict(self._events_published),
                    "consumed": dict(self._events_consumed),
                    "published_total": sum(self._events_published.values()),
                    "consumed_total": sum(self._events_consumed.values()),
                },
                "plugins": dict(self._plugin_requests),
                "acl_invocations": self._acl_invocations,
            }


def identified_couplings() -> List[Dict[str, str]]:
    """
    Lista acoplamentos conhecidos Core↔Legado (auditoria estática).

    Returns:
        Lista de dicts source, target, severity, remediation.
    """
    return [
        {
            "source": "booking/commands/*",
            "target": "app.services.reservation_service",
            "severity": "high",
            "remediation": "ACL LegacyBookingAdapter — Release 2",
        },
        {
            "source": "scheduling/engine/scheduling_engine.py",
            "target": "app.services.agenda_dia_service",
            "severity": "medium",
            "remediation": "Scheduling Port — Release 3",
        },
        {
            "source": "modules/ai/beauty_agent.py",
            "target": "app.services.agente_service",
            "severity": "medium",
            "remediation": "Mover para plugin beauty",
        },
        {
            "source": "*/legacy_sync_service.py",
            "target": "app.models.* legado",
            "severity": "expected",
            "remediation": "Strangler Fig — sunset gradual",
        },
    ]


def test_coverage_by_module() -> Dict[str, Any]:
    """
    Estima cobertura de testes por área via contagem de arquivos test_*.py.

    Returns:
        Dict module_area → {test_files, status}.
    """
    from pathlib import Path

    tests_root = Path(__file__).resolve().parents[2] / "tests"
    mapping = {
        "core_platform": ["test_r1_f1", "test_r1_f2", "test_cf8", "test_coreflow"],
        "booking": ["test_cf", "booking"],
        "scheduling": ["scheduling"],
        "identity": ["identity", "test_modules"],
        "events": ["outbox", "event", "test_cf13", "test_cf14"],
        "mobile": ["test_cf15", "test_cf16", "mobile", "eas"],
        "plugins": ["plugin"],
    }
    result: Dict[str, Any] = {}
    all_tests = list(tests_root.rglob("test_*.py"))
    for area, patterns in mapping.items():
        matched = [
            p.name
            for p in all_tests
            if any(pat in str(p) for pat in patterns)
        ]
        result[area] = {
            "test_files": len(matched),
            "status": "covered" if matched else "gap",
        }
    result["_total_test_files"] = len(all_tests)
    return result
