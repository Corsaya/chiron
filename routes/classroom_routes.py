# routes/classroom_routes.py
"""Chiron addition: Google-Classroom-style view over the configured Courses/
folder. Folder-convention only (no manual registry, per Donovan's call
2026-08-09) — a subfolder of COURSES_ROOT is a classroom, files inside it
are assignments/materials, subfolders are sections.

A small hardcoded table (CUSTOM_APPS below) maps specific known files to a
richer interactive UI shipped under static/classroom-apps/, instead of the
default read-only markdown render — e.g. the SAT diagnostic test opens the
actual Bluebook-style runner, not its source markdown.
"""
import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends
from src.auth_helpers import require_user

logger = logging.getLogger(__name__)

# Defaults to the Learning vault after the 2026-08-27 ownership cleanup. Keep
# this configurable so a future vault move does not require a source edit.
COURSES_ROOT = os.getenv("CHIRON_COURSES_ROOT", "/app/vaults/learning/Courses")

_SKIP_DIRS = {".obsidian", ".git", ".trash", "_artifacts"}

# filename (case-insensitive substring match) -> static app entry point.
# Extend this table as more interactive tools get built.
# Emptied 2026-08-20: the SAT test/drill apps were removed — official Bluebook and the
# College Board Question Bank are the only SAT question sources now.
CUSTOM_APPS: dict[str, str] = {}


def _custom_app_for(filename: str) -> str | None:
    lower = filename.lower()
    for key, url in CUSTOM_APPS.items():
        if key in lower:
            return url
    return None


def _list_materials(dir_path: str, rel_prefix: str = "") -> List[Dict[str, Any]]:
    materials = []
    try:
        entries = sorted(os.scandir(dir_path), key=lambda e: e.name.lower())
    except OSError:
        return materials
    for entry in entries:
        if entry.name in _SKIP_DIRS or entry.name.startswith("."):
            continue
        rel = os.path.join(rel_prefix, entry.name)
        if entry.is_dir():
            materials.append({
                "type": "section",
                "name": entry.name,
                "path": rel,
                "items": _list_materials(entry.path, rel),
            })
        elif entry.name.endswith(".md"):
            custom_app = _custom_app_for(entry.name)
            materials.append({
                "type": "custom_app" if custom_app else "note",
                "name": entry.name[:-3],
                "path": rel,
                "app_url": custom_app,
            })
    return materials


def setup_classroom_routes() -> APIRouter:
    router = APIRouter(prefix="/api/classrooms")

    @router.get("")
    def list_classrooms(owner: str = Depends(require_user)):
        if not os.path.isdir(COURSES_ROOT):
            return {"classrooms": []}
        classrooms = []
        for entry in sorted(os.scandir(COURSES_ROOT), key=lambda e: e.name.lower()):
            if not entry.is_dir() or entry.name in _SKIP_DIRS or entry.name.startswith("."):
                continue
            classrooms.append({"name": entry.name, "path": entry.name})
        return {"classrooms": classrooms}

    @router.get("/{classroom_name}")
    def get_classroom(classroom_name: str, owner: str = Depends(require_user)):
        classroom_dir = os.path.realpath(os.path.join(COURSES_ROOT, classroom_name))
        courses_root_abs = os.path.realpath(COURSES_ROOT)
        if os.path.commonpath([classroom_dir, courses_root_abs]) != courses_root_abs:
            raise HTTPException(403, "Invalid classroom path")
        if not os.path.isdir(classroom_dir):
            raise HTTPException(404, "Classroom not found")
        return {
            "name": classroom_name,
            "materials": _list_materials(classroom_dir),
        }

    @router.get("/{classroom_name}/note")
    def get_note(classroom_name: str, path: str, owner: str = Depends(require_user)):
        classroom_dir = os.path.realpath(os.path.join(COURSES_ROOT, classroom_name))
        courses_root_abs = os.path.realpath(COURSES_ROOT)
        if os.path.commonpath([classroom_dir, courses_root_abs]) != courses_root_abs:
            raise HTTPException(403, "Invalid classroom path")
        note_path = os.path.realpath(os.path.join(classroom_dir, path))
        if os.path.commonpath([note_path, classroom_dir]) != classroom_dir:
            raise HTTPException(403, "Invalid note path")
        if not os.path.isfile(note_path):
            raise HTTPException(404, "Note not found")
        with open(note_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}

    return router
