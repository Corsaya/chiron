"""
sat_drill_routes.py

Chiron addition: export endpoint for the SAT Adaptive Drill classroom app.

Takes the drill session held in the browser (localStorage, same as the test
runner) plus every question asked of the Classroom tutor since the last export,
and writes them into one markdown review document in the pytheas vault — the
doc Donovan opens before walking into the test.
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.auth_helpers import require_user
from src.sat_study_log import clear_entries, read_entries

logger = logging.getLogger(__name__)

# The pytheas vault is mounted read-only (see docker-compose.yml); this is a
# separate narrow read-write mount of just Courses/SAT/Review, so the export
# can write without opening up the rest of the vault.
REVIEW_DIR = os.getenv("CHIRON_SAT_REVIEW_DIR", "/app/vaults/pytheas-review")

LEVEL_NAMES = {
    1: "stretch",
    0: "SAT level",
    -1: "simplified",
    -2: "foundations",
}


class DrillLogEntry(BaseModel):
    domain: str = ""
    skillId: str = ""
    skillName: str = ""
    level: int = 0
    prompt: str = ""
    picked: str = ""
    correctAnswer: str = ""
    correct: bool = False
    usedHint: bool = False


class ExportRequest(BaseModel):
    log: List[DrillLogEntry] = []
    mastery: Dict[str, str] = {}


def _short(text: str, limit: int = 240) -> str:
    """Collapse a question prompt to one scannable line."""
    flat = re.sub(r"\s+", " ", (text or "").strip())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _build_doc(req: ExportRequest, tutor: List[Dict[str, Any]], today: str) -> str:
    missed = [e for e in req.log if not e.correct]
    hinted = [e for e in req.log if e.correct and e.usedHint]
    answered = len(req.log)
    right = answered - len(missed)

    gaps = sorted(k for k, v in req.mastery.items() if v == "gap")
    shaky = sorted(k for k, v in req.mastery.items() if v == "shaky")

    out: List[str] = []
    out.append("---")
    out.append("tags: [pytheas, sat, review, drill, pre-test]")
    out.append(f"created: {today}")
    out.append('source: "Chiron SAT Adaptive Drill + Classroom tutor"')
    out.append('related: ["[[../Crash Courses/R&W — SAT Grammar Rules Reference]]", '
               '"[[../SAT Master Guide — Score Higher (2026-08-12)]]"]')
    out.append("---")
    out.append("")
    out.append(f"# Pre-Test Review — {today}")
    out.append("")
    out.append("Auto-generated from a drill session. **Read the Weak spots and Missed "
               "questions sections first** — everything below them is reference.")
    out.append("")

    # --- the part that matters most, first ---
    out.append("## Weak spots this session")
    out.append("")
    if not gaps and not shaky:
        out.append("_No skill bottomed out — nothing flagged._")
    else:
        if gaps:
            out.append("**Bottomed out** (missed even the foundations rung — these are real gaps):")
            out.append("")
            for k in gaps:
                out.append(f"- {k.split(':', 1)[-1]}")
            out.append("")
        if shaky:
            out.append("**Recovered after dropping a rung** (knows it, but not reliably under pressure):")
            out.append("")
            for k in shaky:
                out.append(f"- {k.split(':', 1)[-1]}")
    out.append("")

    out.append("## Missed questions")
    out.append("")
    if not missed:
        out.append("_Nothing missed._")
    else:
        for e in missed:
            lvl = LEVEL_NAMES.get(e.level, f"level {e.level}")
            out.append(f"### {e.skillId} — {e.skillName}  <sub>({lvl})</sub>")
            out.append("")
            out.append(f"> {_short(e.prompt, 600)}")
            out.append("")
            out.append(f"- You picked: **{_short(e.picked, 160)}**")
            out.append(f"- Correct: **{_short(e.correctAnswer, 160)}**")
            out.append("")
    out.append("")

    if hinted:
        out.append("## Got it, but needed a hint")
        out.append("")
        for e in hinted:
            out.append(f"- **{e.skillId}** {e.skillName} — {_short(e.prompt, 180)}")
        out.append("")

    # --- tutor questions ---
    out.append("## Questions you asked the tutor")
    out.append("")
    if not tutor:
        out.append("_No tutor questions recorded this session._")
    else:
        for i, t in enumerate(tutor, 1):
            lesson = t.get("lesson_title") or ""
            head = f"### {i}. {_short(t.get('question', ''), 200)}"
            out.append(head)
            if lesson:
                out.append("")
                out.append(f"<sub>asked while reading: {lesson}</sub>")
            out.append("")
            answer = (t.get("answer") or "").strip()
            out.append(answer if answer else "_(no answer recorded — the tutor errored or was interrupted)_")
            out.append("")

    out.append("---")
    out.append("")
    out.append(f"_Session totals: {right}/{answered} correct across all ladder levels. "
               "Sub-level-0 rungs are scaffolding, not SAT-difficulty questions — "
               "don't read this percentage as a score estimate._")
    out.append("")
    return "\n".join(out)


def setup_sat_drill_routes() -> APIRouter:
    router = APIRouter(prefix="/api/sat-drill", tags=["sat-drill"])

    @router.post("/export")
    async def export_review(req: ExportRequest, owner: str = Depends(require_user)):
        tutor = read_entries()
        if not req.log and not tutor:
            raise HTTPException(400, "Nothing to export yet — answer some drill questions first.")

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            os.makedirs(REVIEW_DIR, exist_ok=True)
        except OSError as e:
            raise HTTPException(500, f"Cannot create review folder: {e}")

        # One doc per day, overwritten on re-export so repeated exports during a
        # single study day don't litter the folder.
        filename = f"Pre-Test Review — {today}.md"
        path = os.path.join(REVIEW_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(_build_doc(req, tutor, today))
        except OSError as e:
            raise HTTPException(500, f"Cannot write review doc: {e}")

        cleared = clear_entries()
        logger.info(f"SAT review doc written to {path} ({cleared} tutor questions folded in)")
        return {
            "ok": True,
            "path": f"Courses/SAT/Review/{filename}",
            "drill_questions": len(req.log),
            "tutor_questions": cleared,
        }

    return router
