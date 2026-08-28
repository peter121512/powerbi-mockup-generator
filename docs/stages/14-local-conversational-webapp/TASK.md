# Stage 14 — Local Conversational Web App & Spreadsheet-to-Power-BI Demo

## Objective

Build a lightweight **local Node.js web application** that demonstrates the complete conversational dashboard-design workflow in a usable product shell.

The app must let a user:

1. describe the dashboard they want;
2. optionally upload one or more spreadsheets;
3. generate an initial OpenAI image mockup;
4. refine that mockup conversationally over multiple turns;
5. explicitly approve the design;
6. generate and deploy a real Power BI dashboard;
7. use uploaded spreadsheet data where available, or synthesize realistic data where no source data was provided;
8. when synthetic data is used, emit a developer-facing semantic-model contract describing what real data must later be connected.

This is the first usable end-to-end product shell. It is a demo harness, not the final production web/mobile experience.

---

## Core Principle

**Node.js is the application shell, not a rewrite of the Python generator.**

Preserve the existing Python design, ingestion, mockup, semantic-model, rendering and Fabric deployment capabilities wherever practical.

The Node app should invoke the Python engine through a thin boundary such as:

- local HTTP API,
- child process / CLI bridge,
- or another clean IPC mechanism.

Do not duplicate mature Python logic in JavaScript merely to keep everything in one runtime.

The architectural split should be clear:

```text
Node.js web app
  ↓
conversation/session API
  ↓
Python dashboard engine
  ├─ DataContext / spreadsheet profiler
  ├─ OpenAI mockup generation
  ├─ DashboardDesignSession
  ├─ feasibility classification
  ├─ semantic-model generation
  ├─ Power BI renderer
  └─ persistent Fabric deployment
```

---

## User Experience

Keep the app intentionally lightweight and fast to run locally.

A recommended layout is:

- **left/centre conversation panel**
  - chat history
  - text input
  - attachment control
  - approval/build action
- **right mockup panel**
  - current dashboard mockup image
  - revision state
  - feasibility/template notes where useful
- **build/deployment state**
  - progress indicator
  - semantic-model summary
  - Power BI report URL / embed when complete
  - downloadable/viewable semantic-model contract when synthetic data is used

The app should feel like collaborating with a Power BI designer, not operating a form wizard.

Do not require the user to define all KPIs, dimensions, measures or visuals before producing a first mockup.

---

## Required Conversation Flow

### 1. Start

User can begin with natural language such as:

> "Build me a CFO dashboard showing revenue, gross margin, EBITDA and cash performance."

The app creates a persistent design session and either:

- generates the first mockup immediately when confidence is adequate, or
- asks focused clarification questions when ambiguity materially affects the design.

### 2. Optional data upload

User may upload spreadsheets before or during the conversation.

Support at minimum:

- `.xlsx`
- `.csv`

Uploaded files must be profiled into the existing provider-neutral `DataContext` representation.

Multiple files and multi-sheet workbooks should be supported.

Show a compact summary to the user, for example:

> 3 sheets detected · 42 fields · 6 likely measures · 9 likely dimensions

Do not dump raw data into the chat UI.

### 3. Initial mockup

Generate the first OpenAI image mockup using Stage 13 capabilities.

The mockup should:

- be grounded in the user's stated business goal;
- use uploaded spreadsheet structure where supplied;
- begin loosely from proven Power BI template patterns where compatible with the user's request;
- remain credible for Power BI implementation;
- permit later deviations into native/custom visual requirements.

### 4. Conversational refinement

User can send instructions such as:

- "make it more executive"
- "replace the bottom left bar chart with a waterfall"
- "move the filters to the top right"
- "make the KPI cards smaller"
- "use teal rather than blue"
- "show cash conversion as a bespoke radial visual"

Each turn must update the existing `DashboardDesignSession`, not start a new design.

Generate an amended image mockup that preserves unchanged elements wherever possible.

### 5. Approval gate

Power BI generation must not begin until the user explicitly approves the current mockup.

Examples:

- "approved"
- "build it"
- "go ahead"
- "create the Power BI version"

On approval:

- freeze the approved mockup revision;
- create/finalise `DashboardDesignSpec`;
- resolve the data path;
- generate the semantic model;
- build and deploy the actual report.

---

## Data Path A — Uploaded Spreadsheet Data

When spreadsheets are supplied, the real Power BI dashboard should be driven by those spreadsheets rather than the existing demo semantic model.

