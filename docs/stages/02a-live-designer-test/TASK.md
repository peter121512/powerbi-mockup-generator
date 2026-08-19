---
stage: 02a
status: ready
title: Live AI designer integration test
---

# Stage 02a — Live AI Designer Integration Test

## Purpose

Stage 02 implemented the AI dashboard designer and passed its mocked automated test suite, but no live-model smoke test was performed. Before moving on to conversational revision or downstream generation, prove that the real designer works against the configured Amazon Bedrock model and inspect the quality of the resulting `DashboardSpec`.

This is a short integration/testing stage. Do not broaden it into Stage 03.

## Read first

1. Read `KIRO.md`.
2. Read `docs/stages/02-ai-designer/TASK.md` and `REPORT.md`.
3. Inspect the actual Stage 02 implementation, especially `designer/provider.py`, `designer/prompt.py`, `designer/service.py`, `designer/validator.py`, and `designer/clarification.py`.
4. Confirm the current Bedrock model ID and region from the implementation/config before testing.

## Objective

Run the rebuilt designer against a **real Bedrock model call**, using existing locally configured AWS credentials, and determine whether the output is genuinely useful as an enterprise Power BI dashboard specification.

The goal is not merely to prove that the API returns HTTP 200. Assess whether the generated spec demonstrates the analytical-first and enterprise-design behaviour required by Stage 02.

## Test scenario

Use this primary prompt verbatim unless a technical constraint requires a trivial formatting change:

> Create an executive retail performance dashboard for a UK retailer. The primary audience is the CEO and CFO. Show revenue, gross margin, YoY growth, regional performance, product/category performance and major underperformance risks. It should feel premium, restrained and boardroom-ready. Include useful filters for period, region and category.

## Required work

1. Verify that the live provider can authenticate and invoke the configured Bedrock model.
2. Execute the full public designer path rather than calling the provider adapter in isolation.
3. Capture the resulting `DesignOutcome`.
4. If successful, persist the generated `DashboardSpec` as a JSON test artefact under this stage directory, e.g. `LIVE_OUTPUT.json`, with no credentials or sensitive environment data.
5. Review the generated spec for:
   - coherent business purpose and audience;
   - useful analytical questions;
   - sensible KPIs/measures;
   - credible semantic-model structure;
   - coherent mock-data narrative;
   - page architecture appropriate for CEO/CFO use;
   - appropriate visual types for the analytical tasks;
   - visual hierarchy/layout intent;
   - useful filters/interactions;
   - restrained, enterprise-grade design-system intent;
   - confidence evidence and assumptions;
   - absence of broken field/page references;
   - whether the deterministic clarification gate proceeds as expected for this clear prompt.
6. Run the complete automated test suite after any fixes.

## Fix policy

If the live test exposes a **small, clearly Stage-02-scoped integration defect**, fix it in this stage. Examples include:

- incorrect Bedrock request/response handling;
- wrong model identifier or provider configuration behaviour;
- structured JSON extraction failure;
- prompt/schema incompatibility;
- deterministic validator incorrectly rejecting a valid generated spec;
- obvious prompt defects causing structurally unusable output.

Do not use this stage to redesign the architecture or add unrelated capabilities. Record larger quality improvements as recommended future work.

If AWS credentials, Bedrock access, or model permissions are unavailable, do not fake a successful test. Record the exact blocker in `REPORT.md` and stop without inventing results.

## Quality assessment

The report must distinguish **technical integration success** from **design-quality success**.

Rate the live result qualitatively against these dimensions:

- analytical coherence;
- executive usefulness;
- visual-choice appropriateness;
- layout/information hierarchy;
- filters/interactions;
- enterprise aesthetic intent;
- mock-data story;
- structural validity.

Use concrete evidence from the generated spec. Do not claim C-suite quality merely because the JSON validates.

## Acceptance criteria

Stage 02a is complete when:

- a real Bedrock call has been attempted through the public designer path;
- the actual outcome is documented truthfully;
- if successful, the generated `DashboardSpec` is committed as a non-sensitive JSON artefact;
- the output has been reviewed against the Stage 02 product-quality criteria;
- any small integration defects discovered have been fixed and tested, or clearly documented if blocked;
- the complete automated test suite passes after changes;
- `docs/stages/02a-live-designer-test/REPORT.md` is created;
- all intended changes and test artefacts are committed and pushed.

## REPORT.md requirements

Include:

- exact test performed;
- provider/model/region used (no credentials);
- technical outcome;
- `DesignOutcome`;
- elapsed time if readily available;
- generated artefact path if successful;
- concise description of the generated dashboard architecture;
- quality assessment by the dimensions above;
- clarification-gate result;
- defects found and fixes made;
- full automated test result;
- known limitations;
- recommendation on whether the project is ready to proceed to the next stage.

Do not edit this `TASK.md` to mark completion. The report is the completion record.
