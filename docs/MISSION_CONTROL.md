# Mission Control

Authority: [Workspace standards](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/AGENTS.md), [ownership specification](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Knowledge%20Architecture.md), and [project decisions](../../../../Documents/Obsidian/pytheas-vault/Architecture/Pytheas%20and%20Chiron%20Project%20Map.md#chiron-reconciliation-decisions--2026-09-14). This code-coupled document grants no new data ownership. Delivery status and gates belong to the [owning roadmap](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Implementation%20Roadmap.md#chiron-documentation-reconciliation--2026-09-14).

Status: initial interaction specification. Implements principles 1, 5, and 8 in [PHILOSOPHY.md](PHILOSOPHY.md).

“Mission Control” is a contextual view concept, not a new dashboard, homepage, or navigation root. Extend the existing SAT course entry and existing Home/Daily links; preserve their authority and routes. Show a source-linked suggestion, optional time budget, and results from existing records. No new aspiration setup or copied daily task checklist is required.

## Main interaction

Present the proposed action, duration estimate, reason, and Start action. Keep “Why this?” and “Choose another” adjacent. After the source-schema gate, starting creates or resumes work through the existing SAT tracking owner; it does not create a calendar commitment.

The evidence inspector shows referenced observations, interpretation, uncertainty, relevant constraints, and what could change the recommendation. A general baseline suggestion is labeled as such.

## States

| State | Behavior |
| --- | --- |
| No history | Offer baseline practice without personal claims |
| Proposal ready | Show one primary next action and its reason |
| Active session | Offer resume; prevent accidental duplicate sessions |
| Completed | Show recorded accomplishment and follow-up proposal |
| Save failure | Preserve work and offer retry without false success |
| Invalid vault record | Explain the affected record and allow unaffected work |
| No fitting activity | Offer a time-budget change or return later |

Later multi-domain planning must respect commitments and expose conflicts. Lens switching alone never changes the schedule. No universal readiness score or cross-domain performance percentage is part of this delivery.