### Required behaviour

The system must derive a practical semantic model from the uploaded data sufficient to render the approved dashboard.

At minimum determine:

- source sheets/files;
- table/entity candidates;
- likely facts/dimensions;
- data types;
- candidate keys;
- relationships where inferable;
- table grain;
- date field(s);
- measures required by the approved design;
- any necessary derived columns or transformations;
- formatting metadata.

The goal for Stage 14 is not enterprise-perfect modelling, but it must be genuinely driven by the unseen workbook and not pre-wired to known schemas.

### Validation

Before deployment, perform deterministic checks where practical:

- referenced fields exist;
- relationship keys are compatible;
- candidate dimension keys are sufficiently unique;
- required numeric measures have valid source fields;
- no measure silently uses a field absent from the uploaded data;
- the approved visuals can bind to the generated model.

Where ambiguity cannot be safely resolved, ask a focused question rather than inventing business logic.

### Build

Generate the required Power BI semantic model/TMDL and report definition, then deploy through the Stage 12B persistent deployment path.

The report must render real data from the uploaded workbook-derived model.

---

## Data Path B — No Data Supplied / Synthetic Data

If the user approves a dashboard without supplying data, the system must synthesize a coherent dataset that supports the approved dashboard.

Synthetic data must be consistent across tables and metrics rather than arbitrary independent values.

For example, if the approved dashboard includes:

- revenue,
- gross profit,
- margin %, 
- products,
- customers,
- regions,
- monthly trend,

then generated rows must obey basic consistency such as:

```text
gross_profit = revenue - cost
margin_pct = gross_profit / revenue
```

and dimensions/keys must join correctly.

### Synthetic semantic model

Generate a proper semantic model for the synthetic dataset and deploy the Power BI dashboard using it.

### Mandatory developer contract

When synthetic data is used, generate a developer-facing text artifact:

`SEMANTIC_MODEL_CONTRACT.md`

This must be detailed enough that another Power BI/data developer can understand what real data must later replace the synthetic source.

Include at minimum:

#### Model overview

- model purpose
- dashboard/page purpose
- required business subject areas

#### Tables

For every table:

- table name
- business purpose
- expected grain
- source role (`fact`, `dimension`, `bridge`, `reference`, etc.)

#### Columns

For every required column:

- table
- column name
- expected data type
- nullable/not-null expectation where important
- semantic role
- sample meaning / accepted values where useful
- key status

#### Relationships

For every relationship:

- from table/column
- to table/column
- cardinality
- filter direction
- active/inactive expectation
- why the relationship exists

#### Measures

For every dashboard measure:

- display name
- intended DAX
- business definition
- dependent columns/tables
- format string
- caveats / assumptions

#### Date behaviour

- required date table
- date range expectations
- fiscal-calendar assumptions if any
- which date drives which metric where relevant

#### Transformations

- required calculations
- derived columns
- cleansing/normalisation expectations
- currency/unit conversions where applicable

#### Visual bindings

For every approved visual/KPI:

- visual title
- required measures
- required dimensions
- filters/slicers
- sort logic
- implementation class/template/custom visual requirement

#### Replacement guidance

A short practical section explaining what a developer must do to replace the synthetic source with real data while preserving the report.

The contract must reflect the **actual generated synthetic model**, not a generic template document.

---

## Power BI Feasibility Rules

Carry forward Stage 13's feasibility model.

Every approved visual must be classified as one of:

- `EXISTING_TEMPLATE`
- `NATIVE_POWERBI`
- `CUSTOM_VISUAL_REQUIRED`
- `NEEDS_REDESIGN`

Initial mockups should bias toward existing proven templates where compatible with user intent.

Do not force user-requested deviations back into the standard template library merely because those templates are convenient.

A valid deviation should produce or preserve a structured `CustomVisualRequirement`.

For Stage 14, if a required custom visual cannot yet be generated automatically:

- retain the requirement explicitly;
- use a clearly reported closest-supported placeholder in the deployed demo only when necessary;
- do not silently pretend the placeholder is an exact implementation.

`NEEDS_REDESIGN` elements must block build unless the user accepts an alternative.

---

## Node.js App Requirements

Use a current supported Node.js LTS version.

Keep dependencies modest.

Acceptable choices include:

- Express/Fastify for server API;
- lightweight React/Vite frontend, or server-rendered HTML if sufficient;
- WebSocket/SSE or polling for long-running generation/deployment status.

