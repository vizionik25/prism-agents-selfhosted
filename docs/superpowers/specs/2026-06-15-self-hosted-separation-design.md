# Design Spec: PrismAgents Self-Hosted Separation

This document specifies the complete renaming, branding separation, credentials cleanup, and Stripe removal for the self-hosted offering.

## 1. Naming & Rebranding

- **Product Name**: "PrismAgents self-hosted" / "PrismAgents Self-Hosted"
- **Backend Python Package**: `prism_agents_self_hosted` (renamed from `media_agents`)
- **Default Config**:
  - `SELF_HOSTED` defaults to `true` in `backend/src/prism_agents_self_hosted/env.py`.
  - `NEXT_PUBLIC_SELF_HOSTED` defaults to `true` in `frontend/.env.example`.

## 2. Stripe Billing Removal

- Remove the `stripe` python library from `backend/pyproject.toml`.
- Remove `@stripe/stripe-js` and `@stripe/react-stripe-js` from `frontend/package.json`.
- Stub `frontend/src/components/billing/upgrade-modal.tsx` to prevent compile errors without Stripe packages.
- Rewrite `backend/src/prism_agents_self_hosted/routers/billing.py` to remove all imports and usage of `stripe`. Stub endpoints:
  - `GET /billing/status` -> returns `tier: "ENTERPRISE"`, unlimited credits.
  - `POST /billing/checkout` -> returns `501 Not Implemented`.
  - `POST /billing/webhook` -> returns `501 Not Implemented`.
  - `GET /billing/portal` -> returns `501 Not Implemented`.
- Remove Stripe pricing and keys from all `.env.example`, `docker-compose.yml`, and `render.yaml` configurations.

## 3. Credentials & Telemetry Separation

- **Sentry**:
  - Clear Sentry DSN values in `.env.example` files and `render.yaml`.
  - Make `org` and `project` read from environment variables (`SENTRY_ORG`, `SENTRY_PROJECT`) in `frontend/next.config.ts`.
- **PostHog**:
  - Clear personal domains/emails (`vizionikmedia.com`, `vizionik4@gmail.com`) from telemetry filtering.
- **Repository / Paths**:
  - Replace `vizionik25/prism-agents` and local path `/Users/vizionik` in `DEPLOYMENT.md` and specs with generic placeholders.
