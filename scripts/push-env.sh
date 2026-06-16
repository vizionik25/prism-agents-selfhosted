#!/usr/bin/env bash
# Push env vars from local dotenv files to Render (backend) and Vercel (frontend).
#
# Backend path is *not* fully automated by design: Render's REST API for env
# vars is a full-list PUT — partial pushes wipe vars that aren't in the
# payload, which is a destructive footgun for production secrets. So this
# script produces a sanitized `backend/.env.render` file that you drag-drop
# into the Render dashboard:
#
#   Render Dashboard → service → Environment → "Add from .env file" → upload
#   backend/.env.render. The dashboard import is *additive* — it adds/updates
#   matching keys and leaves the rest alone.
#
# Frontend path uses the Vercel CLI directly (per-key add/remove is safe there).
#
# Before running: make sure the source files contain PRODUCTION values.
# Localhost URLs, Sentry environment=development, and `your_*_here`-style
# placeholders are filtered out automatically.
#
# Usage:
#   scripts/push-env.sh backend         # produce backend/.env.render
#   scripts/push-env.sh frontend        # push frontend/.env.local to Vercel
#   scripts/push-env.sh both            # both
#   scripts/push-env.sh --dry-run both  # preview only
#
# Override sources (absolute or repo-relative paths):
#   BACKEND_ENV_FILE=backend/.env.production scripts/push-env.sh backend
#   FRONTEND_ENV_FILE=frontend/.env.production scripts/push-env.sh frontend
#
# Prereqs:
#   - Backend: nothing (script just writes a file).
#   - Frontend: Vercel CLI installed (`npm i -g vercel`) + `vercel login`,
#     and frontend linked to a Vercel project (`cd frontend && vercel link`).

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)

VERCEL_ENVS=(production preview)

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi
MODE=${1:-both}

# Bulletproof dotenv parser: handles quotes, inline comments, `export` prefix.
# Emits one line per var as `KEY<TAB>VALUE`.
parse_env() {
  local file="$1"
  [[ -f "$file" ]] || { echo "✗ missing file: $file" >&2; exit 1; }
  python3 - "$file" <<'PY'
import re, sys
with open(sys.argv[1]) as f:
    for raw in f:
        line = raw.rstrip("\n")
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2)
        # strip inline comments only if unquoted
        if v and v[0] not in "\"'":
            v = v.split("#", 1)[0].rstrip()
        # strip matching outer quotes
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        sys.stdout.write(f"{k}\t{v}\n")
PY
}

should_skip() {
  local k="$1" v="$2"
  # localhost URLs never belong in prod
  if [[ "$v" == http://localhost* || "$v" == http://127.0.0.1* ]]; then
    echo "localhost"; return 0
  fi
  # Don't push the dev Sentry environment name
  if [[ "$k" == "SENTRY_ENVIRONMENT" && "$v" == "development" ]]; then
    echo "would set SENTRY_ENVIRONMENT=development"; return 0
  fi
  # Comments-as-values (placeholder values from .env.example)
  if [[ "$v" =~ ^your_.*_(here|key|secret|id)$ ]]; then
    echo "placeholder value"; return 0
  fi
  return 1
}

# Quote a value for .env file output: double-quote if it contains whitespace,
# `#`, `=`, or any char that the Render parser is picky about; escape inner
# double-quotes and backslashes.
env_quote() {
  local v="$1"
  if [[ "$v" =~ [[:space:]\#=] ]] || [[ -z "$v" ]]; then
    # escape backslashes and double-quotes
    v=${v//\\/\\\\}
    v=${v//\"/\\\"}
    printf '"%s"' "$v"
  else
    printf '%s' "$v"
  fi
}

push_backend() {
  local file="${BACKEND_ENV_FILE:-$ROOT/backend/.env}"
  local out="$ROOT/backend/.env.render"
  echo
  echo "== Backend → Render =="
  echo "Source: $file"
  echo "Target: $out  (drop this into the Render dashboard)"

  local skipped=()
  local count=0
  local tmp; tmp=$(mktemp)
  while IFS=$'\t' read -r k v; do
    if reason=$(should_skip "$k" "$v"); then
      skipped+=("$k ($reason)")
      continue
    fi
    printf '%s=%s\n' "$k" "$(env_quote "$v")" >> "$tmp"
    count=$((count + 1))
  done < <(parse_env "$file")

  if (( ${#skipped[@]} )); then
    echo "Skipped:"
    printf '  - %s\n' "${skipped[@]}"
  fi

  echo "Wrote $count variables."

  if (( DRY_RUN )); then
    echo "(dry-run — preview, not writing $out)"
    echo "--- preview ---"
    cat "$tmp"
    echo "--- end preview ---"
    rm -f "$tmp"
    return
  fi

  mv "$tmp" "$out"
  chmod 600 "$out"

  cat <<EOF

Next: open the Render dashboard for this service:
  Render Dashboard → prism-agents-api → Environment
    → "Add from .env file" → upload $out
    → Save (Render will redeploy)

The dashboard import is additive: existing vars not in the file stay put.
EOF
}

push_frontend() {
  local file="${FRONTEND_ENV_FILE:-$ROOT/frontend/.env.local}"
  echo
  echo "== Frontend → Vercel =="
  echo "Source: $file"

  command -v vercel >/dev/null || { echo "✗ vercel CLI missing (npm i -g vercel)"; exit 1; }
  [[ -d "$ROOT/frontend/.vercel" ]] || {
    echo "✗ frontend not linked. Run: cd frontend && vercel link"; exit 1;
  }

  local pairs=() skipped=()
  while IFS=$'\t' read -r k v; do
    if reason=$(should_skip "$k" "$v"); then
      skipped+=("$k ($reason)")
      continue
    fi
    pairs+=("$k=$v")
  done < <(parse_env "$file")

  if (( ${#skipped[@]} )); then
    echo "Skipped:"
    printf '  - %s\n' "${skipped[@]}"
  fi

  echo "Setting ${#pairs[@]} variables on: ${VERCEL_ENVS[*]}"
  printf '  %s\n' "${pairs[@]%%=*}"

  if (( DRY_RUN )); then
    echo "(dry-run — not pushing)"
    return
  fi

  pushd "$ROOT/frontend" >/dev/null
  for pair in "${pairs[@]}"; do
    local k="${pair%%=*}" v="${pair#*=}"
    for env in "${VERCEL_ENVS[@]}"; do
      # Remove existing so add is idempotent; swallow "not found" errors.
      vercel env rm "$k" "$env" --yes >/dev/null 2>&1 || true
      printf '%s' "$v" | vercel env add "$k" "$env" >/dev/null
      echo "  ✓ $k ($env)"
    done
  done
  popd >/dev/null
}

case "$MODE" in
  backend)  push_backend ;;
  frontend) push_frontend ;;
  both)     push_backend; push_frontend ;;
  *) echo "Usage: $0 [--dry-run] [backend|frontend|both]" >&2; exit 1 ;;
esac

echo
echo "Done."
