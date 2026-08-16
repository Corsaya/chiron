"""
build_info_routes.py

Chiron addition: exposes what commit/version is actually running in this
container. Built to catch exactly the bug hit on 2026-08-16 — a Docker
image built 2 minutes before a commit landed, silently serving stale code
with no way to tell from the UI. See scripts/docker-build.sh, which writes
BUILD_INFO.json into the image at build time; this route just reads it back.
"""

import json
import os

from fastapi import APIRouter

from src.constants import BASE_DIR, APP_VERSION

BUILD_INFO_PATH = os.path.join(BASE_DIR, "BUILD_INFO.json")


def setup_build_info_routes():
    router = APIRouter(tags=["build-info"])

    @router.get("/api/build-info")
    async def build_info():
        if os.path.isfile(BUILD_INFO_PATH):
            try:
                with open(BUILD_INFO_PATH, "r", encoding="utf-8") as f:
                    info = json.load(f)
                info.setdefault("app_version", APP_VERSION)
                return info
            except Exception:
                pass
        return {
            "app_version": APP_VERSION,
            "commit": "unknown",
            "note": "No BUILD_INFO.json baked in — image was built without scripts/docker-build.sh",
        }

    return router