Do not introduce a large platform framework unless it materially simplifies the demo.

### Minimum local commands

A developer should be able to run something broadly equivalent to:

```bash
npm install
npm run dev
```

and open the app locally.

If the Python engine needs a separate process, provide a single convenience command such as:

```bash
npm run dev:all
```

or equivalent.

Document environment variables required for:

- OpenAI image generation;
- Fabric/Power BI deployment;
- any local runtime configuration.

Never commit secrets.

---

## Session / API Behaviour

Expose a clean application contract between the Node UI and the Python engine.

Suggested operations:

```text
POST /api/sessions
POST /api/sessions/:id/message
POST /api/sessions/:id/files
GET  /api/sessions/:id
GET  /api/sessions/:id/mockup
POST /api/sessions/:id/approve
GET  /api/sessions/:id/build-status
GET  /api/sessions/:id/semantic-model-contract
```

Exact routes are not mandatory, but the responsibilities must be separated cleanly.

Long-running image generation / report deployment must not freeze the browser UI.

Return useful progress states such as:

```text
profiling_data
creating_mockup
waiting_for_user
approved
building_semantic_model
building_report
deploying
complete
failed
```

Errors should surface intelligibly in the UI.

---

## Persistence

For this stage, lightweight local persistence is sufficient.

At minimum, a session should survive page refreshes during one local demo run.

Use a simple local store such as:

- JSON files,
- SQLite,
- or another lightweight mechanism.

Do not introduce enterprise infrastructure.

Persist at least:

- conversation turns;
- uploaded-file references;
- `DataContext`;
- mockup revisions;
- current/approved design spec;
- build state;
- report ID/URL;
- generated semantic-model contract where applicable.

---

## Fresh-Data Acceptance Rule

The implementation must not be validated solely against a workbook or schema known during development.

At least one acceptance run must use a **previously unseen workbook** introduced only at test time.

The system must not contain hard-coded field names or mappings specific to the acceptance workbook.

The test report should explicitly list:

- what the system inferred;
- what questions it asked;
- what model it generated;
- what it got right/wrong.

---

## Required End-to-End Acceptance Scenarios

### Scenario A — Unseen Spreadsheet

Use a previously unseen multi-sheet workbook supplied only for acceptance testing.

Required journey:

1. launch local Node app;
2. start conversation with dashboard request;
3. upload workbook;
4. app profiles workbook;
5. OpenAI image mockup generated;
6. user performs at least **two natural-language refinements**;
7. user approves;
8. system derives semantic model from workbook;
9. real Power BI report generated;
10. report deployed through persistent Stage 12B path;
11. deployed report screenshot captured;
12. verify visible values come from the uploaded workbook-derived dataset.

A PASS requires no pre-authored mapping for that workbook.

### Scenario B — No Data / Synthetic

Required journey:

1. launch fresh session with natural-language dashboard request;
2. provide no spreadsheet;
3. generate first OpenAI mockup;
4. perform at least two refinements;
5. approve;
6. generate internally consistent synthetic data;
7. generate semantic model;
8. build/deploy Power BI dashboard;
9. capture deployed screenshot;
10. generate `SEMANTIC_MODEL_CONTRACT.md`;
11. verify the contract exactly describes the model actually used by the report.

### Scenario C — Session Continuity

- create session;
- upload data;
- generate mockup;
- refresh/reload the browser;
- continue conversation;
- confirm state and current image are preserved.

### Scenario D — Feasibility Deviation

Request a reasonable visual not currently in the template library.

Expected:

- mockup retains user intent;
- visual becomes `CUSTOM_VISUAL_REQUIRED`;
- requirement survives approval;
- build output clearly reports whether a placeholder was required.

### Scenario E — Invalid/Impossible Request

Request something Power BI cannot credibly deliver, e.g. an interactive 3D physics simulation as a report visual.

Expected:

- `NEEDS_REDESIGN`;
- app explains the limitation conversationally;
- approval/build is blocked until a feasible alternative is chosen.

---

## Visual Quality

The local web app itself should be polished enough for a stakeholder demo but should not consume the majority of the stage.

Target:

- clean dark/light neutral UI;
- professional typography;
- clear mockup emphasis;
- responsive enough for a laptop browser;
- no default scaffold branding;
- no developer-debug appearance in the main user flow.

