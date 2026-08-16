"""
vault_git_routes.py

Chiron addition: git status/commit/push for the configured Obsidian vault
roots (VAULT_ROOTS), surfaced in the UI so a stale/uncommitted vault (or a
stale Docker image — see the "built" timestamp in /api/build-info) is
visible at a glance instead of discovered by accident.

Only operates on paths inside VAULT_ROOTS — never an arbitrary client-
supplied path — since these endpoints shell out to `git` on the host
filesystem.
"""

import asyncio
import logging
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.middleware import require_admin
from src.constants import VAULT_ROOTS

logger = logging.getLogger(__name__)


def _resolve_root(name: str) -> str:
    """Map a vault root's basename (e.g. 'pytheas') back to its full path,
    restricted to VAULT_ROOTS — refuses anything not in that configured list."""
    for root in VAULT_ROOTS:
        if os.path.basename(root.rstrip("/")) == name:
            return root
    raise HTTPException(status_code=404, detail=f"Unknown vault root: {name}")


async def _git(root: str, *args: str) -> tuple:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", root, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return "", "git not installed in this container", 127
    stdout, stderr = await proc.communicate()
    return stdout.decode(errors="replace").strip(), stderr.decode(errors="replace").strip(), proc.returncode


async def _vault_status(root: str) -> dict:
    name = os.path.basename(root.rstrip("/"))
    is_repo, _, rc = await _git(root, "rev-parse", "--is-inside-work-tree")
    if rc != 0 or is_repo != "true":
        return {"name": name, "path": root, "is_repo": False}

    branch, _, _ = await _git(root, "branch", "--show-current")
    porcelain, _, _ = await _git(root, "status", "--porcelain")
    dirty_files = [l for l in porcelain.splitlines() if l.strip()]

    ahead = behind = 0
    counts, _, rc2 = await _git(root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    has_upstream = rc2 == 0
    if has_upstream and counts:
        parts = counts.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    last_log, _, _ = await _git(root, "log", "-1", "--format=%H|%cI|%s")
    last_hash = last_date = last_msg = ""
    if last_log:
        pieces = last_log.split("|", 2)
        if len(pieces) == 3:
            last_hash, last_date, last_msg = pieces

    return {
        "name": name,
        "path": root,
        "is_repo": True,
        "branch": branch,
        "dirty": len(dirty_files) > 0,
        "dirty_count": len(dirty_files),
        "has_upstream": has_upstream,
        "ahead": ahead,
        "behind": behind,
        "last_commit_hash": last_hash[:10],
        "last_commit_date": last_date,
        "last_commit_message": last_msg,
    }


class CommitRequest(BaseModel):
    message: str


def setup_vault_git_routes():
    router = APIRouter(prefix="/api/vault-git", tags=["vault-git"])

    @router.get("/status")
    async def status(request: Request):
        """Git status for every configured Obsidian vault root."""
        require_admin(request)
        results = await asyncio.gather(*(_vault_status(r) for r in VAULT_ROOTS))
        return {"vaults": list(results)}

    @router.post("/{name}/commit")
    async def commit(name: str, req: CommitRequest, request: Request):
        """Stage all changes and commit in the named vault root."""
        require_admin(request)
        root = _resolve_root(name)
        message = req.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Commit message required")

        _, stderr, rc = await _git(root, "add", "-A")
        if rc != 0:
            return {"ok": False, "error": f"git add failed: {stderr[:300]}"}

        porcelain, _, _ = await _git(root, "status", "--porcelain", "--cached")
        if not porcelain.strip():
            return {"ok": False, "error": "Nothing staged to commit"}

        _, stderr, rc = await _git(root, "commit", "-m", message)
        if rc != 0:
            return {"ok": False, "error": f"git commit failed: {stderr[:300]}"}
        return {"ok": True}

    @router.post("/{name}/push")
    async def push(name: str, request: Request):
        """Push the named vault root to its configured upstream."""
        require_admin(request)
        root = _resolve_root(name)
        _, stderr, rc = await _git(root, "push")
        if rc != 0:
            return {"ok": False, "error": f"git push failed: {stderr[:300]}"}
        return {"ok": True}

    return router
