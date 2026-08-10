"""Shared, plain-language explanation helpers."""

from __future__ import annotations


DISCLAIMER = (
    "This recommendation is automated financial decision support, not "
    "professional financial advice or a guaranteed outcome."
)


def kes(value: float) -> str:
    return f"KES {value:,.2f}"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"
