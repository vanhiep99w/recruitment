#!/usr/bin/env bash
# wait-for.sh — waits until both Postgres and Redis are ready before exiting 0
# Usage: ./scripts/wait-for.sh [max_attempts]

set -euo pipefail

MAX_ATTEMPTS="${1:-60}"
SLEEP_SECONDS=2

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "[wait-for] Waiting for Postgres (${POSTGRES_HOST}:${POSTGRES_PORT}) and Redis (${REDIS_HOST}:${REDIS_PORT})..."

attempt=0
postgres_ready=false
redis_ready=false

until [[ "$postgres_ready" == "true" && "$redis_ready" == "true" ]]; do
    attempt=$((attempt + 1))
    if [[ $attempt -gt $MAX_ATTEMPTS ]]; then
        echo "[wait-for] ERROR: timed out after ${MAX_ATTEMPTS} attempts." >&2
        exit 1
    fi

    # Check Postgres
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -q 2>/dev/null; then
        if [[ "$postgres_ready" != "true" ]]; then
            echo "[wait-for] Postgres is ready."
        fi
        postgres_ready=true
    else
        echo "[wait-for] Attempt ${attempt}/${MAX_ATTEMPTS}: Postgres not ready, retrying in ${SLEEP_SECONDS}s..."
    fi

    # Check Redis
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" PING 2>/dev/null | grep -q PONG; then
        if [[ "$redis_ready" != "true" ]]; then
            echo "[wait-for] Redis is ready."
        fi
        redis_ready=true
    else
        echo "[wait-for] Attempt ${attempt}/${MAX_ATTEMPTS}: Redis not ready, retrying in ${SLEEP_SECONDS}s..."
    fi

    if [[ "$postgres_ready" != "true" || "$redis_ready" != "true" ]]; then
        sleep "$SLEEP_SECONDS"
    fi
done

echo "[wait-for] Both Postgres and Redis are available. Proceeding."
exit 0
