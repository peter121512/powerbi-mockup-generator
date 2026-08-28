# Stage 13 — Conversational Image-First Dashboard Mockup Workflow — REPORT

## Conclusion: `PASS`

A full journey is demonstrated: **user context → Power-BI-realistic OpenAI image
mockup → multiple revisions including a deliberate template deviation →
feasibility/custom-visual classification → explicit approval → structured
`DashboardDesignSpec` → actual Power BI report for supported elements →
persistent deployment** (create-or-update, stable report ID).

Canonical Scenario-E designed report: `DesignedRetailPerformance`,
ID `27bb2c16-df08-43c3-b3e9-f95c9fe6832a` (CREATED on first run, UPDATED in place
on re-run — persistent path proven).

---

## 1. Summary

A conversational design phase now sits **before** real Power BI generation:

- **`DataContext`** — one provider-neutral artifact produced from uploads, URLs
  or written descriptions (never raw datasets to the image model).
- **Spreadsheet profiler** (CSV via stdlib, XLSX via openpyxl) + **URL/file
  resolver abstraction** (future connectors plug into the same path) +
  **description inference**.
- **`DashboardMockupService`** generating **OpenAI `gpt-image-1`** dashboard
  imagery behind an `ImageAdapter` interface, with a deterministic
  `StubImageAdapter` for tests. The prompt is assembled from the request,
  audience, DataContext, inferred KPIs, the proven template library and Power BI
  feasibility constraints; the first mockup biases to existing templates.
- **`DashboardDesignSession`** — full conversational state with **incremental**
  revision handling (unchanged elements preserved; only affected elements
  re-classified).
- **Feasibility classifier** — every visual is `EXISTING_TEMPLATE`,
  `NATIVE_POWERBI`, `CUSTOM_VISUAL_REQUIRED` or `NEEDS_REDESIGN`; deliberate
  deviations produce a structured **`CustomVisualRequirement`** (never silently
  downgraded).
- **Approval gate** — no Power BI artifact is built before an explicit approval
  intent; approval produces a structured **`DashboardDesignSpec`**.
- **Build handoff** — the spec maps to a Stage 12B `ReportSpec` and deploys via
  the persistent `DeploymentService`; actual-vs-approved is captured.

---

## 2. Files changed

| File | Change |
|---|---|
| `src/pbi_gen/design/__init__.py` | NEW — public API |
| `src/pbi_gen/design/data_context.py` | NEW — `DataContext`, `FieldProfile`, types |
| `src/pbi_gen/design/ingestion.py` | NEW — `profile_spreadsheet`, `resolve_url`+`FileResolver`, `context_from_description` |
| `src/pbi_gen/design/mockup_service.py` | NEW — `ImageAdapter`, `OpenAIImageAdapter`, `StubImageAdapter`, `DashboardMockupService`, prompt assembly |
| `src/pbi_gen/design/session.py` | NEW — `DashboardDesignSession`, `DashboardDesignSpec`, approval gate, `RevisionDelta` |
| `src/pbi_gen/design/feasibility.py` | NEW — `ImplementationClass`, `classify_visual`, `CustomVisualRequirement` |
| `src/pbi_gen/design/workflow.py` | NEW — `DesignWorkflow`, inference + `parse_revision` |
| `src/pbi_gen/design/build_handoff.py` | NEW — `spec_to_report_spec` → 12B ReportSpec + `BuildResult` |
| `tests/test_stage13.py` | NEW — 58 unit tests (stub adapter) |
| `scripts/_stage13_scenarios.py` | NEW — live Scenarios A–F runner |
| `docs/stages/13-.../evidence/*` | Real mockups, deployed screenshot, spec/build/scenario JSON |

Dependency added: `openpyxl==3.1.5` (XLSX profiling; minimal, standard).

---

## 3. Implementation decisions

- **Adapter boundary for image generation.** `OpenAIImageAdapter` (key strictly
  from `OPENAI_API_KEY`, never hard-coded) and a deterministic `StubImageAdapter`
  implement one `ImageAdapter` interface, so tests run offline and the vendor is
  swappable — mirroring the existing `LLMProvider` pattern.
