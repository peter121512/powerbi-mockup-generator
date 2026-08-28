# Stage 13 — Conversational Image-First Dashboard Mockup Workflow

## Objective

Introduce a conversational design workflow that sits before real Power BI generation.

The user should be able to describe a dashboard goal, provide data context through files/links/descriptions, iterate through OpenAI-generated dashboard images in a back-and-forth conversation, approve a visual direction, and only then trigger generation of the actual Power BI dashboard.

This stage is about reducing the cost and friction of design iteration before expensive/report-building work begins.

---

## Core User Journey

1. User describes the dashboard they want in natural language.
2. System asks only for information materially needed to create a credible mockup.
3. User may provide one or more of:
   - uploaded spreadsheet files (CSV/XLSX initially),
   - online-accessible files/URLs,
   - written descriptions of the data,
   - screenshots/reference images,
   - business goals / audience / KPIs / preferred style.
4. System extracts enough structure from the supplied context to understand likely dimensions, measures, time fields, and dashboard intent.
5. System creates an **image mockup using OpenAI image generation** before building any Power BI report artifact.
6. User can respond conversationally with changes such as:
   - "make the KPI row smaller"
   - "use a donut for margin mix"
   - "move the filters to the top right"
   - "make it more executive"
   - "replace this chart with a trend"
   - "use these colours instead"
7. System generates an amended image mockup while preserving unchanged aspects of the previous design.
8. Iteration continues until the user explicitly approves the mockup.
9. Approved mockup is converted into a structured dashboard specification.
10. The existing Power BI generation/deployment pipeline then creates the real dashboard based on the approved design.

The image mockup phase and Power BI generation phase must be clearly distinct states.

---

## Design Principle

**Design cheaply, build expensively.**

Do not create or deploy Power BI artifacts during exploratory visual iteration unless the user explicitly requests it.

Image generation is the fast design loop. Power BI generation begins only after explicit approval.

---

## Conversation State

Create a reusable conversation/session model, for example `DashboardDesignSession`, containing at minimum:

- session id
- original user request
- conversation history relevant to design
- supplied files / URLs / data descriptions
- extracted data summary
- inferred measures/dimensions
- design preferences
- current mockup revision
- prior mockup revisions
- structured page spec draft
- approval state
- confidence / unresolved assumptions

The session must support incremental amendment rather than treating every user message as a brand-new dashboard.

A revision should preserve previously approved/inferred decisions unless the user changes them.

---

## Input Mechanisms

### 1. Uploaded spreadsheet files

Support at least:

- `.xlsx`
- `.csv`

For each uploaded file, extract a lightweight data profile sufficient for dashboard design:

- sheet/table names
- column names
- inferred types
- row count where practical
- sample values
- likely date fields
- likely numeric measures
- likely categorical dimensions

Do **not** require a complete semantic model during the image-mockup phase.

The purpose is to make visual suggestions plausible and grounded in the user's actual data.

### 2. Online files / URLs

Provide an input abstraction for externally hosted files.

At minimum, architect the workflow so a URL/file reference can be resolved into the same internal `DataContext` shape used for uploads.

Implementation may initially support a limited subset of publicly/directly accessible files, but the abstraction must not assume local upload only.

Future connectors must be able to plug into this same path.

### 3. User-written descriptions

The workflow must work when the user has no file ready.

Example:

> "I have invoice-level finance data with customer, product, region, invoice date, revenue, cost, budget and currency. I want a CFO dashboard."

The system should infer enough to propose a design, clearly marking assumptions.

---

## Data Context Artifact

Create a provider-neutral structured artifact, e.g. `DataContext`, that can be produced from uploads, URLs, or descriptions.

Suggested structure:

```json
{
  "sources": [],
  "entities": [],
  "fields": [],
  "candidate_measures": [],
  "candidate_dimensions": [],
  "date_fields": [],
  "relationships": [],
  "assumptions": [],
  "confidence": 0.0
}
```

The image-generation prompt must use this artifact rather than raw spreadsheet dumps.

Do not send large raw datasets to the image model.

---

## OpenAI Image Mockup Generation

Add a first-class image mockup service.

Suggested interface:

