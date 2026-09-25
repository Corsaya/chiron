"""Dated SAT question picks from the current six-PDF course; read-only."""
import csv
import hashlib
import json
from itertools import zip_longest
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

from src.sat_course import CourseSourceError, pdf_source_path

START = date(2026, 9, 24)
END = date(2026, 10, 3)
DOMAINS = ("Algebra", "Advanced Math", "Problem Solving and Data Analysis", "Geometry and Trigonometry")
SCHEDULE = {
    "2026-09-24": ("Mixed starting set", [(DOMAINS[0], "", 3), (DOMAINS[1], "", 4), (DOMAINS[2], "", 2), (DOMAINS[3], "", 3)]),
    "2026-09-25": ("Algebra: systems and solution counts", [(DOMAINS[0], "Systems of two", 10), (DOMAINS[0], "", 8)]),
    "2026-09-26": ("Advanced Math: functions and quadratics", [(DOMAINS[1], "Nonlinear functions", 10), (DOMAINS[1], "Nonlinear equations", 8)]),
    "2026-09-27": ("Official timed practice", []),
    "2026-09-28": ("Advanced Math: expressions and equations", [(DOMAINS[1], "Equivalent expressions", 8), (DOMAINS[1], "", 8)]),
    "2026-09-29": ("Problem Solving and Data Analysis", [(DOMAINS[2], "Percentages", 3), (DOMAINS[2], "Ratios", 3), (DOMAINS[2], "One-variable", 3), (DOMAINS[2], "Two-variable", 3), (DOMAINS[2], "Probability", 2), (DOMAINS[2], "Inference", 2)]),
    "2026-09-30": ("Geometry and Trigonometry", [(DOMAINS[3], "Area and volume", 4), (DOMAINS[3], "Right triangles", 4), (DOMAINS[3], "Lines, angles", 4), (DOMAINS[3], "Circles", 4)]),
    "2026-10-01": ("Two official timed Math modules", []),
    "2026-10-02": ("Light review of logged misses", []),
    "2026-10-03": ("Official SAT", []),
}
INSTRUCTIONS = {
    "2026-09-27": "Take a fresh official Bluebook practice test if available; otherwise use two untouched official timed Math modules. Review before adding PDF questions.",
    "2026-10-01": "Complete two 35-minute unfamiliar official Math modules, then review easy misses, skips, and timing.",
    "2026-10-02": "Review 8–12 varied misses for 30–45 minutes, rehearse calculator and test logistics, then stop early.",
    "2026-10-03": "Take the official SAT. Secure routine items, flag time sinks, and verify the requested value.",
}


def _index(root: Path) -> list[dict]:
    path = root / "Questions" / "question-index.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 300_000:
        raise CourseSourceError("SAT question locator is unavailable")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") != "sat_question_locator_v1" or len(data.get("questions", [])) != 600:
        raise CourseSourceError("SAT question locator is invalid")
    for source in data["sources"]:
        pdf = pdf_source_path(root, source["path"])
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != source["sha256"]:
            raise CourseSourceError("SAT PDFs changed; rebuild the question locator")
    return data["questions"]


def _logged(root: Path) -> tuple[set[str], list[str]]:
    path = root / "Tracking" / "attempts.csv"
    if path.is_symlink() or not path.is_file():
        return set(), []
    attempted = set()
    misses = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            identifier = (row.get("question_id") or "").strip().lower()
            if not identifier:
                continue
            attempted.add(identifier)
            if (row.get("correct") or "").strip().lower() in {"0", "false", "no", "n"}:
                misses.append(identifier)
    return attempted, list(dict.fromkeys(reversed(misses)))


def daily_questions(root: Path, day: str | None = None) -> dict:
    if day is None:
        day = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    try:
        target = date.fromisoformat(day)
    except ValueError as exc:
        raise CourseSourceError("Invalid study date") from exc
    if not START <= target <= END or day != target.isoformat():
        raise CourseSourceError("Study date is outside this SAT plan")
    questions = _index(root)
    attempted, misses = _logged(root)
    used = set()
    selections = {}
    for scheduled_day, (_, groups) in SCHEDULE.items():
        batches = []
        for domain, skill, count in groups:
            candidates = [q for q in questions if q["domain"] == domain and q["skill"].startswith(skill) and (q["path"], q["page"]) not in used]
            if len(candidates) < count:
                raise CourseSourceError("SAT question locator lacks enough questions")
            chosen = candidates[:count]
            batches.append(chosen)
            for question in chosen:
                used.add((question["path"], question["page"]))
        selections[scheduled_day] = [q for row in zip_longest(*batches) for q in row if q] if batches else []
    if day == "2026-10-02":
        by_id = {q["id"]: q for q in questions}
        picks = [by_id[identifier] for identifier in misses if identifier in by_id][:12]
        if not picks:
            # No false claim of past misses: offer a small unfamiliar mixed fallback.
            batches = [[q for q in questions if q["domain"] == domain and (q["path"], q["page"]) not in used][:2] for domain in DOMAINS]
            picks = [q for row in zip_longest(*batches) for q in row if q]
        selections[day] = picks
    picks = [{**q, "logged": q["id"] in attempted} for q in selections[day]]
    return {
        "date": day, "focus": SCHEDULE[day][0], "instruction": INSTRUCTIONS.get(day, "Attempt the questions timed before checking the answers; then review misses and slow items in the existing attempt log."),
        "questions": picks, "short_set": min(4, len(picks)), "source": "Courses/SAT/Questions/question-index.json",
        "dates": list(SCHEDULE), "review_from_log": day == "2026-10-02" and bool(misses),
    }
