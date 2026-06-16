"""Tests for the generations router's status normalization.

The Prisma `GenerationStatus` enum is uppercase in the DB; the HTTP API contract
(plus the TypeScript Generation.status type on the frontend) is lowercase. The
boundary normalization lives in `_format_status`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from media_agents.routers.generations import _format_datetime, _format_status


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("PENDING", "pending"),
        ("PROCESSING", "processing"),
        ("COMPLETED", "completed"),
        ("FAILED", "failed"),
        ("pending", "pending"),  # idempotent
    ],
)
def test_format_status_lowercases(raw: str, expected: str) -> None:
    assert _format_status(raw) == expected


def test_format_status_handles_non_string() -> None:
    """Defensive: if Prisma ever returns an enum object instead of a string."""

    class FakeEnum:
        def __str__(self) -> str:
            return "COMPLETED"

    assert _format_status(FakeEnum()) == "completed"


def test_format_datetime_iso_roundtrip() -> None:
    dt = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
    out = _format_datetime(dt)
    assert out == "2026-04-13T12:00:00+00:00"


def test_format_datetime_passes_through_strings() -> None:
    assert _format_datetime("2026-04-13T12:00:00Z") == "2026-04-13T12:00:00Z"
