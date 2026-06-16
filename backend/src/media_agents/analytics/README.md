# analytics — PostHog integration

Single source of truth for backend analytics. Do not import `posthog` outside
this package; always go through `analytics.capture(...)` / `analytics.identify(...)`.

Contract: `.telemetry/tracking-plan.yaml` v1, `.telemetry/instrument.md`.

## Files

- `client.py` — `AnalyticsClient` with send-time internal-user guard; module-level singleton `analytics`.
- `events.py` — every tracked event name as a `Final[str]` constant. No raw event-name strings anywhere.
- `traits.py` — helpers that build `identify()` payloads from a Prisma User row.
- (sibling) `scripts/sync_analytics_traits.py` — daily reconciliation job.

## Environment

| Var | Required | Default |
|---|---|---|
| `POSTHOG_API_KEY` | yes | — |
| `POSTHOG_HOST`    | no  | `https://us.i.posthog.com` |

When `POSTHOG_API_KEY` is unset, the client is a no-op — safe for dev / CI.

## Usage

```python
from media_agents.analytics import analytics
from media_agents.analytics.events import GENERATION_COMPLETED

analytics.capture(
    user_id=str(user_id),
    event=GENERATION_COMPLETED,
    email=current_user.get("email"),  # used ONLY for the internal-user guard
    properties={
        "generation_id": str(gen_id),
        "board_id": str(board_id),
        "status": "succeeded",
        "duration_ms": 1234,
        # ...
    },
)
```

`email` is a guard parameter — it is never forwarded to PostHog's event
properties. PII policy is `traits_only` per the tracking plan.

## Reconciliation

```
uv run python -m scripts.sync_analytics_traits
```

Runs `identify()` with `full_identify_payload(user)` for every user. Safe to
run repeatedly — PostHog merges traits by `distinct_id`. Schedule daily.

## Adding a new event

1. Add the event to `.telemetry/tracking-plan.yaml` (and bump `meta.version`).
2. Add a constant to `events.py`.
3. Wire the `analytics.capture(...)` call in the appropriate router.
4. Update `.telemetry/delta.md` with the change.
