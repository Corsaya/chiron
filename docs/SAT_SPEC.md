# SAT first implementation

Authority: [Workspace standards](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/AGENTS.md), [ownership specification](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Knowledge%20Architecture.md), and [project decisions](../../../../Documents/Obsidian/pytheas-vault/Architecture/Pytheas%20and%20Chiron%20Project%20Map.md#chiron-reconciliation-decisions--2026-09-14). This code-coupled document grants no new data ownership. Delivery status and gates belong to the [owning roadmap](../../../../Documents/Obsidian/life-vault/personal-private/Workspace/Implementation%20Roadmap.md#chiron-documentation-reconciliation--2026-09-14).

Status: full-loop target; the first delivered increment is the read-only source-to-recommendation view. Practice writes remain gated. Derives from [ARCHITECTURE.md](ARCHITECTURE.md) and principles 2–8 in [PHILOSOPHY.md](PHILOSOPHY.md).

## User loop

1. Open the existing SAT course view through current navigation; link the existing goal and optionally supply available study time.
2. Inspect the proposed mission and its reason.
3. Start an appropriate existing course practice block; transitions are only a synthetic interface fixture, not a personalized priority.
4. Identify the relationship before answering the question.
5. Receive feedback tied to the authored answer and explanation.
6. Complete the session and inspect observations and a follow-up proposal.

Reuse the existing course Home, active-attempt Daily Training Loop, Tracking Guide, skill IDs, drills, mistakes, and assessment structure. Inspect those owners before mapping a writer. Synthetic original fixtures may exercise the interface but do not become a second course library. Existing sources determine current study priorities.

## Recommendation boundary

The previously proposed “most errors in three sessions” rule and transitions-first default are withdrawn: they would compete with the existing SAT study and review workflow. First expose the current source-linked next action and its evidence. If a source lacks rationale, label it as an authored plan rather than manufacture a personalized inference. Automated ranking is deferred until mapped to and accepted in the owning SAT workflow.

Missing evidence remains explicit. A selected practice block must fit the user's declared available time; no calendar inference or editing is introduced. A full practice test is not the first software acceptance gate.

## Acceptance criteria

- Empty history shows no invented accuracy, mastery, readiness, or score.
- Recognition and solving responses remain separate observations.
- Every personalized proposal resolves to inspectable evidence and states uncertainty.
- A failed save keeps the response recoverable and does not show completion.
- Retried submissions do not duplicate evidence; interrupted sessions resume after restart.
- Completion reports actual results and proposes a next step without changing commitments.
- All core interactions work without a model connection; authoritative records remain readable in the vault.

## Deferred

Full SAT coverage, calibrated mastery, adaptive tests, score prediction, generated items, XP, and automatic scheduling. The first delivery validates the interaction and evidence loop; it does not establish learning efficacy. Later evaluation must examine delayed performance on unfamiliar items before making improvement claims.

## Read-only increment acceptance

In the existing SAT Classroom entry, show the course-authored next action, an expandable evidence section, and buttons opening the source and referenced course notes. Show source modified time and a revision fingerprint. Clearly label this as the recorded plan, not a live assessment. Missing/malformed/locked sources fail visibly without hiding existing course navigation. SAT shows no localStorage completion or inferred mastery. The endpoint is authenticated, read-only, path-confined, and uncached; no vault script is executed.

Validate with synthetic source fixtures, actual ASGI route requests, and the existing Classroom UI in a browser at desktop/mobile widths. Inspect the real source read-only separately; never place personal content in fixtures or screenshots. This increment does not satisfy the full practice-runner acceptance criteria above.

## Reproduce the read-only checks

Use a Python environment with FastAPI, httpx, uvicorn, and Playwright installed; no production dependency was added. From the repository root:

```bash
python -m unittest tests.test_sat_course -v
node --check static/classroom.js
python -m tests.sat_course_preview
```

With the synthetic preview running, in a second terminal:

```bash
python -m tests.sat_course_browser
```

The browser command accepts `--chromium /path/to/chromium` when using an existing browser installation and `--output` for screenshots. It opens actual Classroom assets and routes against temporary synthetic records on loopback port 8768; stop the preview with Ctrl+C. It does not start the full application or prove deployment authentication/middleware compatibility. Route authentication is covered separately by the focused tests. Real deployment retains `CHIRON_COURSES_ROOT` and the existing authentication configuration; do not point the synthetic preview at personal records.