```python
class DashboardMockupService:
    def create_mockup(self, session: DashboardDesignSession) -> MockupRevision: ...
    def revise_mockup(self, session: DashboardDesignSession, user_instruction: str) -> MockupRevision: ...
```

The service should generate dashboard imagery through OpenAI image generation.

The generated image prompt should be assembled from:

- business request
- intended audience
- DataContext
- inferred KPIs
- visual hierarchy
- current design choices
- existing accepted Power BI visual style
- prior mockup / amendment instruction where relevant

The system should strongly bias toward designs that the current Power BI renderer can plausibly reproduce.

Do not deliberately produce impossible designs just because the image model can draw them.

---

## Template-Aware Image Mockups

The image phase should be visually creative but constrained by real implementation capability.

Use `docs/TEMPLATE_INVENTORY.md` as the capability boundary for implementation-aware mockups.

For each proposed visual in the mockup, maintain a provisional mapping to the closest existing template where possible.

Example:

```json
{
  "intent": "monthly revenue trend",
  "mockup_visual": "line chart",
  "candidate_template": "premium_trend",
  "confidence": 0.96
}
```

A mockup may contain a design element not exactly supported by the current inventory, but this must be flagged as a likely template gap rather than silently promised.

The user should be able to approve a design while knowing which elements are exact matches versus approximations.

---

## Conversational Revision Behaviour

When a user requests a change, amend the existing mockup rather than regenerating a concept from scratch.

For each revision:

1. Parse what changed.
2. Preserve unchanged requirements.
3. Update the structured design state.
4. Generate a new image based on the prior approved/current state.
5. Record the revision and delta.

Examples:

- "make all KPI cards the same width" -> change layout only.
- "switch gross margin from bar to donut" -> change one visual only.
- "use teal instead of purple" -> update colour tokens only.
- "add a regional filter" -> add filter control; leave all other visuals intact.

Avoid unnecessary design drift between revisions.

---

## Approval Gate

The system must not automatically move from image mockup to Power BI artifact generation.

Require an explicit approval intent such as:

- "approved"
- "build it"
- "create the Power BI version"
- "go ahead with this"

On approval:

1. freeze the approved image revision;
2. create a structured `DashboardDesignSpec`;
3. map mockup elements to existing templates;
4. classify any unsupported elements as `TEMPLATE_LIMITATION`;
5. pass the spec to the existing renderer/build/deployment pipeline.

---

## DashboardDesignSpec

The approved design must become a structured artifact rather than relying on the image alone.

Suggested fields:

- page title/subtitle
- target resolution/aspect ratio
- navigation layout
- slicers / filters
- KPI cards
- visual list
- visual types/templates
- x/y/w/h geometry
- titles
- metric/dimension intent
- design tokens / palette
- typography
- annotation/insight regions
- mockup revision id
- source DataContext id
- assumptions
- template gaps

The actual Power BI renderer should consume this spec.

The image is evidence/reference; it must not be the sole build instruction.

---

## Power BI Build Handoff

Once approved, the workflow should reuse the existing Stage 12A/12B architecture:

- shared visual templates
- parameterised colours
- standard headers
- responsive donut composite logic
- functional navigation
- persistent `DeploymentService`
- stable report ID / URL for updates

If an approved mockup is revised after deployment, treat it as an amendment to the same logical report and update it in place.

Do not revert to delete/create deployment.

---

## User Experience Requirements

The system should feel like collaborating with a Power BI designer, not filling out a rigid wizard.

It should:

- infer aggressively where confidence is high;
- ask focused questions only when ambiguity materially affects the design;
- allow the user to provide files at any point in the conversation;
- allow design changes in plain English;
- preserve context between turns;
- make it clear when the user is viewing an image concept versus a deployed Power BI report;
- show/record assumptions where the data context is incomplete.

Do not require users to define every measure, chart, or table before generating the first image.

---

## Confidence Behaviour

Use the existing project philosophy:

- high confidence -> infer and continue;
- moderate confidence -> infer but record assumption;
- low confidence on a decision that materially affects the design -> ask the user.

As a guide, if overall design/data-context confidence is below ~50% for the initial request, ask one or more targeted questions before generating the first mockup.

