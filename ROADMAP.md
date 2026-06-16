# Roadmap

PrismAgents feature roadmap — planned enhancements organized by priority.

---

## 🔜 Near-Term

### Account Management API
User-facing endpoints for profile management, settings, and usage history.
- Profile read/update (email, display name, avatar)
- Credit balance and usage history queries (by key, date range, action type)
- Account settings management

### Scoped API Keys
Restrict API keys to specific boards, agents, teams, or action types. Ships alongside Account Management API.
- Per-key permission scopes (board, agent, capability)
- Scope enforcement in auth middleware
- UI for configuring scopes during key creation

### Credit Usage Rate Limiting
User-configurable spending controls for API key usage.
- Daily, weekly, and monthly credit usage caps
- Per-key and account-level limits
- Configurable via account management endpoints and UI
- Alert notifications when approaching limits

### Automatic Credit Reloading
Automatically purchase credit packs when balance drops below a threshold. Available for Plus & Pro tiers.
- Configurable threshold and reload amount
- Stripe integration for automatic payments
- Usage notifications and reload receipts

---

## 🔮 Future

### Dedicated Programmatic Endpoints
Simplified endpoints designed for machine-to-machine use.
- `POST /v1/run` — synchronous endpoint accepting agent/team ID + message, returns full result as JSON (no SSE)
- Batch execution support
- Webhook callbacks for long-running generations

### Client SDKs
Lightweight client libraries for common languages.
- Python SDK (PyPI)
- JavaScript/TypeScript SDK (npm)
- Auto-generated from OpenAPI spec
- Authentication, streaming, and error handling built-in

---

## ✅ Shipped

### v0.2 — API Key Access (2026-06-14)
Programmatic access to PrismAgents via API keys for Plus+ tier users.
- `sk-prism-*` API keys with SHA-256 hashing (raw key never stored)
- Dual auth middleware (JWT + API key)
- `/api-keys` CRUD router (create, list, revoke)
- Plus+ tier gating with mandatory usage disclaimer
- Unified credits — API calls deduct from the same pool
- 19 tests, API reference documentation

### v0.1 — Chat File Attachments (2026-06-14)
Full-stack file attachment support in the chat interface.
- Image, video, and document (PDF, DOCX, TXT, MD) attachments
- Backend validation, text extraction, multimodal LLM integration
- Frontend attachment UI with loading/error states
- 213 backend tests
