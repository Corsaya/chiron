"""Build the read-only SAT Classroom question locator from the six source PDFs.

Usage: python scripts/build_sat_question_index.py /path/to/Courses/SAT
Requires pdftotext (Poppler). Stores locations and skill labels, never answers.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def build(root: Path) -> dict:
    questions = root / "Questions"
    entries = []
    sources = []
    pdfs = sorted(questions.glob("*/*.pdf"))
    if len(pdfs) != 6:
        raise ValueError(f"Expected six SAT source PDFs; found {len(pdfs)}")
    for pdf in pdfs:
        raw = subprocess.check_output(["pdftotext", "-raw", str(pdf), "-"])
        pages = raw.decode("utf-8", errors="replace").split("\f")
        count = 0
        for page_number, page in enumerate(pages, 1):
            match = re.search(r"Question ID ([0-9a-f]{8})", page)
            if not match:
                continue
            skill = re.search(r"(?m)^Skill\s*\n(.*?)\nDi(?:ﬃ|ffi)culty", page, re.S)
            if not skill:
                raise ValueError(f"Missing skill: {pdf.name} page {page_number}")
            entries.append({
                "id": match.group(1),
                "path": pdf.relative_to(root).as_posix(),
                "page": page_number,
                "domain": pdf.parent.name,
                "skill": " ".join(skill.group(1).split()),
            })
            count += 1
        sources.append({"path": pdf.relative_to(root).as_posix(), "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "entries": count})
    if len(entries) != 600:
        raise ValueError(f"Expected 600 question entries; found {len(entries)}")
    return {"kind": "sat_question_locator_v1", "owner": "SAT course", "lifecycle": "derived reference", "privacy": "private", "review_after": "2026-10-03", "sources": sources, "questions": entries}


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    output = root / "Questions" / "question-index.json"
    output.write_text(json.dumps(build(root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed 600 entries into {output}")
