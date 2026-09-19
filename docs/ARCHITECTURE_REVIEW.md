# Chiron Architecture Review

Status: Accepted review, 2026-09-19

## Purpose

This review evaluates Chiron as a maintainable personal-performance orchestration layer built on Odysseus. It distinguishes current implementation from planned capability and identifies the documentation, ownership, privacy, and testing work required before feature development resumes.

The review is intentionally implementation-facing. Private knowledge, local filesystem details, personal records, and confidential roadmap material remain outside this public repository.

## Executive assessment

Chiron is currently a thin integration layer on a large Odysseus modular monolith. The inherited platform already provides a FastAPI backend, static browser client, authentication, agents, tasks, calendar, notes, documents, email, model management, SQLite-backed records, JSON configuration stores, vector retrieval, and supporting services. Chiron adds knowledge-source ingestion, filesystem-backed course browsing, a lesson tutor, repository status controls, build metadata, and a read-only calendar/project reference tool.

The fork strategy remains sound. A rewrite or immediate split into many domain packages would increase maintenance risk without proving user value. Chiron should retain Odysseus as its core and add small, explicit adapters for domains such as learning, admissions, projects, and health.

The immediate problem is architectural truthfulness and checkout reconciliation. At the start of this review, the local checkout was three commits behind `origin/dev`, making documented SAT adapter files and specifications appear absent. Fetching the remote showed that those artifacts existed and had been verified in the newer revision. This is evidence that architecture audits must identify and reconcile the exact local and remote revisions before declaring an implementation missing. Existing behavior still creates state outside canonical knowledge sources, so new feature work should remain frozen until ownership contradictions are resolved.

## Current architecture

```text
Browser client (static HTML/CSS/JavaScript)
                    |
FastAPI application and route modules
                    |
Core auth, database, sessions, agents, schedulers
                    |
SQLite + JSON operational stores + derived indexes
                    |
Read-only canonical knowledge sources and external providers
```

### Inherited platform

- `app.py` is the application composition root.
- `routes/` exposes product capabilities through FastAPI routers.
- `core/` owns authentication, middleware, sessions, and the primary SQLAlchemy schema.
- `src/` contains managers, agent/tool execution, indexing, scheduling, model integration, and runtime configuration.
- `services/` contains search, memory, research, media, and model-support subsystems.
- `static/` is a large browser application composed primarily of static HTML, CSS, and JavaScript modules.
- Docker Compose supplies the application and supporting retrieval/notification services.

### Chiron integration layer

- Configured knowledge roots are registered with the inherited personal-document index.
- A polling watcher detects broad source changes and refreshes derived indexes.
- Classroom reads course Markdown directly from a configured source directory.
- A lesson tutor sends bounded lesson context to a configured model.
- Repository endpoints inspect configured roots and currently expose mutation operations.
- A standalone calendar/project tool joins read-only calendar data to project references.

## Ownership model

Chiron must preserve one authoritative owner per information type.

| Information type | Authority | Chiron responsibility |
| --- | --- | --- |
| Human-readable knowledge and plans | Canonical Markdown source | Read, index, render, reference, and write only through an approved adapter |
| External commitments and issued records | Issuing provider | Cache or display with source identity and freshness |
| Application sessions, authentication, connector cursors | Chiron operational stores | Own, back up, restore, and expire |
| Search/vector data | Rebuildable derived indexes | Recreate from source; never block direct source access |
| Domain progress and evidence | Existing domain record owner | Derive analytics; do not create parallel writable state |
| Secrets | Existing secret-storage boundary | Never store in Markdown, Git, logs, or generated documentation |

Every adapter must state its source owner, allowed paths, stable identifiers, read/write direction, idempotency rule, privacy boundary, failure signal, and rollback.

## Findings

### AR-01 — Documentation and checkout state had drifted

Architecture and delivery documents described SAT adapter files and code-coupled specifications that were absent from the initial local revision but present in three newer `origin/dev` commits. The local checkout had not fetched those commits. A feature may not be labeled missing, implemented, deployed, or verified until both the stated revision and relevant remote state have been reconciled.

Impact: critical. Stale checkout state can create false missing-feature reports, while unsupported completion receipts can make new work depend on unavailable behavior.

Required correction:

1. Establish the actual checkout and revision as the implementation baseline.
2. Fetch and compare the relevant remote before concluding that documented work is missing.
3. Make one roadmap authoritative for execution status.
4. Link every completed task to inspectable code and verification evidence.

