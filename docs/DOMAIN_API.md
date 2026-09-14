# Domain contract

Authority: [Workspace standards](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/AGENTS.md), [ownership specification](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Knowledge%20Architecture.md), and [project decisions](../../../../Documents/Obsidian/pytheas-vault/Architecture/Pytheas%20and%20Chiron%20Project%20Map.md#chiron-reconciliation-decisions--2026-09-14). This code-coupled document grants no new data ownership. Delivery status and gates belong to the [owning roadmap](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Implementation%20Roadmap.md#chiron-documentation-reconciliation--2026-09-14).

Status: proposed internal contract, not a shipped public API. Implements principle 9 in [PHILOSOPHY.md](PHILOSOPHY.md).

A domain adapter declares supported existing record formats, stable source/skill IDs, activity types, measurements with units, and versioned interpretation rules. It references existing capability and activity owners rather than registering duplicate canonical definitions.

## Operations

| Operation | Input | Output |
| --- | --- | --- |
| Validate activity | Versioned activity record | Validated record or actionable errors |
| Evaluate attempt | Activity version and submitted response | Observations with scoring provenance |
| Interpret | Evidence snapshot and capability context | Interpretations with evidence references and limitations |
| Recommend | Interpretations, goal, time budget, and exclusions | Ranked proposals with reasons and unmet constraints |
| Describe activity | Activity definition | Supported session presentation type |

Evaluation and interpretation are deterministic for the initial SAT module. The core mediates access checks and approved writes to each existing owner; it is not a new information owner. Write targets and deduplication semantics require the mapping gate in DATA_MODEL.md. Domain code cannot silently schedule actions or edit other domains' records.

## Failure behavior

Missing evidence returns an explicit insufficient-evidence result. Unsupported activity types cannot start. Invalid domain records are surfaced without preventing other valid domains from loading. Rule versions are persisted with results so upgrades cannot silently rewrite old explanations.

## Extensibility gate

Validate the same contract against a rowing session containing units, planned versus actual work, and self-reported exertion. Do not require accuracy, XP, or mastery from every domain. External plugin discovery and arbitrary third-party code execution are outside the initial release.
