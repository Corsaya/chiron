"""Read an existing SAT course plan. No store, scoring model, or vault execution."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re


class CourseSourceError(ValueError):
    """A source cannot be safely presented."""


def read_source(root: Path, relative: str) -> dict:
    """Confine reads to visible Markdown files; never follow symlinks."""
    root = root.resolve()
    relative_path = Path(relative)
    if relative_path.is_absolute() or any(
        part in ("..", "locked") or part.startswith(".")
        for part in relative_path.parts
    ):
        raise CourseSourceError("Source path is not allowed")
    current = root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise CourseSourceError("Linked source paths are not allowed")
    if current.suffix.lower() != ".md" or not current.is_file():
        raise CourseSourceError("Source note is unavailable")
    # Bound source size before decoding; no attachment or executable imports.
    with current.open("rb") as handle:
        raw = handle.read(1_000_001)
        if len(raw) > 1_000_000:
            raise CourseSourceError("Source note is too large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CourseSourceError("Source note is not UTF-8") from exc
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if frontmatter and re.search(
        r"(?im)^\s*(?:privacy\s*:\s*['\"]?locked|locked\s*:\s*(?:true|yes|1))\b",
        frontmatter[1],
    ):
        raise CourseSourceError("Source is locked")
    return {
        "path": relative_path.as_posix(),
        "content": text,
        "revision": sha256(raw).hexdigest(),
        "modified_at": datetime.fromtimestamp(
            current.stat().st_mtime, timezone.utc
        ).isoformat(),
    }


def pdf_source_path(root: Path, relative: str) -> Path:
    """Locate a course PDF without allowing linked or escaping paths."""
    root = root.resolve()
    relative_path = Path(relative)
    if (relative_path.is_absolute() or not relative_path.parts or relative_path.parts[0] != "Questions" or any(
        part in ("..", "locked") or part.startswith(".")
        for part in relative_path.parts
    )):
        raise CourseSourceError("PDF path is not allowed")
    current = root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise CourseSourceError("Linked PDF paths are not allowed")
    if current.suffix.lower() != ".pdf" or not current.is_file():
        raise CourseSourceError("PDF is unavailable")
    if current.stat().st_size > 30_000_000:
        raise CourseSourceError("PDF is too large")
    return current


def section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    captured = []
    active = False
    fenced = False
    for line in lines:
        if line.startswith(("```", "~~~")):
            fenced = not fenced
        if not fenced and re.match(r"^#{1,2} ", line):
            if active:
                break
            active = line.strip() == f"## {heading}"
            continue
        if active:
            captured.append(line)
    return "\n".join(captured).strip() or None


def course_plan(root: Path) -> dict:
    source = read_source(root, "Home.md")
    action = section(source["content"], "Next action")
    evidence = section(source["content"], "Evidence we actually have")
    references = []
    seen = {"Home.md"}
    for target, label in re.findall(
        r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", "\n".join(filter(None, [action, evidence]))
    ):
        target = target.split("#", 1)[0]
        if not target.startswith("Courses/SAT/"):
            continue
        path = target.removeprefix("Courses/SAT/")
        if not path.endswith(".md"):
            path += ".md"
        if path in seen:
            continue
        seen.add(path)
        try:
            note = read_source(root, path)
        except CourseSourceError:
            continue
        references.append({
            "path": note["path"], "title": label or Path(path).stem,
            "revision": note["revision"], "modified_at": note["modified_at"],
        })
    return {
        "kind": "authored_plan", "action": action, "evidence": evidence,
        "source": {key: value for key, value in source.items() if key != "content"},
        "references": references,
        "limitations": "This is the recorded course plan, not a live assessment. "
        "Source dates and claims have not been independently reverified. "
        "Opening a note does not establish practice or mastery.",
    }