Acceptance criteria:

- Every current implementation claim resolves to a tracked file and commit.
- Every verification claim includes a reproducible command or manual test record.
- Historical, remote-only, or checkout-specific claims are labeled as such.

### AR-02 — Privacy policy is not fully enforced

Configured knowledge sources are ingested broadly. The repository supports manual exclusions and hidden-directory filtering, but the policy-level locked-content boundary is not demonstrably enforced at discovery, indexing, search, or model-context boundaries.

Impact: critical. Documentation cannot protect private data when runtime code ignores the marker.

Required correction:

1. Specify file- and folder-level lock semantics.
2. Fail closed when a lock marker is malformed or ambiguous.
3. Enforce the boundary before indexing and again before model context is assembled.
4. Remove derived entries when access is revoked.
5. Test locked fixtures across indexing, search, direct reads, watchers, logs, and model calls.

Acceptance criteria:

- Locked content never appears in indexes, search results, cached snippets, logs, or model payloads.
- Unlocking requires an explicit source change and produces an auditable reindex.
- Deletion or revocation removes derived data.

### AR-03 — Learning state has competing owners

The Classroom client stores completion in browser-local state, while canonical learning evidence lives elsewhere. The tutor also writes a separate JSON study log without a functioning export/retention lifecycle.

Impact: critical for evidence quality. Multiple completion and study-history stores can disagree while each appears authoritative.

Required correction:

1. Remove or clearly demote browser-local completion to a non-authoritative display preference.
2. Stop treating the tutor JSON log as evidence.
3. Read existing domain records through a source-revision-aware adapter.
4. Add writes only through an approved, idempotent domain contract.

Acceptance criteria:

- One source owns completion, attempts, mistakes, and mastery evidence.
- Derived views display source path, revision, and freshness.
- Repeated submission cannot create duplicate evidence.
- External source changes cause a visible conflict rather than silent overwrite.

### AR-04 — Repository controls exceed the approved boundary

The current repository UI includes stage-all, commit, and push operations. Initial Git service scope is discovery, status, fetch, pull, and opening a repository. Automatic commit, push, merge, and conflict resolution are prohibited.

Impact: high. Broad mutations can publish unrelated or private work and are inconsistent with read-only source mounts.

Required correction:

1. Disable commit and push endpoints and UI.
2. Specify repository discovery roots and stable repository identity.
3. Implement status before network operations.
4. Add fetch and fast-forward-only pull with visible refusal on dirty/diverged/conflicted repositories.
5. Never stage, commit, push, merge, or resolve automatically.

Acceptance criteria:

- Discovery handles nested repositories without duplicates.
- Status reports branch, modified state, upstream, ahead, behind, and remote.
- Pull runs only when the worktree is clean and the update is fast-forwardable.
- All refusal states are explicit and leave the repository unchanged.

### AR-05 — Chiron lacks a repository-level identity and contract set

The entry README and roadmap primarily describe upstream Odysseus. A maintainer cannot determine the Chiron delta, governing documents, supported deployment, or accepted ownership boundaries from the repository alone.

Impact: high. Contributors can follow valid upstream guidance that is wrong for Chiron.

Required documents:

- public-safe agent instruction pointer;
- Chiron overview and inherited/upstream boundary;
- architecture and storage contracts;
- privacy/indexing specification;
- domain-adapter specification template;
- Git service specification;
- testing and deployment contracts;
- technical-debt/GOTCHAS ownership.

### AR-06 — Polling and broad refresh will not scale

The current watcher recursively scans every configured source on a short interval and triggers a broad refresh after a coarse fingerprint change.

Impact: medium now, high at the stated long-term scale.

Required direction:

1. Measure current scan and refresh cost.
2. Add bounded backoff and observable health before changing mechanisms.
3. Move toward per-file event ingestion or a durable incremental queue when evidence justifies it.
4. Keep direct source access functional when an index is stale or unavailable.

### AR-07 — Chiron-specific verification is insufficient

The inherited test suite is large, but direct coverage of the Chiron integration layer is sparse. The documented local test environment does not currently provide the expected test runner.

Impact: high. Upstream test volume can create false confidence in personal integrations.

Required correction:

1. Define a reproducible Chiron development/test environment.
2. Add focused adapter, privacy, source-confinement, and failure-state tests.
3. Separate synthetic automated fixtures from read-only real-source acceptance checks.
4. Require runtime/browser verification for UI changes.