The Power BI mockup image and resulting Power BI report remain the hero artifacts.

---

## Security / File Handling

- never expose OpenAI/Fabric secrets to browser JavaScript;
- all secret-bearing calls occur server-side;
- validate file extensions and reasonable size limits;
- use per-session temporary/upload directories;
- prevent path traversal;
- do not execute uploaded spreadsheet content;
- clean up temporary artifacts where practical.

---

## Regression Requirements

Stage 14 must not regress the accepted systems from previous stages.

At minimum rerun:

- Stage 12A tests;
- Stage 12B tests;
- Stage 13 tests;
- full repository test suite.

The Node app must use the persistent `DeploymentService`; do not reintroduce delete/create deployment.

---

## Evaluation

### A. Local product experience — /20

- coherent conversational UI
- attachments work
- current mockup visible
- status/progress understandable
- refresh/session continuity

### B. Conversational design workflow — /20

- OpenAI image mockup works
- multi-turn refinement works
- unchanged decisions are preserved
- approval gate works
- feasibility deviations survive

### C. Spreadsheet-to-Power-BI path — /25

- unseen workbook is profiled
- semantic model derives from real workbook
- approved dashboard binds to that model
- deployed values genuinely derive from workbook data
- no acceptance-specific hard-coded mappings

### D. Synthetic-data path + model contract — /20

- synthetic data internally coherent
- generated model supports approved dashboard
- report deploys
- semantic-model contract is complete and accurate
- developer could plausibly use contract to substitute a real source

### E. Architecture / regression — /15

- Node stays a thin product shell
- Python capabilities reused
- secrets safe
- persistent deployment preserved
- prior tests remain green

Target: **>=85/100** overall, with no hard acceptance failure.

---

## Hard Acceptance Criteria

Stage 14 passes only if all are true:

- A lightweight local Node.js web app runs successfully.
- User can converse naturally with the app.
- `.xlsx` and `.csv` uploads work.
- Uploaded spreadsheets update the design `DataContext`.
- OpenAI image generation produces the initial mockup.
- At least two conversational refinements can be performed in the UI.
- Session state survives browser refresh during the demo.
- No Power BI artifact is built before explicit approval.
- Approved spreadsheet-backed session generates a real semantic model from an unseen workbook.
- Approved spreadsheet-backed session deploys a working Power BI report using data derived from that workbook.
- Approved no-data session generates coherent synthetic data and a corresponding semantic model.
- Synthetic session deploys a working Power BI report.
- Synthetic session produces `SEMANTIC_MODEL_CONTRACT.md` describing the actual generated model.
- Every approved visual is feasibility-classified.
- `CUSTOM_VISUAL_REQUIRED` deviations are preserved rather than silently discarded.
- `NEEDS_REDESIGN` blocks deployment until resolved.
- Deployment uses Stage 12B create-or-update behaviour.
- Stage 12A/12B/13 regression tests remain green.

---

## Deliverables

Create at minimum:

- local Node.js web app;
- package scripts for simple local startup;
- conversation UI;
- spreadsheet upload UI;
- current/revision mockup viewer;
- session persistence;
- Node ↔ Python engine boundary;
- async progress/status handling;
- spreadsheet-backed semantic model generation path;
- synthetic data generator;
- synthetic semantic model generator;
- `SEMANTIC_MODEL_CONTRACT.md` generator;
- Power BI build/deployment handoff;
- automated Node/API tests where appropriate;
- Python tests for new model/data logic;
- end-to-end browser evidence;
- screenshots of both acceptance journeys;
- generated contract evidence;
- `docs/stages/14-local-conversational-webapp/REPORT.md`.

The REPORT must distinguish deterministic automated evidence from developer/self-assessment.

---

## Out of Scope

Do not turn this stage into the full enterprise data-source discovery project.

Defer:

- SQL Server estate discovery/search;
- MySQL connector;
- Fabric Parquet/OneLake catalogue discovery;
- Fabric DB/Warehouse connector;
- enterprise-scale relationship inference;
- Bedrock Nova reasoner implementation;
- fully automated custom-visual factory;
- Android app;
- production auth/multi-tenancy/cloud hosting.

The app should be architected so those capabilities can slot in later.

---

## Conclusion Values

`REPORT.md` must end with one of:

- `PASS`
- `PARTIAL_PASS`
- `FAIL`

A `PASS` requires successful live evidence for both the unseen-spreadsheet path and the no-data synthetic path.