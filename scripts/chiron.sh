#!/usr/bin/env bash
# Start this checkout's Compose stack from any working directory.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1; then
    printf 'Docker and Docker Compose are required to start Chiron.\n' >&2
    exit 1
fi

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_command=(sudo docker)
fi

case "${1:-start}" in
    start) "${docker_command[@]}" compose up -d --build ;;
    stop) "${docker_command[@]}" compose stop ;;
    logs) "${docker_command[@]}" compose logs -f odysseus ;;
    status) "${docker_command[@]}" compose ps ;;
    *) printf 'Usage: chiron [start|stop|logs|status]\n' >&2; exit 2 ;;
esac
