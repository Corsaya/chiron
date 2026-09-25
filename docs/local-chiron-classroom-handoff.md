# Local Chiron Classroom handoff

Source: the current Obsidian Vault project cloud conversation, September 24–25, 2026. Its thread ID and exact title are not exposed in this workspace. This is a point-in-time continuation; the cloud workspace cannot access the ThinkPad's filesystem, Docker daemon, or local Codex task list.

## Completed upstream

- SAT roadmap saved in `Corsaya/obsidian-vault`, under `02-School/SAT/`.
- Chiron `dev` gained a Classroom home link, guided Desmos examples, startup error handling, a finite API timeout, and current HTML navigation.
- The Docker publish workflow was repaired; the last workflow for the Classroom mount repair passed.
- The Classroom 404 means the running container's mounted learning vault lacks `Courses/SAT`. `scripts/chiron.sh` now preserves its selected vault path through `sudo`, and validates that path before starting.

## Local task

1. Inspect the current Chiron checkout, `.env` (do not print secrets), Docker Compose mounts, and the location of the actual `Courses/SAT` folder. Preserve unrelated changes.
2. Pull `dev` if the checkout is clean and behind. If it is dirty, reconcile without discarding user edits.
3. Run `bash scripts/setup-chiron-local-env.sh` from the Chiron checkout, or set `CHIRON_LEARNING_DIR` explicitly to the absolute parent of `Courses` if the script cannot locate it.
4. Check `docker compose ps`, the mounted course inside `odysseus`, and the authenticated `/api/classrooms/SAT` and `/api/classrooms/SAT/plan` responses. Open the SAT Classroom in the browser and verify the Desmos coach. Report exact failures, without exposing `.env` secrets.

Do not replay completed GitHub commits, vault writes, repository restructuring, or unrelated installations. This local task is to configure and verify the ThinkPad environment.
