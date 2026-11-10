#!/bin/sh
# Apply pending database migrations before starting the backend.
#
# Without this step a fresh Postgres volume has no schema and every event query
# fails with `relation "events" does not exist`. Alembic is idempotent, so this
# is a no-op once the database is at head.
set -eu

echo "Applying database migrations..."
attempt=1
until alembic upgrade head; do
    if [ "$attempt" -ge 10 ]; then
        echo "Migrations failed after $attempt attempts" >&2
        exit 1
    fi
    echo "Migration attempt $attempt failed; retrying in 2s..." >&2
    attempt=$((attempt + 1))
    sleep 2
done

exec "$@"
