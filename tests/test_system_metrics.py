"""Real system-monitor contracts for the terminal command-center overview."""

from __future__ import annotations

from pathlib import Path

import pytest


class FakeClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_sampler_calculates_cpu_from_counter_deltas_and_real_memory() -> None:
    from a_conductor.system_metrics import SystemMetricsSampler

    clock = FakeClock()
    cpu_samples = iter(((100, 1000), (130, 1200)))
    sampler = SystemMetricsSampler(
        clock=clock,
        cpu_times_reader=lambda: next(cpu_samples),
        memory_reader=lambda: (6 * 1024**3, 32 * 1024**3),
    )
    clock.value = 105.0
    metrics = sampler.sample()
    # total delta=200, idle delta=30 => 85% busy
    assert metrics.cpu_percent == pytest.approx(85.0)
    assert metrics.memory_used_bytes == 6 * 1024**3
    assert metrics.memory_total_bytes == 32 * 1024**3
    assert metrics.uptime_seconds == pytest.approx(5.0)


def test_sampler_clamps_bad_cpu_delta_and_degrades_unavailable_memory() -> None:
    from a_conductor.system_metrics import SystemMetricsSampler

    clock = FakeClock()
    cpu_samples = iter(((100, 1000), (400, 1200)))
    sampler = SystemMetricsSampler(
        clock=clock,
        cpu_times_reader=lambda: next(cpu_samples),
        memory_reader=lambda: None,
    )
    metrics = sampler.sample()
    assert metrics.cpu_percent == 0.0
    assert metrics.memory_used_bytes is None
    assert metrics.memory_total_bytes is None


def test_system_metric_formatters_are_compact_and_honest() -> None:
    from a_conductor.system_metrics import format_memory, format_percent, format_uptime

    assert format_percent(None) == "—"
    assert format_percent(18.24) == "18%"
    assert format_memory(None, None) == "—"
    assert format_memory(6.2 * 1024**3, 32 * 1024**3) == "6.2 / 32.0 GB"
    assert format_uptime(65) == "00:01:05"
    assert format_uptime(2 * 86400 + 14 * 3600 + 37 * 60) == "2d 14h 37m"


def test_collector_source_never_uses_subprocess() -> None:
    source = Path("src/a_conductor/system_metrics.py").read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "powershell" not in source.lower()
    assert "cmd.exe" not in source.lower()


def test_real_sampler_is_safe_to_call_on_current_platform() -> None:
    from a_conductor.system_metrics import SystemMetricsSampler

    sampler = SystemMetricsSampler()
    metrics = sampler.sample()
    assert metrics.uptime_seconds >= 0
    if metrics.cpu_percent is not None:
        assert 0.0 <= metrics.cpu_percent <= 100.0
    if metrics.memory_total_bytes is not None:
        assert metrics.memory_total_bytes > 0
        assert metrics.memory_used_bytes is not None
        assert 0 <= metrics.memory_used_bytes <= metrics.memory_total_bytes