Do not ask questions merely because information is absent if a reasonable visual assumption can be made safely.

---

## Required Test Scenarios

### Scenario A — Description only

Input:

> "I have SaaS subscription data with customer, plan, ARR, MRR, churn date, region and sales owner. Build me an executive retention dashboard."

Expected:

- DataContext inferred from text;
- image mockup generated;
- sensible KPIs and visuals proposed;
- assumptions recorded;
- user amendment produces a revised image without design drift.

### Scenario B — Spreadsheet upload

Use a representative multi-sheet workbook.

Expected:

- workbook profiled;
- fields reflected in DataContext;
- mockup recommendations grounded in actual columns;
- no fake measures that contradict available data.

### Scenario C — Online file

Resolve at least one supported URL/file source into DataContext and generate a mockup from it.

### Scenario D — Multi-turn revision

Run at least 4 revisions:

1. initial mockup
2. change visual type
3. change colours
4. move filters/layout
5. approval

Verify unchanged elements remain stable.

### Scenario E — Approved mockup to real Power BI

- approve the mockup;
- create DashboardDesignSpec;
- generate actual Power BI report using existing templates;
- deploy via persistent update path;
- capture screenshot;
- compare actual report against approved mockup.

---

## Evaluation

### A. Conversational workflow — /25

- back-and-forth state preserved
- revisions are incremental
- approval gate works
- focused clarification behaviour

### B. Data grounding — /20

- uploaded/linked/described data becomes structured DataContext
- mockup reflects actual available fields
- assumptions/confidence handled correctly

### C. Image mockup quality — /20

- professional executive-grade appearance
- strong visual hierarchy
- appropriate visual types
- coherent layout/theme

### D. Template feasibility — /15

- mockup mostly reproducible using existing template inventory
- gaps explicitly classified
- no impossible capability silently promised

### E. Approved mockup -> Power BI fidelity — /20

Evaluate actual deployed report against the approved design for:

- information hierarchy
- page geometry
- visual selection
- colour/theme
- headers/KPIs/navigation
- overall visual character

Target: >=80/100 overall.

---

## Hard Acceptance Criteria

Stage 13 passes only if all are true:

- User can start from natural-language dashboard intent.
- At least spreadsheet upload, URL/file abstraction, and description-based context are implemented.
- OpenAI image generation is used for the initial visual mockup phase.
- Multiple conversational revisions preserve state and previous decisions.
- No Power BI artifact is built before explicit user approval.
- Approval produces a structured DashboardDesignSpec.
- DashboardDesignSpec maps proposed visuals to existing template capabilities.
- Approved design can be turned into an actual Power BI report.
- Actual report uses the persistent Stage 12B deployment path.
- Actual-vs-approved mockup comparison is captured and reported.
- Existing Stage 12A/12B tests continue to pass.

---

## Deliverables

Create at minimum:

- conversational/session domain model
- DataContext abstraction
- spreadsheet profiler
- URL/file resolver abstraction
- mockup image service
- OpenAI image-generation adapter
- revision/delta handling
- DashboardDesignSpec
- template-feasibility mapper
- approval/build handoff
- automated tests
- end-to-end evidence
- `docs/stages/13-conversational-image-mockup-workflow/REPORT.md`

Include generated mockup revisions and the final deployed screenshot as evidence where practical.

---

## Out of Scope for Stage 13

Do not turn this stage into the full enterprise data-source discovery project.

Specifically defer:

- SQL Server deep schema search/discovery
- MySQL connector
- Fabric Parquet catalogue search
- Fabric DB/Warehouse connector
- large-scale relationship/grain inference across enterprise schemas
- full greenfield semantic-model generation from complex source systems
- Bedrock Nova reasoner implementation
- automated custom-visual generation
- Android application

Those remain later stages.

---

## Conclusion Values

REPORT.md must end with one of:

- `PASS`
- `PARTIAL_PASS`
- `FAIL`

A `PASS` requires a demonstrated conversation from user context -> OpenAI image mockup -> multiple revisions -> explicit approval -> structured design spec -> actual Power BI report -> persistent deployment.