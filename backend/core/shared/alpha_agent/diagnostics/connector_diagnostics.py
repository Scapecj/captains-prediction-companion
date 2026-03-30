"""Shared diagnostics helpers for alpha_agent connectors."""

from __future__ import annotations

from typing import Any


def classify_exception(exc: Exception) -> tuple[bool, list[str], bool]:
    """Convert connector exceptions into auth/alert/degraded signals."""
    message = str(exc).lower()
    alerts: list[str] = []
    auth_ok = True
    degraded_mode = False

    if any(token in message for token in ("429", "rate limit", "rate_limited")):
        alerts.append("http_429")
        degraded_mode = True
    if "partial outage" in message or "partial_outage" in message:
        alerts.append("partial_outage")
        degraded_mode = True
    if any(
        token in message
        for token in ("401", "403", "api key", "auth failed", "not set", "private key")
    ):
        auth_ok = False
    if any(token in message for token in ("timeout", "temporarily unavailable", "connection reset")):
        degraded_mode = True

    if not alerts and degraded_mode:
        alerts.append("connector_degraded")

    return auth_ok, alerts, degraded_mode


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
