# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────
# PrismAgents frontend — Next.js 16 + React 19 + Tailwind v4
# Multi-stage build optimized for self-hosted deployments
# ──────────────────────────────────────────────────────────────

# ── Builder ──────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies with BuildKit cache
RUN --mount=type=cache,id=npm-cache,target=/root/.npm \
    --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    npm ci

# Copy source and build
COPY . .

# Build the Next.js application
RUN npm run build

# ── Runtime ──────────────────────────────────────────────────
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy built assets
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/health || exit 1

CMD ["node", "server.js"]