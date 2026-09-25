#!/usr/bin/env bash
# Start this checkout's Compose stack from any working directory.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1; then
    printf 'Docker and Docker Compose are required to start Chiron.\n' >&2
    exit 1
fi

# Prefer the reorganized vault, while recognizing the older and nested
# checkouts. Explicit CHIRON_LEARNING_DIR in the shell or .env wins.
obsidian_dir="${OBSIDIAN_DIR:-/home/donovan/Documents/Obsidian}"
if [[ -z "${OBSIDIAN_DIR:-}" ]] && [[ -f .env ]]; then
    dotenv_obsidian=$(sed -n 's/^OBSIDIAN_DIR=//p' .env | tail -n 1)
    [[ -z "$dotenv_obsidian" ]] || obsidian_dir="${dotenv_obsidian%\"}"
    obsidian_dir="${obsidian_dir#\"}"
fi
if [[ -z "${CHIRON_LEARNING_DIR:-}" ]] && ! grep -q '^CHIRON_LEARNING_DIR=' .env 2>/dev/null; then
    for candidate in \
        "$obsidian_dir/obsidian-vault/learning" \
        "$obsidian_dir/learning-vault" \
        "$obsidian_dir/learning"; do
        if [[ -d "$candidate/Courses/SAT" ]]; then
            export CHIRON_LEARNING_DIR="$candidate"
            break
        fi
    done
    if [[ -z "${CHIRON_LEARNING_DIR:-}" ]] && [[ -d "$obsidian_dir" ]]; then
        sat_dir=$(find "$obsidian_dir" -maxdepth 6 -type d -path '*/Courses/SAT' -print -quit 2>/dev/null || true)
        [[ -z "$sat_dir" ]] || export CHIRON_LEARNING_DIR="$(dirname "$(dirname "$sat_dir")")"
    fi
fi

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    # sudo otherwise strips the detected override and Compose mounts the
    # legacy vault even though a valid SAT course was found above.
    compose_env=()
    [[ -z "${CHIRON_LEARNING_DIR:-}" ]] || compose_env+=("CHIRON_LEARNING_DIR=$CHIRON_LEARNING_DIR")
    [[ -z "${OBSIDIAN_DIR:-}" ]] || compose_env+=("OBSIDIAN_DIR=$OBSIDIAN_DIR")
    docker_command=(sudo env "${compose_env[@]}" docker)
fi

check_sat_mount() {
    local source
    source=$("${docker_command[@]}" compose config --format json | python3 -c '
import json,sys
config=json.load(sys.stdin)
volumes=config["services"]["odysseus"]["volumes"]
print(next((v["source"] for v in volumes if v.get("target")=="/app/vaults/learning"), ""))
') || return 1
    if [[ ! -d "$source/Courses/SAT" ]]; then
        printf 'SAT course not found in the selected learning vault: %s\n' "$source" >&2
        printf 'Set CHIRON_LEARNING_DIR in .env to the absolute parent of Courses, then run chiron again.\n' >&2
        return 1
    fi
    printf 'SAT course mount: %s/Courses/SAT\n' "$source"
}

case "${1:-start}" in
    start) check_sat_mount && "${docker_command[@]}" compose up -d --build ;;
    stop) "${docker_command[@]}" compose stop ;;
    logs) "${docker_command[@]}" compose logs -f odysseus ;;
    status) "${docker_command[@]}" compose ps ;;
    *) printf 'Usage: chiron [start|stop|logs|status]\n' >&2; exit 2 ;;
esac
