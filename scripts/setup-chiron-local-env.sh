#!/usr/bin/env bash
# Configure this checkout's SAT Classroom on the machine holding the vault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

vault_root="${OBSIDIAN_DIR:-/home/donovan/Documents/Obsidian}"
if [[ -n "${CHIRON_LEARNING_DIR:-}" ]]; then
    learning_dir="$CHIRON_LEARNING_DIR"
else
    learning_dir=""
    for candidate in \
        "$vault_root/obsidian-vault/learning" \
        "$vault_root/learning-vault" \
        "$vault_root/learning"; do
        if [[ -d "$candidate/Courses/SAT" ]]; then
            learning_dir="$candidate"
            break
        fi
    done
    if [[ -z "$learning_dir" ]] && [[ -d "$vault_root" ]]; then
        sat_dir=$(find "$vault_root" -maxdepth 6 -type d -path '*/Courses/SAT' -print -quit 2>/dev/null || true)
        [[ -z "$sat_dir" ]] || learning_dir="$(dirname "$(dirname "$sat_dir")")"
    fi
fi

if [[ -z "$learning_dir" ]] || [[ ! -d "$learning_dir/Courses/SAT" ]]; then
    printf 'SAT course not found under %s. Run: find "%s" -type d -path "*/Courses/SAT" -print\n' "$vault_root" "$vault_root" >&2
    printf 'Then rerun with CHIRON_LEARNING_DIR set to the absolute parent of Courses.\n' >&2
    exit 1
fi
learning_dir=$(realpath "$learning_dir")
export CHIRON_LEARNING_DIR="$learning_dir"

python3 - "$learning_dir" <<'PY'
from pathlib import Path
import re
import shutil
import sys

path = Path('.env')
source = Path('.env.example')
value = sys.argv[1]
if any(char in value for char in '\n\r"$\\'):
    raise SystemExit('Vault path contains characters unsupported by this setup command; set CHIRON_LEARNING_DIR manually.')
if not path.exists():
    shutil.copyfile(source, path)
    path.chmod(0o600)
text = path.read_text()
line = f'CHIRON_LEARNING_DIR="{value}"'
updated, count = re.subn(r'^CHIRON_LEARNING_DIR=.*$', lambda _: line, text, flags=re.M)
if count == 0:
    updated = text.rstrip('\n') + '\n' + line + '\n'
if updated != text:
    backup = path.with_name('.env.bak.sat-setup')
    shutil.copy2(path, backup)
    backup.chmod(0o600)
    path.write_text(updated)
    path.chmod(0o600)
print(f'SAT learning vault: {value}')
print('Updated .env (existing settings preserved).')
PY

bash scripts/chiron.sh
bash scripts/chiron.sh status
printf 'Open http://localhost:7001/static/classroom.html#/SAT\n'
