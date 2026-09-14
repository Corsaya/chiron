# Calendar ↔ Projects

A read-only local integration, independent of Chiron's database and calendar
provider. The project note owns its stable `id`, tasks and status; the calendar
owns event times and recurrence. No second project registry or writable event
store is created.

Run with `uv run scripts/calendar-projects.py ...`; inline dependencies use the
existing calendar parser family and PyYAML. Alternatively use Python in an
environment containing `icalendar` and `PyYAML`. Nothing runs in the background.

## Project to calendar

The selected Markdown note needs YAML frontmatter with a unique, stable `id`.
Select the real project note, not a new duplicate created for this tool.

```bash
uv run scripts/calendar-projects.py describe \
  --vault-root /path/to/vault \
  --note /path/to/vault/Projects/Example.md
```

Paste the resulting `Project: example-id` line into the existing event's
description. Preserve its other description content. This does not create or
reschedule an event. Optional `--vault-name 'My Vault'` adds an Obsidian URI;
the installed vault name must match on the device. Test the link on your phone.
The ID-only default avoids putting private note paths into calendar metadata.

## Calendar to project

Export one calendar privately from its current owner, then run:

```bash
uv run scripts/calendar-projects.py events \
  --vault-root /path/to/vault \
  --note /path/to/vault/Projects/Example.md \
  --ics /private/path/export.ics
```

JSON output contains linked event records, recurrence rules/exclusions,
exceptions, source checksum, and file modification time. It is **not an expanded
agenda**, capacity/conflict calculation, or proof of live provider freshness.
Cancelled records remain visibly cancelled. Exceptions without a marker inherit
their series marker; an explicit different project marker overrides inheritance.
Use one source calendar per command to preserve UID scope. Unmarked events are
not guessed from titles; zero results is not proof that nothing is scheduled.

## Permissions, operation and rollback

The user is the accountable owner. Trigger is an explicit local command.
Inputs are one named note and optionally one named ICS export. Output goes to
stdout; there are no network/provider calls, writes, cached indexes, or retries.
Same inputs produce the same references/records; timestamps describe the file.
Errors are visible on stderr with exit 2. No daemon needs disabling. Removing
the pasted project marker reverts the calendar-side link without touching time,
tasks, or history.

Only select authorized inputs. The tool enforces the chosen root after symlink
resolution and rejects `.locked` directory markers and locked frontmatter. This
is not a security sandbox or a replacement for the owner's access instructions.
It reads only note frontmatter; it never copies project prose or task lists into
calendar descriptions. Export reports may contain private event titles/paths:
do not send them to public CI or commit them into a public repository.

Known limitations: live provider editing, migration, calendar UI integration,
cross-vault ID uniqueness audits, note-rename discovery, and recurrence expansion
are outside this first integration. No task is marked complete by an event.

Validation: `uv run --no-project --with icalendar --with pyyaml python tests/test_calendar_projects_local.py`.

Implementation references: [icalendar parsing](https://icalendar.readthedocs.io/en/latest/how-to/usage.html)
and [Obsidian URI](https://help.obsidian.md/Extending+Obsidian/Obsidian+URI).