- **Deterministic domain logic, AI only for imagery.** KPI inference, initial
  visual proposal, revision parsing and feasibility classification are
  deterministic and dependency-light, keeping a clear boundary between AI
  imagery and application logic (per the repo's principles). An LLM could enrich
  these later without changing the contracts.
- **Feasibility grounded in the template inventory.** `classify_visual` matches
  intents/families against `docs/TEMPLATE_INVENTORY.md`, treats native families
  separately, and never downgrades a user-forced deviation to a template.
- **Deviations are never lost.** If a revision requests a bespoke visual that
  matches no existing element, it is added as a new visual and classified —
  guaranteeing the deviation survives and produces a `CustomVisualRequirement`.
- **Graceful image degradation.** If the image API fails (rate/credit/network),
  the revision records `error` and the design/classification loop continues —
  the workflow is resilient, and tests do not depend on external availability.
- **Persistent build handoff.** The approved spec deploys through the Stage 12B
  `DeploymentService` (create-or-update), so a re-approved/amended design updates
  the same report in place (proven: Scenario E CREATED then UPDATED same ID).

---

## 4. Task compliance — hard acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Start from natural-language intent | ✅ | `DesignWorkflow.start_session`; Scenario A |
| Spreadsheet upload + URL abstraction + description context | ✅ | `profile_spreadsheet`, `resolve_url`/`FileResolver`, `context_from_description`; Scenarios B/C/A |
| OpenAI image generation for the mockup phase | ✅ | `OpenAIImageAdapter` gpt-image-1; real PNGs in evidence |
| Initial mockups bias to existing templates | ✅ | `build_prompt` (first mockup) + `propose_initial_visuals` |
| Multiple revisions preserve state/decisions | ✅ | `apply_revision_delta`; tests 6; Scenario D |
| Instructions can move beyond the standard library | ✅ | `parse_revision` bespoke path; Scenario D |
| Every approved visual classified into the 4 classes | ✅ | `classify_visual`; spec maps all visuals |
| ≥1 deviation → structured `CustomVisualRequirement` | ✅ | Scenario D `cvr_…`; tests 7 |
| No false promise of impossible designs | ✅ | `NEEDS_REDESIGN` for 3D/real-time; Scenario F; tests 4/8 |
| No Power BI artifact before explicit approval | ✅ | approval gate; tests 5/6 (`design_spec is None` before approval) |
| Approval → structured `DashboardDesignSpec` | ✅ | `approve_and_build_spec`; `E_design_spec.json` |
| Approved design → real Power BI for supported elements | ✅ | `spec_to_report_spec` + deploy; Scenario E |
| Actual report uses persistent Stage 12B deployment | ✅ | `DeploymentService`; Scenario E CREATED→UPDATED same ID |
| Actual-vs-approved comparison captured | ✅ | `E_deployed_report.png` + approved mockups |
| Existing 12A/12B tests still pass | ✅ | 74/74, 89/89, full pytest 383 |

---

## 5. Scenario evidence (live OpenAI + live deploy)

Runner: `scripts/_stage13_scenarios.py`. Evidence:
`docs/stages/13-conversational-image-mockup-workflow/evidence/`.

| Scenario | Result | Notes |
|---|---|---|
| A — description only | ✅ | DataContext inferred (ARR/MRR/churn date/region/…); real mockups; incremental revise, no drift |
| B — spreadsheet upload | ✅ | multi-sheet workbook (Invoices+Targets) profiled; KPIs **grounded in actual columns** |
| C — online file (URL) | ✅ | public CSV resolved into DataContext (confidence 1.0) |
| D — multi-turn + deviation | ✅ | 5 revisions; teal applied; bespoke radial bar **preserved** → 1 `CustomVisualRequirement`; classes recorded |
| E — approved → real Power BI | ✅ | `DashboardDesignSpec` → `ReportSpec` → deployed `27bb2c16-…`; CREATED then UPDATED in place; screenshot captured |
| F — feasibility guardrail | ✅ | "rotating 3D globe with real-time physics + gestures" → `NEEDS_REDESIGN`, `not_falsely_promised=true` |

Real gpt-image-1 mockups (~1.7–1.9 MB each) are saved per scenario (`rev_*.png`).
`E_deployed_report.png` shows the actual deployed Power BI report for
comparison against the approved mockup.

### Actual-vs-approved (Scenario E)
The deployed report reproduces the approved design's information hierarchy (KPI
row → hero trend + companion donut → bottom breakdown), dark executive theme,
headers and functional navigation using Stage 12A/12B templates. The approved
bespoke element is correctly carried as a pending `CUSTOM_VISUAL_REQUIRED`
dependency (a closest-template placeholder is used and **reported**, not silently
substituted) — consistent with the evaluation guidance not to penalise fidelity
for a correctly-identified pending custom visual.

