"""Standalone tests: no Chiron database, server or real personal data required."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse


spec = importlib.util.spec_from_file_location(
    "calendar_projects", Path(__file__).parents[1] / "scripts/calendar-projects.py"
)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def calendar(*events):
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n"
            + "".join(events) + "END:VCALENDAR\r\n").encode()


def event(uid="one", project="example", extra=""):
    description = "" if project is None else f"DESCRIPTION:Project: {project}\r\n"
    return (f"BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTART;TZID=America/New_York:20261025T090000\r\n"
            f"{description}{extra}END:VEVENT\r\n")


class CalendarProjectsTests(unittest.TestCase):
    def test_reference_is_id_only_by_default_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = root / "Project #1.md"
            content = "---\nid: example\n---\nPrivate prose must not be copied."
            note.write_text(content)
            ref = bridge.project_reference(root, note)
            self.assertEqual(bridge.description(ref), "Project: example")
            ref = bridge.project_reference(root, note, "My Vault")
            params = parse_qs(urlparse(ref["obsidian_uri"]).query)
            self.assertEqual(params, {"vault": ["My Vault"], "file": [note.name]})
            self.assertEqual(note.read_text(), content)

    def test_locked_and_escape_paths_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / "vault"
            root.mkdir()
            outside = parent / "outside.md"
            outside.write_text("---\nid: outside\n---\n")
            link = root / "escape.md"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "inside"):
                bridge.project_reference(root, link)
            note = root / "locked.md"
            note.write_text("---\nid: hidden\nprivacy: locked\n---\n")
            with self.assertRaisesRegex(ValueError, "locked"):
                bridge.project_reference(root, note)
            (root / ".locked").touch()
            with self.assertRaisesRegex(ValueError, "locked"):
                bridge.project_reference(root, note)

    def test_series_rules_exclusions_and_cancellation_retained(self):
        data = calendar(
            event(extra="RRULE:FREQ=WEEKLY;COUNT=3\r\nEXDATE;TZID=America/New_York:20261101T090000\r\n"),
            event(project=None, extra="RECURRENCE-ID;TZID=America/New_York:20261108T090000\r\nSTATUS:CANCELLED\r\n"),
            event(uid="other", project="other"),
        )
        rows = bridge.linked_records(data, "example")
        self.assertEqual(len(rows), 2)
        self.assertIn("COUNT=3", rows[0]["rrule"])
        self.assertEqual(rows[0]["exdate"], "20261101T090000")
        self.assertEqual(rows[0]["dtstart_params"]["TZID"], "America/New_York")
        self.assertTrue(rows[1]["inherited_project"])
        self.assertEqual(rows[1]["status"], "CANCELLED")

    def test_explicit_exception_project_wins(self):
        data = calendar(event(), event(project="other", extra="RECURRENCE-ID:20261108T090000Z\r\n"))
        self.assertEqual(len(bridge.linked_records(data, "example")), 1)
        self.assertEqual(len(bridge.linked_records(data, "other")), 1)

    def test_folded_description_and_no_fuzzy_matching(self):
        data = calendar(event(project=None, extra="DESCRIPTION:Meeting\\nProject: exa\r\n mple\\nMore detail\r\n"),
                        event(uid="unmarked", project=None, extra="SUMMARY:example\r\n"))
        self.assertEqual(len(bridge.linked_records(data, "example")), 1)

    def test_duplicate_uid_and_ambiguous_marker_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            bridge.linked_records(calendar(event(), event()), "example")
        with self.assertRaisesRegex(ValueError, "Multiple Project"):
            bridge.linked_records(calendar(event(project="example\\nProject: other")), "example")

    def test_all_day_record_is_not_converted_to_timed_event(self):
        raw = event().replace("DTSTART;TZID=America/New_York:20261025T090000", "DTSTART;VALUE=DATE:20261025")
        row = bridge.linked_records(calendar(raw), "example")[0]
        self.assertEqual(row["dtstart"], "20261025")
        self.assertEqual(row["dtstart_params"], {"VALUE": "DATE"})

    def test_empty_marker_does_not_consume_the_next_line(self):
        with self.assertRaisesRegex(ValueError, "Invalid Project"):
            bridge.linked_records(calendar(event(project="\\nOther: example")), "example")


if __name__ == "__main__":
    unittest.main()
