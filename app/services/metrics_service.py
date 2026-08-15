"""Business metrics service — TASK-007 (FASE 8).

Métricas prometheus-style en memoria + endpoint de exposición.
No requiere dependencia ``prometheus-client`` (solo stdlib + mode in-memory
thread-safe), alineado con el constraint de no añadir dependencias pesadas.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Counter:
    value: int = 0
    labels: dict[str, str] = field(default_factory=dict)

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class Histogram:
    buckets: list[float] = field(
        default_factory=lambda: [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1,
            2.5,
            5,
            10,
        ]
    )
    counts: dict[float, int] = field(default_factory=lambda: defaultdict(int))
    sum_value: float = 0.0
    count: int = 0
    labels: dict[str, str] = field(default_factory=dict)

    def observe(self, value: float) -> None:
        self.sum_value += value
        self.count += 1
        for b in self.buckets:
            if value <= b:
                self.counts[b] += 1


class MetricsRegistry:
    """Registro de métricas en memoria, thread-safe (singleton).

    ``counter`` / ``histogram`` devuelven el mismo objeto para los mismos
    ``(name, labels)`` (clave canónica por orden alfabético de labels).
    """

    _instance: MetricsRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> MetricsRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    self = super().__new__(cls)
                    self._counters: dict[str, list[Counter]] = defaultdict(list)
                    self._histograms: dict[str, list[Histogram]] = defaultdict(list)
                    cls._instance = self
        return cls._instance

    def counter(self, name: str, labels: dict[str, str] | None = None) -> Counter:
        labels = labels or {}
        key = self._label_key(labels)
        for c in self._counters[name]:
            if self._label_key(c.labels) == key:
                return c
        c = Counter(labels=labels)
        self._counters[name].append(c)
        return c

    def histogram(self, name: str, labels: dict[str, str] | None = None) -> Histogram:
        labels = labels or {}
        key = self._label_key(labels)
        for h in self._histograms[name]:
            if self._label_key(h.labels) == key:
                return h
        h = Histogram(labels=labels)
        self._histograms[name].append(h)
        return h

    @staticmethod
    def _label_key(labels: dict[str, str]) -> str:
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def to_prometheus(self) -> str:
        lines: list[str] = []
        for name, counters in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            for c in counters:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(c.labels.items()))
                if label_str:
                    lines.append(f"{name}{{{label_str}}} {c.value}")
                else:
                    lines.append(f"{name} {c.value}")
        for name, histograms in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            for h in histograms:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(h.labels.items()))
                for b in h.buckets:
                    bucket_label = f'le="{b}"'
                    if label_str:
                        lines.append(f"{name}{{{label_str},{bucket_label}}} {h.counts[b]}")
                    else:
                        lines.append(f"{name}_bucket{{{bucket_label}}} {h.counts[b]}")
                if label_str:
                    lines.append(f'{name}{{{label_str},le="+Inf"}} {h.count}')
                    lines.append(f"{name}_sum{{{label_str}}} {h.sum_value}")
                    lines.append(f"{name}_count{{{label_str}}} {h.count}")
                else:
                    lines.append(f'{name}_bucket{{le="+Inf"}} {h.count}')
                    lines.append(f"{name}_sum {h.sum_value}")
                    lines.append(f"{name}_count {h.count}")
        return "\n".join(lines)


metrics = MetricsRegistry()


def record_search_request(provider: str) -> None:
    metrics.counter("search_requests_total", {"provider": provider}).inc()


def record_opportunity_generated() -> None:
    metrics.counter("opportunities_generated_total").inc()


def record_search_order_duration(seconds: float) -> None:
    metrics.histogram("search_order_duration_seconds").observe(seconds)