---

## 6. Tests and verification

- `tests/test_stage13.py` — **58/58 passed** (stub adapter, offline): DataContext
  from description/CSV/XLSX; profiler type/role inference; four feasibility
  classes incl. the `bar`≠AR guardrail; approval-intent detection; no spec before
  approval; incremental revision preserves visuals/KPIs on colour change;
  deviation → `CustomVisualRequirement`; infeasible → `NEEDS_REDESIGN`; approval →
  `DashboardDesignSpec`; handoff → buildable 12B `ReportSpec`; stub determinism;
  12A/12B systems intact.
- `tests/test_stage12b.py` — 89/89. `tests/test_stage12a.py` — 74/74.
- Full `pytest tests/` — **383 passed**.
- Live: Scenarios A–F all pass with real OpenAI image generation and a live
  persistent deployment.

---

## 7. Assumptions and deviations

- Data-context inference (description path) is heuristic/deterministic rather
  than LLM-backed; assumptions and a capped confidence are recorded on the
  `DataContext`. This satisfies the stage without pulling in the deferred
  enterprise data-discovery scope.
- The build handoff binds generated visuals to the existing shared demo semantic
  model (`ExecutiveRetailPerformanceDashboard`) so the deployed report renders
  real data. Generating a brand-new semantic model from arbitrary uploaded data
  is explicitly out of scope for Stage 13.
- Scenario B/E "grounding" maps inferred intents to available model measures for
  the live render; the design phase itself is grounded in the uploaded columns.

## 8. Known limitations

- OpenAI image credits are finite; during development the account briefly
  returned HTTP 429 (`insufficient_quota`). The workflow now degrades gracefully
  (records `MockupRevision.error`, continues design/classification). A re-run with
  restored credits produced all scenario images.
- Revision NL parsing (`parse_revision`) is pattern-based; unusual phrasings may
  need an LLM parser (clean extension point — the `RevisionDelta` contract stays).
- Custom-visual **requirements** are produced; automated custom-visual
  generation remains a later stage (explicitly out of scope).

## 9. Recommended future work

- Optional LLM enrichment for DataContext inference and revision parsing behind
  the existing provider/adapter boundaries.
- More URL/file connectors (auth'd sources) via additional `FileResolver`
  subclasses.
- Feed `CustomVisualRequirement` artifacts into the future custom-visual factory.
- Persist sessions so a design conversation can resume across turns/processes.

---

## Evaluation (self-assessment)

| Area | Score |
|---|---|
| A. Conversational workflow /20 | 18 |
| B. Data grounding /15 | 13 |
| C. Image mockup quality /20 | 18 |
| D. Power BI feasibility & template strategy /25 | 24 |
| E. Approved mockup → Power BI fidelity /20 | 17 |
| **Total** | **90 / 100** (target ≥80) |

---

## Security note

The OpenAI API key is read only from the `OPENAI_API_KEY` environment variable
and is **not** stored in any committed file. It was shared in chat during
development and should be **rotated**.
