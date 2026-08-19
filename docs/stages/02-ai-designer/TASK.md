---
stage: 02
status: ready
title: AI dashboard designer and clarification gate
---

# Stage 02 — AI Dashboard Designer and Clarification Gate

## Context

Stage 01 established the canonical rich `DashboardSpec` contract. It now supports dashboard intent, multi-page structure, visual semantics, filters/interactions, enterprise design-system intent, semantic-model requirements, analytical mock-data narratives, structured confidence/assumptions, and revision metadata.

The next step is to create the reasoning component that converts natural-language business requirements into that structured specification.

The long-term Phase 1 product goal remains:

> A user should be able to describe the dashboard they want in natural language and receive a genuinely impressive, enterprise-grade Power BI mock-up suitable for demonstration to a C-suite audience, using coherent mocked data. Follow-up prompts should amend the same dashboard rather than regenerate an unrelated one.

The desired user experience is deliberately high-autonomy. The system should infer sensible analytical and visual decisions aggressively rather than interrogating the user for routine detail. Clarification should be reserved for ambiguity material enough that proceeding would have a substantial chance of producing the wrong dashboard.

The quality bar is not “valid JSON from an LLM”. The designer must reason about the business problem before it reasons about charts.

## Read first

Before changing code:

1. Read `KIRO.md` and follow it as the standing operating instruction.
2. Read `README.md` for product direction and architectural principles.
3. Read `docs/stages/01-dashboard-spec/TASK.md`.
4. Read `docs/stages/01-dashboard-spec/REPORT.md`.
5. Inspect `src/pbi_gen/models/dashboard_spec.py` in full.
6. Inspect representative Stage 01 tests in `tests/test_dashboard_spec.py`.
7. Inspect the archived/legacy designer implementation where useful, especially the prior LLM integration in `peter121512/pbi`, but treat it as evidence rather than an architecture to copy.

## Stage objective

Implement the first production-shaped **AI dashboard designer** that accepts natural-language dashboard requirements and produces a validated canonical `DashboardSpec`.

The designer must explicitly separate:

1. probabilistic reasoning performed by the LLM;
2. typed validation performed by Pydantic;
3. deterministic application logic, especially clarification gating and revision metadata handling.

This stage is the first real reasoning layer of the rebuilt engine. It should prove that a business prompt can become a coherent, analytically useful, visually intentional dashboard specification without uncontrolled prose being passed downstream.

## Core design principle

The designer should reason in approximately this order:

```text
User requirement
    ↓
Business objective and audience
    ↓
Analytical questions / decisions the report must support
    ↓
Metrics and dimensional breakdowns required
    ↓
Minimum viable semantic model
    ↓
Mock-data story required to make the analysis meaningful
    ↓
Page architecture and information hierarchy
    ↓
Visual choice and field bindings
    ↓
Filters / interactions / navigation
    ↓
Enterprise design-system intent
    ↓
Confidence evidence and assumptions
    ↓
Validated DashboardSpec
    ↓
Deterministic clarification decision
```

Do not design the system around “pick some charts from the user prompt”. The analytical problem must drive the report structure.

## Required capabilities

### 1. Natural-language design entry point

Create a clear public interface for generating a new dashboard specification from a prompt.

The interface should be simple enough for later CLI/API use, for example conceptually:

```python
design_dashboard(requirement: str, ...) -> DesignResult
```

The exact naming is an implementation decision.

The returned result must distinguish at minimum between:

- a usable validated `DashboardSpec`; and
- a clarification request that should be presented to the user before generation continues.

Do not represent this distinction by returning arbitrary prose or `None`.

### 2. LLM provider boundary

Introduce an explicit, narrow abstraction around the model call so the rest of the application does not depend directly on one vendor SDK.

Requirements:

