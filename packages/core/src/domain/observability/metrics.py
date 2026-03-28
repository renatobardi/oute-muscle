"""
T182: Cloud Monitoring custom metrics.

Defines and records three metric families:
  1. LLM latency per model  — histogram (ms)
  2. Rule match rates        — counter (rule_id × tenant)
  3. Tenant usage            — gauge (scans, findings, rules per tenant)

The metrics are emitted via the OpenTelemetry Metrics API so they work with
any exporter (GCP Cloud Monitoring, Prometheus, console).  At startup, the
application calls configure_metrics() to set up the GCP exporter.

Usage:
    from packages.core.src.domain.observability.metrics import (
        record_llm_call,
        record_rule_match,
        record_tenant_usage,
    )

    # Inside an LLM router:
    record_llm_call(model="gemini-2.5-flash", latency_ms=342.7, success=True)

    # Inside the finding service:
    record_rule_match(rule_id="unsafe-regex-001", tenant_id="tenant-abc")

    # Inside a background job:
    record_tenant_usage(tenant_id="tenant-abc", scans=12, findings=47, rules=8)
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenTelemetry instruments (lazily initialised)
# ---------------------------------------------------------------------------

_llm_latency_histogram = None      # Histogram[ms]
_rule_match_counter = None         # Counter
_tenant_scan_gauge = None          # ObservableGauge
_tenant_finding_gauge = None
_tenant_rule_gauge = None

_METER_NAME = "oute.muscle"
_SCHEMA_URL = "https://opentelemetry.io/schemas/1.24.0"


def configure_metrics(
    exporter: str = "gcp",
    gcp_project_id: Optional[str] = None,
    export_interval_seconds: int = 60,
) -> None:
    """
    Set up the OpenTelemetry metrics pipeline.

    Args:
        exporter:               "gcp" | "prometheus" | "console" | "none"
        gcp_project_id:         Required when exporter="gcp"
        export_interval_seconds: How often to push metrics (default 60s)
    """
    global _llm_latency_histogram, _rule_match_counter
    global _tenant_scan_gauge, _tenant_finding_gauge, _tenant_rule_gauge

    if exporter == "none":
        return

    try:
        from opentelemetry import metrics as otel_metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    except ImportError:
        log.warning("opentelemetry-sdk not installed — metrics disabled")
        return

    resource = Resource(attributes={SERVICE_NAME: "oute-muscle"})

    readers = []
    if exporter == "gcp":
        try:
            from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter

            readers.append(
                PeriodicExportingMetricReader(
                    CloudMonitoringMetricsExporter(project_id=gcp_project_id),
                    export_interval_millis=export_interval_seconds * 1000,
                )
            )
        except ImportError:
            log.warning("opentelemetry-exporter-gcp-monitoring not installed — metrics disabled")
            return

    elif exporter == "prometheus":
        try:
            from opentelemetry.exporter.prometheus import PrometheusMetricReader
            readers.append(PrometheusMetricReader())
        except ImportError:
            log.warning("opentelemetry-exporter-prometheus not installed")
            return

    elif exporter == "console":
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        readers.append(
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=export_interval_seconds * 1000,
            )
        )

    provider = MeterProvider(resource=resource, metric_readers=readers)
    otel_metrics.set_meter_provider(provider)

    meter = otel_metrics.get_meter(_METER_NAME, schema_url=_SCHEMA_URL)

    # LLM latency histogram (unit: ms)
    _llm_latency_histogram = meter.create_histogram(
        name="oute.llm.latency_ms",
        description="End-to-end latency of LLM API calls in milliseconds",
        unit="ms",
    )

    # Rule match counter
    _rule_match_counter = meter.create_counter(
        name="oute.rule.matches_total",
        description="Number of times a Semgrep rule matched a scan finding",
        unit="{matches}",
    )

    # Tenant usage gauges (driven by explicit record_tenant_usage calls)
    _tenant_scan_gauge = meter.create_up_down_counter(
        name="oute.tenant.scans_total",
        description="Total number of scans per tenant",
        unit="{scans}",
    )
    _tenant_finding_gauge = meter.create_up_down_counter(
        name="oute.tenant.findings_total",
        description="Total number of findings per tenant",
        unit="{findings}",
    )
    _tenant_rule_gauge = meter.create_up_down_counter(
        name="oute.tenant.rules_total",
        description="Total number of active Semgrep rules per tenant",
        unit="{rules}",
    )

    log.info("otel_metrics_configured", exporter=exporter)


# ---------------------------------------------------------------------------
# Public recording functions
# ---------------------------------------------------------------------------

def record_llm_call(
    model: str,
    latency_ms: float,
    success: bool,
    operation: str = "generate",
) -> None:
    """
    Record an LLM API call.

    Args:
        model:       Model identifier (e.g. "gemini-2.5-flash", "claude-sonnet-4")
        latency_ms:  Wall-clock time of the call in milliseconds
        success:     Whether the call completed without error
        operation:   Type of operation (e.g. "generate", "embed")
    """
    if _llm_latency_histogram is None:
        return
    _llm_latency_histogram.record(
        latency_ms,
        attributes={
            "model": model,
            "success": str(success).lower(),
            "operation": operation,
        },
    )


@contextmanager
def timed_llm_call(
    model: str,
    operation: str = "generate",
) -> Generator[None, None, None]:
    """
    Context manager that automatically records LLM call latency.

    Usage:
        with timed_llm_call(model="gemini-2.5-flash"):
            response = await vertex_ai.generate(...)
    """
    t0 = time.perf_counter()
    success = False
    try:
        yield
        success = True
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000
        record_llm_call(model=model, latency_ms=latency_ms, success=success, operation=operation)


def record_rule_match(
    rule_id: str,
    tenant_id: str,
    severity: str = "unknown",
) -> None:
    """
    Increment the rule match counter.

    Args:
        rule_id:   Semgrep rule ID (e.g. "unsafe-regex-001")
        tenant_id: Tenant that owns the scan
        severity:  Finding severity (error | warning | info)
    """
    if _rule_match_counter is None:
        return
    _rule_match_counter.add(
        1,
        attributes={
            "rule_id": rule_id,
            "tenant_id": tenant_id,
            "severity": severity,
        },
    )


def record_tenant_usage(
    tenant_id: str,
    scans: int = 0,
    findings: int = 0,
    rules: int = 0,
) -> None:
    """
    Record absolute tenant resource usage (scans, findings, rules).
    This is typically called from a nightly job that queries the DB.

    NOTE: These are up_down_counters, so pass the *delta* since the last call,
    or reset the gauge by passing negative values.  For simplicity, callers
    typically pass the full current count and rely on the OTEL exporter's
    cumulative-to-delta conversion.
    """
    attrs = {"tenant_id": tenant_id}
    if _tenant_scan_gauge is not None and scans:
        _tenant_scan_gauge.add(scans, attributes=attrs)
    if _tenant_finding_gauge is not None and findings:
        _tenant_finding_gauge.add(findings, attributes=attrs)
    if _tenant_rule_gauge is not None and rules:
        _tenant_rule_gauge.add(rules, attributes=attrs)
