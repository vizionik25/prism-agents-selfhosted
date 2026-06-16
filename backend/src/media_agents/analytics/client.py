"""
PostHog analytics client for PrismAgents.

Single source of truth for all backend analytics. Nothing outside this package
should import ``posthog`` directly — routers call ``analytics.capture(...)`` and
``analytics.identify(...)``.

Contract: see ``.telemetry/tracking-plan.yaml`` and ``.telemetry/instrument.md``.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from media_agents.env import get_env

logger = logging.getLogger(__name__)

INTERNAL_DOMAINS: frozenset[str] = frozenset({"vizionikmedia.com"})
INTERNAL_EMAILS: frozenset[str] = frozenset({"vizionik4@gmail.com"})


def is_internal_email(email: Optional[str]) -> bool:
    if not email:
        return False
    lower = email.lower()
    if lower in INTERNAL_EMAILS:
        return True
    if "@" not in lower:
        return False
    return lower.rsplit("@", 1)[-1] in INTERNAL_DOMAINS


class AnalyticsClient:
    """Thin wrapper around posthog-python with an internal-user guard."""

    def __init__(self) -> None:
        api_key = get_env("POSTHOG_API_KEY", "")
        host = get_env("POSTHOG_HOST", "https://us.i.posthog.com")
        self.enabled = bool(api_key)
        self._client: Any = None
        if not self.enabled:
            logger.info("POSTHOG_API_KEY not set — analytics disabled.")
            return
        try:
            from posthog import Posthog  # noqa: PLC0415
        except ImportError:
            logger.warning("posthog package not installed — analytics disabled.")
            self.enabled = False
            return
        self._client = Posthog(project_api_key=api_key, host=host)

    def identify(
        self,
        user_id: str,
        traits: dict[str, Any],
        *,
        email: Optional[str] = None,
    ) -> None:
        if not self.enabled or self._client is None:
            return
        payload = dict(traits)
        if is_internal_email(email or payload.get("email")):
            payload["is_internal"] = True
        try:
            self._client.identify(distinct_id=user_id, properties=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PostHog identify failed (user_id=%s): %s", user_id, exc)

    def capture(
        self,
        user_id: str,
        event: str,
        properties: Optional[dict[str, Any]] = None,
        *,
        email: Optional[str] = None,
        set_traits: Optional[dict[str, Any]] = None,
        set_once_traits: Optional[dict[str, Any]] = None,
    ) -> None:
        if not self.enabled or self._client is None:
            return
        if is_internal_email(email):
            return
        props: dict[str, Any] = dict(properties or {})
        if set_traits:
            props["$set"] = set_traits
        if set_once_traits:
            props["$set_once"] = set_once_traits
        try:
            self._client.capture(
                distinct_id=user_id,
                event=event,
                properties=props,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("PostHog capture failed (event=%s): %s", event, exc)

    def shutdown(self) -> None:
        if self._client is not None:
            try:
                self._client.shutdown()
            except Exception as exc:  # noqa: BLE001
                logger.warning("PostHog shutdown failed: %s", exc)


analytics = AnalyticsClient()