- one concrete provider implementation is sufficient for this stage;
- prefer the provider already practical for the current project environment;
- configuration must come from environment/config, never committed secrets;
- provider/model selection must not leak throughout the domain logic;
- tests must be able to run without live model access;
- malformed or invalid model output must fail clearly.

Do not adopt a heavyweight agent framework merely to wrap a single structured model call.

### 3. Structured output into the canonical model

The LLM must be constrained or strongly instructed to produce output compatible with the Stage 01 `DashboardSpec` schema.

Prefer native structured-output / JSON-schema capabilities where supported. At the boundary, always validate through Pydantic before treating the result as trusted.

The designer must not silently coerce fundamentally invalid output into a plausible-looking dashboard.

If provider limitations require an intermediate model or response wrapper, keep it explicit and typed.

### 4. Analytical reasoning quality

The design prompt/instructions must cause the model to make a coherent chain of product decisions reflected in the structured output.

A good generated spec should:

- identify the business purpose and intended audience;
- derive the key analytical questions the report should answer;
- choose metrics that address those questions;
- define enough tables/columns/measures to support those metrics;
- choose page roles intentionally rather than creating a flat visual dump;
- create a strong executive overview first when the audience warrants it;
- use deeper diagnostic/detail pages only where they add decision value;
- choose visual types appropriate to the analytical task;
- use visual priority and position to create meaningful information hierarchy;
- include useful slicers/filters rather than decorative or redundant ones;
- specify interactions/drill-through/navigation where they genuinely help;
- create a coherent mock-data narrative with trends, variance, risks, targets, outliers or other meaningful patterns where appropriate;
- choose a consistent enterprise design-system intent across pages;
- avoid gratuitous chart variety, pie/donut overuse, gauges, visual clutter, excessive slicers, and other weak BI defaults unless analytically justified.

### 5. First-attempt completeness

The default behaviour should be to produce a **complete credible dashboard on the first attempt**, not an intentionally skeletal MVP specification.

For a sufficiently clear executive-dashboard request, the designer should normally infer:

- a sensible page architecture;
- the important KPIs;
- suitable comparative/trend views;
- the most useful dimensional breakdowns;
- a small set of decision-relevant filters;
- an appropriate design language;
- enough mock-data story to make the dashboard demonstrable.

Do not ask the user for choices such as “bar or line chart?”, exact colours, whether to include an obvious date filter, or other decisions a competent BI designer should make independently.

### 6. Deterministic clarification gate

Stage 01 deliberately modelled confidence as evidence rather than an arbitrary percentage. Implement deterministic logic that decides whether the designer should proceed or ask a clarification question.

The product behaviour should approximate this rule:

> Proceed autonomously unless there is a material ambiguity such that confidence in a major dashboard decision is below roughly 50%.

Do **not** implement a fake LLM-generated numeric confidence score.

Instead, derive the gate from structured evidence such as:

- unresolved open questions;
- `evidence_against` on high-impact confidence dimensions;
- critical assumptions whose being wrong would materially change metrics, model, page architecture or audience interpretation;
- missing/contradictory business context;
- ambiguous metric definitions where plausible interpretations produce materially different dashboards.

The gate should distinguish **material** ambiguity from routine design discretion.

Examples that should normally **not** trigger clarification:

- precise visual colour choices;
- exact page padding;
- bar vs. column where either is reasonable;
- whether a CEO overview should contain obvious core KPIs;
- a reasonable inferred reporting period for synthetic data when none was specified.

Examples that **may** trigger clarification:

- “margin” could mean gross margin, contribution margin or operating margin and the requested decision depends on the distinction;
- user asks for sales performance but gives contradictory geography/company context that fundamentally affects the report;
- a named KPI cannot be interpreted with reasonable domain confidence;
- two equally plausible business objectives would require substantially different report architectures.

When clarification is required, return **one compact, high-value question** wherever possible, not a questionnaire.

### 7. Confidence generated by reasoning, gate owned by code

The LLM should populate structured confidence evidence and assumptions as part of its design output.

