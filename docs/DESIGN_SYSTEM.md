# Design system

Authority: [Workspace standards](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/AGENTS.md), [ownership specification](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Knowledge%20Architecture.md), and [project decisions](../../../../Documents/Obsidian/pytheas-vault/Architecture/Pytheas%20and%20Chiron%20Project%20Map.md#chiron-reconciliation-decisions--2026-09-14). This code-coupled document grants no new data ownership. Delivery status and gates belong to the [owning roadmap](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Implementation%20Roadmap.md#chiron-documentation-reconciliation--2026-09-14).

Status: implementation constraints. Supports principles 5, 7, and 8 in [PHILOSOPHY.md](PHILOSOPHY.md).

Extend the existing frontend's theme variables, buttons, inputs, cards, typography, and monochrome SVG icons. Follow `CONTRIBUTING.md`; do not establish a parallel styling system for SAT. Dark mode is the default and other themes use the existing theme mechanism.

## Shared components

| Component | Responsibility |
| --- | --- |
| Mission card | Action, estimate, rationale, start/resume |
| Evidence inspector | Observation, interpretation, uncertainty, proposal |
| Session runner | Prompt, response, feedback, saved progress |
| Result summary | Supported accomplishment and next proposal |
| Capability summary | Assessment context, evidence coverage, current interpretation |

Each interactive component defines loading, empty, error, disabled, and keyboard-focus behavior. Use text alongside semantic color. Explain why an action is unavailable.

Keep state calculations out of presentation components. Motion may communicate a recorded transition; it must respect reduced-motion preferences and never delay input. Celebration requires confirmed persistence, not an optimistic save.

Validate the running interface at narrow and wide widths, with keyboard-only navigation and reduced motion. Capture the result as required by the repository's contribution guidance.