## Dead or contradictory surfaces

These are candidates for removal or redesign after dependency confirmation:

- empty custom Classroom application dispatch and its remaining middleware exception;
- tutor-log read/clear functions with no consumer;
- copy referring to a removed adaptive-drill export flow;
- repository commit/push endpoints and UI;
- browser-local completion presented as progress;
- upstream-only onboarding presented as Chiron onboarding.

No item should be removed solely because this review identifies it. Each removal needs an exact dependency search, migration impact, rollback, and focused verification.

## Naming rules

- Chiron is the product name.
- Odysseus names remain where compatibility or upstream synchronization requires them.
- A domain integration should use `adapter`, `projection`, or `view` when it does not own the underlying record.
- “Module” means an independently testable adapter/service boundary, not necessarily a new top-level package.
- “Vault,” “repository,” “knowledge source,” and “operational store” must not be used interchangeably.

## Target architecture

```text
Canonical knowledge and provider records
                 |
        source-specific adapters
                 |
Odysseus core services and operational stores
                 |
 source-linked projections and contextual guidance
```

The target is not ten isolated applications. It is one inherited core with small adapters that preserve source authority.

Each adapter owns only:

- source mapping and validation;
- stable identifier translation;
- privacy and permission enforcement;
- rebuildable projections;
- narrowly approved writes;
- conflict and failure reporting.

## Migration roadmap

### Phase 0A — Reconcile truth

- Freeze new production features.
- Record the actual repository baseline and custom-commit inventory.
- Reconcile each implementation receipt against local and remote revisions.
- Select one execution roadmap.
- Repair broken and checkout-specific documentation links.

Exit: every current status claim is reproducible from the named revision.

### Phase 0B — Approve specifications

- Adopt architecture decision records.
- Approve storage, privacy/indexing, adapter, Git, testing, and deployment specifications.
- Establish a single technical-debt/GOTCHAS owner.

Exit: every proposed write path has an owner, schema/format, permission, idempotency rule, failure signal, and rollback.

### Phase 0C — Correct unsafe contradictions

- Enforce locked-content exclusion.
- Disable competing learning state and repository mutations.
- Remove stale UI claims after dependency review.
- Establish focused Chiron tests.

Exit: no known path bypasses privacy or writes a competing canonical record.

### Phase 1A — Read-only learning adapter

- Map current source records and identifiers.
- Render one existing next action and supporting evidence.
- Display source, revision, freshness, and privacy scope.
- Test missing, stale, malformed, linked, and locked sources.

Exit: useful read-only behavior with unchanged source bytes and timestamps.

### Phase 1B — Evidence capture

- Add recoverable draft state only in the approved canonical format.
- Publish evidence idempotently.
- Detect source-revision conflicts.
- Derive analytics from canonical rows without inventing mastery.

Exit: one reviewed session writes evidence exactly once and existing projections reproduce it.

### Later phases

Apply the same adapter contract to planning/reflection, repository management, admissions, projects, health, finance, and automation. Expansion requires evidence that the preceding adapter reduces real friction without creating another source of truth.

## Risk assessment

| Risk | Rating | Required control |
| --- | --- | --- |
| False implementation receipts | Critical | Revision-linked evidence and one task authority |
| Private content indexed or sent to a model | Critical | Fail-closed locked-content enforcement |
| Conflicting domain progress | Critical | One canonical record owner |
| Unintended Git publication | High | Remove commit/push; constrain pull behavior |
| Upstream maintenance burden | High | Delta inventory and explicit merge policy |
| Non-restorable operational state | High | Storage catalog and restore drill |
| Polling cost at scale | High long-term | Measurement and incremental indexing path |
| Sparse integration tests | High | Chiron-specific verification lane |

## Change protocol

Before deleting, renaming, moving, or consolidating anything:

1. Explain why the current structure is insufficient.
2. Identify current and proposed owners.
3. Count affected files, links, routes, tests, configurations, and workflows.
4. Provide a dry run and rollback.
5. Preserve existing work and history.
6. Obtain approval for irreversible changes.
7. Apply one logical migration per commit and verify behavior plus links.

## Decision

Keep the Odysseus fork. Treat Chiron as an inherited platform with a small, explicit adapter layer. Reconcile documentation and enforce canonical ownership/privacy before adding features. The first successful architecture milestone is a trustworthy boundary: canonical records in, source-linked operational guidance out, and no invisible second owner between them.