However:

- the LLM must not have final authority over whether clarification is required;
- deterministic code must compute/override the final gate;
- if the Stage 01 `requires_clarification` field remains useful, deterministic code should populate or reconcile it after validation rather than trusting the model blindly.

Document the gate policy clearly enough that later stages can tune it without changing the designer prompt.

### 8. Stable identity for initial generation

A newly designed dashboard must receive valid revision metadata and stable page/visual IDs.

Initial generation must ensure:

- `version == 1`;
- no parent specification is required;
- page IDs are unique;
- visual IDs are unique within their page;
- the result can later become the parent of a conversational amendment.

Do not implement full conversational revision in this stage unless a very small shared abstraction is necessary. The next stage can own amendment semantics.

### 9. Validation beyond raw Pydantic shape

Add a deterministic semantic validation pass where useful for obvious cross-reference problems that Stage 01 intentionally left unresolved.

At minimum consider validating generated specs for:

- visual `FieldRef` references to tables/columns/measures that do not exist;
- drill-through/navigation targets that reference missing pages;
- tooltip page IDs that do not exist;
- impossible/out-of-bounds visual positions;
- obvious visual overlap if practical without building a full constraint solver;
- filters referencing missing fields;
- relationships referencing missing tables/columns.

Keep this validation focused on catching broken generated specifications. Do not turn the stage into a full Power BI semantic-model validator.

### 10. DesignResult / error contract

Introduce an explicit typed result/error boundary for designer execution.

The application should be able to tell the difference between:

- success: validated dashboard specification;
- clarification needed: compact question + relevant uncertainty context;
- provider failure;
- malformed/invalid structured output;
- semantic validation failure.

Exact classes/enums are an implementation decision, but callers should not need to infer state from exception strings.

### 11. Observability suitable for development

Provide enough structured diagnostics to understand why a design succeeded or failed without printing secrets or huge raw prompts by default.

Useful development metadata may include:

- provider/model used;
- validation errors;
- clarification dimensions triggered;
- high-level assumptions;
- optional raw-response capture behind an explicit debug mode if safe.

Do not build a telemetry platform in this stage.

## Prompt / reasoning guidance

The system instructions supplied to the LLM should establish the designer as an expert enterprise BI practitioner, not a chart autocomplete engine.

They should strongly encourage:

- analytical-first reasoning;
- C-suite information hierarchy when the audience is executive;
- restrained visual density;
- a small number of high-value visuals rather than dashboard wallpaper;
- comparison against target/prior period where meaningful;
- deliberate use of whitespace and grouping;
- consistency across pages;
- explicit analytical purpose for each visual;
- minimal but useful filters;
- coherent mock-data storytelling;
- accessibility descriptions;
- preservation of uncertainty as structured evidence rather than invented certainty.

Do not rely on a single phrase such as “make it beautiful” to deliver visual quality.

## Representative target scenarios

Tests / fixtures should exercise at least the following classes of request.

### Scenario A — Executive retail dashboard

> Create an executive retail performance dashboard for a UK retailer. The primary audience is the CEO and CFO. Show revenue, gross margin, YoY growth, regional performance, product/category performance and major underperformance risks. It should feel premium, restrained and boardroom-ready. Include useful filters for period, region and category.

Expected characteristics include a strong executive overview, trend/comparison context, diagnostic breakdowns, coherent semantic model, useful filters, and a meaningful data story.

### Scenario B — Sparse but inferable request

> I run a SaaS company. Build me a board dashboard showing whether growth is healthy.

The designer should infer sensible SaaS executive metrics and architecture without asking routine questions. Assumptions should be recorded.

### Scenario C — Material ambiguity

> Build a profitability dashboard focused on margin.

If the intended margin definition materially changes the dashboard and there is insufficient evidence to infer it, the clarification gate should be capable of asking a single targeted question.

