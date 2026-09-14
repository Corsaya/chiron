#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["icalendar>=6,<8", "PyYAML>=6,<7"]
# ///
"""Read-only project/calendar handoff; no provider access or persistent index."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

import yaml


def project_reference(root: Path, note: Path, vault_name: str | None = None) -> dict:
    """Read only the selected note's frontmatter, never scan a vault."""
    root = root.resolve(strict=True)
    note = note.resolve(strict=True)
    try:
        relative = note.relative_to(root)
    except ValueError:
        raise ValueError("Project note must be inside the selected vault root") from None
    if note.suffix.lower() != ".md":
        raise ValueError("Project note must be Markdown")
    for directory in (note.parent, *note.parent.parents):
        if (directory / ".locked").exists():
            raise ValueError("Selected path has a .locked boundary")
        if directory == root:
            break
    with note.open(encoding="utf-8-sig") as stream:
        if stream.readline().strip() != "---":
            raise ValueError("Project note requires YAML frontmatter with a stable id")
        lines = []
        for line in stream:
            if line.strip() == "---":
                break
            lines.append(line)
            if sum(map(len, lines)) > 65536:
                raise ValueError("Frontmatter exceeds 64 KiB")
        else:
            raise ValueError("Unterminated frontmatter")
    metadata = yaml.safe_load("".join(lines))
    if not isinstance(metadata, dict):
        raise ValueError("Frontmatter must be a mapping")
    if metadata.get("locked") or any(
        str(metadata.get(key, "")).lower() == "locked"
        for key in ("privacy", "access")
    ):
        raise ValueError("Selected note is locked")
    project_id = metadata.get("id")
    if not isinstance(project_id, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", project_id):
        raise ValueError("Project requires a stable id using letters, digits, dot, underscore or hyphen")
    result = {"project_id": project_id, "note": relative.as_posix()}
    if vault_name:
        result["obsidian_uri"] = "obsidian://open?" + urlencode(
            {"vault": vault_name, "file": relative.as_posix()}
        )
    return result


def description(reference: dict) -> str:
    lines = [f"Project: {reference['project_id']}"]
    if "obsidian_uri" in reference:
        lines.append(f"Notes: {reference['obsidian_uri']}")
    return "\n".join(lines)


def declared_project(event) -> str | None:
    raw = event.get("DESCRIPTION", "")
    if isinstance(raw, list):
        raise ValueError("Multiple DESCRIPTION fields in an event")
    values = re.findall(r"^Project:[ \t]*([^\r\n]*)", str(raw), re.MULTILINE)
    if len(values) > 1:
        raise ValueError("Multiple Project markers in an event")
    if not values:
        return None
    value = values[0].strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value):
        raise ValueError("Invalid Project marker")
    return value


def raw_property(event, key: str):
    value = event.get(key)
    if value is None:
        return None
    if isinstance(value, list):
        return [v.to_ical().decode("utf-8") for v in value]
    return value.to_ical().decode("utf-8")


def linked_records(data: bytes, project_id: str) -> list[dict]:
    """Return VEVENT records, not expanded agenda occurrences.

    Detached exceptions without their own Project marker inherit the master's
    marker. Overrides with an explicit different marker belong to that project.
    """
    from icalendar import Calendar

    calendar = Calendar.from_ical(data)
    if calendar.name != "VCALENDAR":
        raise ValueError("Expected one VCALENDAR export")
    for component in calendar.walk():
        if component.errors:
            raise ValueError("Calendar has parsing errors; repair the export before reading links")
    events = calendar.walk("VEVENT")
    masters = {}
    identities = set()
    for event in events:
        uid = event.get("UID")
        if uid is None or isinstance(uid, list) or not str(uid):
            raise ValueError("Every event must have exactly one UID")
        recurrence_id = raw_property(event, "RECURRENCE-ID")
        if isinstance(recurrence_id, list):
            raise ValueError("Multiple RECURRENCE-ID fields")
        identity = (str(uid), recurrence_id)
        if identity in identities:
            raise ValueError("Duplicate UID/RECURRENCE-ID pair in export")
        identities.add(identity)
        marker = declared_project(event)
        if recurrence_id is None:
            masters[str(uid)] = marker

    records = []
    for event in events:
        uid = str(event["UID"])
        marker = declared_project(event)
        inherited = marker is None and "RECURRENCE-ID" in event
        if inherited:
            marker = masters.get(uid)
        if marker != project_id:
            continue
        records.append({
            "uid": uid,
            "recurrence_id": raw_property(event, "RECURRENCE-ID"),
            "project_id": marker,
            "inherited_project": inherited,
            "summary": str(event.get("SUMMARY", "")),
            "status": str(event.get("STATUS", "")),
            "dtstart": raw_property(event, "DTSTART"),
            "dtstart_params": dict(event["DTSTART"].params) if "DTSTART" in event else {},
            "dtend": raw_property(event, "DTEND"),
            "dtend_params": dict(event["DTEND"].params) if "DTEND" in event else {},
            "rrule": raw_property(event, "RRULE"),
            "rdate": raw_property(event, "RDATE"),
            "exdate": raw_property(event, "EXDATE"),
        })
    return records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("describe", "events"))
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--note", type=Path, required=True,
                        help="Explicit canonical note path; no vault-wide scanning")
    parser.add_argument("--vault-name", help="Optional installed Obsidian vault name for a deep link")
    parser.add_argument("--ics", type=Path, help="One private calendar export, required for events")
    args = parser.parse_args(argv)
    try:
        reference = project_reference(args.vault_root, args.note, args.vault_name)
        if args.command == "describe":
            if args.ics:
                raise ValueError("--ics is only used by events")
            print(description(reference))
        else:
            if args.ics is None:
                raise ValueError("events requires --ics")
            export = args.ics.resolve(strict=True)
            data = export.read_bytes()
            report = {
                "mode": "read-only-export-records-not-expanded-agenda",
                "project": reference,
                "snapshot_file": str(export),
                "snapshot_sha256": hashlib.sha256(data).hexdigest(),
                "file_modified_at": datetime.fromtimestamp(
                    export.stat().st_mtime, timezone.utc
                ).isoformat(),
                "provider_exported_at": None,
                "warning": "File mtime is not provider freshness. Zero links does not mean no scheduled work.",
                "events": linked_records(data, reference["project_id"]),
            }
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
