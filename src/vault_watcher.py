# src/vault_watcher.py
"""Chiron addition: poll configured Obsidian vault roots for changes and
trigger a personal-docs reindex automatically.

No filesystem-event dependency (watchfiles/watchdog) is installed, and this
only needs to notice "something changed" at a coarse grain, so a cheap mtime
poll is used instead of adding a new dependency for exact-event notification.
"""
import logging
import os
import threading
import time
from typing import Iterable

logger = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 15
_SKIP_DIRS = {".obsidian", ".git", ".trash"}


def _fingerprint(root: str) -> tuple[float, int]:
    """Return (max mtime, file count) for markdown/text files under root."""
    max_mtime = 0.0
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if not name.endswith((".md", ".txt", ".json")):
                continue
            count += 1
            try:
                mtime = os.path.getmtime(os.path.join(dirpath, name))
            except OSError:
                continue
            if mtime > max_mtime:
                max_mtime = mtime
    return max_mtime, count


def start_vault_watcher(
    roots: Iterable[str],
    on_change,
    *,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
) -> threading.Thread:
    """Start a daemon thread polling `roots` for changes; calls `on_change()`
    (no args) when any root's fingerprint changes. Returns the thread."""
    roots = [r for r in roots if os.path.isdir(r)]

    def _loop():
        last = {root: _fingerprint(root) for root in roots}
        logger.info(f"vault_watcher: watching {len(roots)} vault root(s) every {poll_seconds}s")
        while True:
            time.sleep(poll_seconds)
            for root in roots:
                try:
                    current = _fingerprint(root)
                except Exception as e:
                    logger.warning(f"vault_watcher: fingerprint failed for {root}: {e}")
                    continue
                if current != last.get(root):
                    last[root] = current
                    logger.info(f"vault_watcher: change detected under {root}, reindexing")
                    try:
                        on_change()
                    except Exception as e:
                        logger.error(f"vault_watcher: on_change failed: {e}")

    thread = threading.Thread(target=_loop, name="vault-watcher", daemon=True)
    thread.start()
    return thread
