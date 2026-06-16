"""PostHog analytics — see .telemetry/instrument.md for the integration contract."""

from .client import analytics, is_internal_email
from . import events
from . import traits

__all__ = ["analytics", "events", "traits", "is_internal_email"]
