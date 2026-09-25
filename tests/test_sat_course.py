"""Synthetic, read-only SAT adapter and actual Classroom route contracts."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import classroom_routes
from src.sat_course import CourseSourceError, course_plan, pdf_source_path, read_source


HOME = """---
privacy: private
---
# SAT
## Next action
Try [[Courses/SAT/Current/Practice|a five-question practice block]].
## Evidence we actually have
Two observed errors are recorded in [[Courses/SAT/Current/Review|the review]].
These observations do not establish a persistent weakness.
## Other
Do not include this section.
"""


class SatCourseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.courses = Path(self.temp.name)
        self.root = self.courses / "SAT"
        (self.root / "Current").mkdir(parents=True)
        (self.root / "Home.md").write_text(HOME)
        (self.root / "Current/Practice.md").write_text("# Practice\nSynthetic exercise.")
        (self.root / "Current/Review.md").write_text("# Review\nSynthetic observations.")

    def client(self):
        app = FastAPI()
        app.include_router(classroom_routes.setup_classroom_routes())
        return TestClient(app)

    def test_source_sections_links_and_revision_without_writes(self):
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*.md")}
        result = course_plan(self.root)
        self.assertIn("five-question", result["action"])
        self.assertNotIn("Do not include", result["evidence"])
        self.assertEqual(len(result["references"]), 2)
        self.assertEqual(result["kind"], "authored_plan")
        self.assertEqual(len(result["source"]["revision"]), 64)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*.md")})

    def test_missing_sections_are_unknown_and_revision_changes(self):
        original = course_plan(self.root)["source"]["revision"]
        (self.root / "Home.md").write_text("# SAT\nNo current plan.")
        result = course_plan(self.root)
        self.assertIsNone(result["action"])
        self.assertIsNone(result["evidence"])
        self.assertNotEqual(original, result["source"]["revision"])

    def test_path_escape_symlink_and_non_markdown_rejected(self):
        outside = self.courses / "outside.md"
        outside.write_text("private")
        (self.root / "linked.md").symlink_to(outside)
        for path in ("../outside.md", str(outside), "linked.md", ".git/config", "tool.py"):
            with self.subTest(path=path), self.assertRaises(CourseSourceError):
                read_source(self.root, path)

    def test_locked_source_and_reference_rejected(self):
        (self.root / "Current/Review.md").write_text('---\nprivacy: "locked"\n---\nHidden')
        self.assertEqual(len(course_plan(self.root)["references"]), 1)
        (self.root / "Home.md").write_text("---\nlocked: true\n---\nHidden")
        with self.assertRaises(CourseSourceError):
            course_plan(self.root)

    def test_unreadable_format_and_oversized_note_rejected(self):
        for data in (b"\xff", b"x" * 1_000_001):
            (self.root / "Home.md").write_bytes(data)
            with self.assertRaises(CourseSourceError):
                course_plan(self.root)

    def test_routes_are_read_only_and_no_store(self):
        with patch.object(classroom_routes, "COURSES_ROOT", str(self.courses)), patch.dict(
            "os.environ", {"AUTH_ENABLED": "false"}
        ), self.client() as client:
            response = client.get("/api/classrooms/SAT/plan")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(client.get("/api/classrooms/SAT/daily-questions", params={"date": "2026-09-24"}).status_code, 422)
            self.assertEqual(client.post("/api/classrooms/SAT/plan", json={}).status_code, 405)
            self.assertEqual(client.get("/api/classrooms/SAT/note", params={"path": "../outside.md"}).status_code, 422)
            note = client.get("/api/classrooms/SAT/note", params={"path": "Current/Review.md"})
            self.assertEqual(note.status_code, 200)
            self.assertIn("Synthetic", note.json()["content"])
            (self.root / "Home.md").unlink()
            self.assertEqual(client.get("/api/classrooms/SAT/plan").status_code, 422)

    def test_pdf_listing_and_authenticated_read_rejects_escapes(self):
        questions = self.root / "Questions/Algebra"
        questions.mkdir(parents=True)
        pdf = questions / "Algebra.pdf"
        pdf.write_bytes(b"%PDF-1.4\nsynthetic")
        outside = self.courses / "outside.pdf"
        outside.write_bytes(b"%PDF-1.4\nprivate")
        (questions / "linked.pdf").symlink_to(outside)
        (self.root / "Tracking").mkdir()
        (self.root / "Tracking/attempts.csv").write_text("header-only")
        with self.assertRaises(CourseSourceError):
            pdf_source_path(self.root, "Questions/Algebra/linked.pdf")
        with patch.object(classroom_routes, "COURSES_ROOT", str(self.courses)), patch.dict(
            "os.environ", {"AUTH_ENABLED": "false"}
        ), self.client() as client:
            materials = client.get("/api/classrooms/SAT").json()["materials"]
            self.assertNotIn("Tracking", [item["name"] for item in materials])
            questions_item = next(item for item in materials if item["name"] == "Questions")
            self.assertEqual(questions_item["items"][0]["items"][0]["type"], "pdf")
            response = client.get("/api/classrooms/SAT/pdf", params={"path": "Questions/Algebra/Algebra.pdf"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "application/pdf")
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.content, pdf.read_bytes())
            for path in ("../outside.pdf", "Questions/Algebra/linked.pdf", "Current/Practice.md"):
                self.assertEqual(client.get("/api/classrooms/SAT/pdf", params={"path": path}).status_code, 422)

    def test_routes_require_authentication(self):
        with patch.object(classroom_routes, "COURSES_ROOT", str(self.courses)), patch.dict(
            "os.environ", {"AUTH_ENABLED": "true", "LOCALHOST_BYPASS": "false"}
        ), self.client() as client:
            self.assertEqual(client.get("/api/classrooms/SAT/plan").status_code, 401)
            self.assertEqual(client.get("/api/classrooms/SAT/daily-questions").status_code, 401)
            self.assertEqual(client.get("/api/classrooms/SAT/pdf", params={"path": "Questions/Algebra/Algebra.pdf"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
