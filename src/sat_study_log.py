"""
sat_study_log.py

Chiron addition: a flat append-only record of every question Donovan asks the
Classroom tutor, so that at the end of a study session it can be folded into a
single review document in the vault.

Deliberately a JSON file rather than a DB table — this is study scratch data
with a lifetime of days, it needs to survive a container restart but nothing
more, and it matches how auth.json is already handled in this codebase.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.constants import DATA_DIR

logger = logging.getLogger(__name__)

LOG_PATH = os.path.join(DATA_DIR, "sat_study_log.json")

# Answers can be long; the review doc wants the substance, not a transcript.
MAX_ANSWER_CHARS = 4000
# Keep the file from growing without bound across many sessions.
MAX_ENTRIES = 500

_lock = threading.Lock()


def _read_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"sat_study_log unreadable, starting fresh: {e}")
        return []


def read_entries() -> List[Dict[str, Any]]:
    with _lock:
        return _read_unlocked()


def record_question(question: str, answer: str = "", lesson_title: str = "") -> None:
    """Append one tutor exchange. Never raises — a logging failure must not
    take down the tutor response the student is actually waiting on."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "question": (question or "").strip(),
            "answer": (answer or "").strip()[:MAX_ANSWER_CHARS],
            "lesson_title": lesson_title or "",
        }
        with _lock:
            entries = _read_unlocked()
            entries.append(entry)
            if len(entries) > MAX_ENTRIES:
                entries = entries[-MAX_ENTRIES:]
            tmp = LOG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
            os.replace(tmp, LOG_PATH)
    except Exception as e:  # noqa: BLE001 - best-effort logging only
        logger.warning(f"failed to record SAT tutor question: {e}")


def clear_entries() -> int:
    """Drop the log after it has been exported. Returns how many were cleared."""
    with _lock:
        n = len(_read_unlocked())
        try:
            if os.path.exists(LOG_PATH):
                os.remove(LOG_PATH)
        except OSError as e:
            logger.warning(f"failed to clear SAT study log: {e}")
            return 0
        return n
