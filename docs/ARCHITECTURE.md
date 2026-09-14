# Chiron implementation architecture

Authority: [Workspace standards](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/AGENTS.md), [ownership specification](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Knowledge%20Architecture.md), and [project decisions](../../../../Documents/Obsidian/pytheas-vault/Architecture/Pytheas%20and%20Chiron%20Project%20Map.md#chiron-reconciliation-decisions--2026-09-14). This code-coupled document grants no new data ownership. Delivery status and gates belong to the [owning roadmap](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Implementation%20Roadmap.md#chiron-documentation-reconciliation--2026-09-14).

Status: proposed implementation baseline; not a description of shipped functionality.
Product principles: [PHILOSOPHY.md](PHILOSOPHY.md). Workspace ownership rules govern their implementation.
Product purpose and essential experience: [VISION.md](VISION.md).

## First delivery

Extend the existing SAT course view with one loop: a contextual suggestion proposes an activity from the existing course workflow, the learner inspects why, completes practice, and sees recorded evidence and a justified follow-up. No external intelligence service is required for this loop.

The existing application has a Python server in `app.py`, route modules, a static frontend, classroom routes, and vault integrations. Extend these boundaries rather than replacing the application shell. Existing workspace features remain available during incremental delivery.

## Responsibilities

- Core: adapters to existing owners, provenance, derived interpretations, proposals, and safe owner-scoped writes after schema mapping.
- Domain adapters: references to existing capabilities, activity content, scoring, and study workflow; no competing subject policy.
- Experience: contextual course views, session interactions, evidence inspector, and journey context within existing Home/Daily navigation.

The experience references authoritative domain records through adapters; it does not independently calculate mastery. Domains propose actions; they do not mutate commitments. Optional coaching consumes the same evidence available to the inspector.

## Persistence boundary

SAT content and errors remain in existing `learning/Courses/SAT/` ownership (physical `learning-vault/Courses/SAT/`); Health, goals, tasks, and calendar retain their Workspace owners. Chiron adds no canonical record tree. Any justified indexes are rebuildable and owner-scoped; do not build one before the Workspace search gate requires it. Existing operational databases remain unchanged.

Reuse configured vault access boundaries. Validate ownership, schema, references, and permitted paths before writes. Use atomic replacement and revision checks; expose conflicts instead of overwriting external edits. Register any new fixed storage paths through the existing constants convention.

## Delivery authority

Sequence, dependencies, file ownership, and status live only in the [Workspace implementation roadmap](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Implementation%20Roadmap.md#chiron-documentation-reconciliation--2026-09-14). No application changes are authorized by this document.

## Experience references

[DESIGN_SYSTEM.md](DESIGN_SYSTEM.md), [UI_GUIDELINES.md](UI_GUIDELINES.md), [COACH.md](COACH.md), [LENSES.md](LENSES.md), and [JOURNEYS.md](JOURNEYS.md) define supporting boundaries. Cross-domain scheduling, generated questions, score prediction, XP, and narrative generation are deferred.
