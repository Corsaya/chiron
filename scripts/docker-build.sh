#!/usr/bin/env bash
# Chiron addition: writes BUILD_INFO.json (current git commit/date/branch)
# before building, then runs the normal docker compose build. Built after
# a stale-image bug (2026-08-16) where a commit landed 2 minutes after a
# plain `docker compose build`, and the running container silently kept
# serving the old code with no way to detect it from the UI. Use this
# instead of a bare `docker compose build` so the image always carries an
# accurate build fingerprint, readable via /api/build-info.
set -euo pipefail
cd "$(dirname "$0")/.."

cat > BUILD_INFO.json <<EOF
{
  "commit": "$(git rev-parse HEAD)",
  "short_commit": "$(git rev-parse --short HEAD)",
  "branch": "$(git branch --show-current)",
  "commit_date": "$(git log -1 --format=%cI)",
  "commit_subject": "$(git log -1 --format=%s | sed 's/"/\\"/g')",
  "built_at": "$(date -u +%FT%TZ)",
  "dirty": $( [ -z "$(git status --porcelain)" ] && echo false || echo true )
}
EOF

echo "Wrote BUILD_INFO.json:"
cat BUILD_INFO.json
echo

docker compose build "$@"