Use deterministic fixtures/mocks for automated tests. Live-model smoke testing may be documented separately and must not be required for the normal test suite.

## Tests

Add meaningful automated tests covering at minimum:

1. successful design flow using a mocked provider and realistic structured model output;
2. Pydantic validation of model output;
3. semantic cross-reference validation;
4. malformed provider output producing a typed failure;
5. provider error producing a typed failure;
6. high-confidence/inferable prompt proceeding without clarification;
7. material ambiguity causing the deterministic clarification gate to trigger;
8. routine design uncertainty **not** causing clarification;
9. initial revision metadata being valid;
10. generated assumptions/confidence evidence being preserved in the spec;
11. no tests requiring external credentials or network access.

Prefer tests of domain behaviour over tests that assert giant prompt strings verbatim.

## Configuration

Add only the configuration needed for the chosen model provider.

Requirements:

- no secrets in Git;
- example configuration/env documentation may contain placeholders only;
- provider and model should be replaceable without rewriting designer/domain logic;
- sensible timeouts/retry behaviour may be added if the provider SDK requires it, but avoid elaborate resiliency infrastructure at this stage.

## Non-goals

Do NOT expand this stage into:

- PBIR/PBIP rendering;
- Fabric deployment changes;
- full synthetic-data generation rewrite;
- screenshot capture;
- vision-based dashboard critique;
- autonomous multi-agent frameworks;
- Android or web UI;
- persistence/database infrastructure;
- full conversational revision/amendment behaviour;
- semantic-model optimisation beyond what is needed for a credible mock-up;
- exhaustive support for every Power BI visual type.

The output of this stage is a high-quality validated `DashboardSpec` (or a justified clarification request), not a rendered dashboard yet.

## Architecture expectations

Prefer a small set of explicit components, conceptually similar to:

```text
Designer service
    ├── prompt/context builder
    ├── LLM provider adapter
    ├── structured DashboardSpec parsing
    ├── semantic spec validator
    └── deterministic clarification gate
```

Exact file/module names are implementation decisions.

The deterministic application layer should remain easy to unit test without an LLM.

## Learning objective

In `REPORT.md`, explain practically:

- why this is an “agentic” component even without a multi-agent framework;
- where probabilistic reasoning ends and deterministic code begins;
- why confidence evidence is more useful than asking the LLM for a confidence percentage;
- how structured output changes failure modes compared with parsing prose;
- how the provider boundary keeps the architecture model/vendor-independent;
- which parts of the designer are likely to evolve into separate critic/reviser roles later and which should remain deterministic functions.

## Acceptance criteria

The stage is complete when:

- a public natural-language dashboard-design entry point exists;
- at least one real LLM provider can be used through a narrow provider abstraction;
- normal automated tests require no live provider/network access;
- model output is validated into the canonical Stage 01 `DashboardSpec`;
- generated specs exhibit analytical-first reasoning rather than a flat chart list;
- a deterministic clarification gate exists and is covered by tests;
- routine ambiguity is inferred through while material ambiguity can produce one useful clarification question;
- obvious generated-spec cross-reference errors are caught deterministically;
- callers receive explicit typed success/clarification/failure outcomes;
- initial revision identity is correct and ready for later amendments;
- no secrets/environment-specific credentials are committed;
- existing Stage 01 tests remain passing;
- new Stage 02 tests pass;
- the implementation is committed and pushed;
- `docs/stages/02-ai-designer/REPORT.md` is created and committed.

## REPORT.md requirements

The report must include:

- implementation summary;
- files added/changed;
- final designer architecture;
- chosen provider and rationale;
- prompt/structured-output approach;
- clarification-gate algorithm and examples;
- semantic validation added;
- typed result/error model;
- tests run and results;
- any live-model smoke test performed, clearly separated from automated tests;
- assumptions and deviations;
- known limitations;
- recommended next stage;
- the agentic-learning explanation described above.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
