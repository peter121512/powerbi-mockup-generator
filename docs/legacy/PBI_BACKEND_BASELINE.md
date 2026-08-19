# Legacy `peter121512/pbi` Backend Baseline

Source repository: `peter121512/pbi`
Source commit/tree reviewed: `8d24ebcca5e4ecbdd09bef7df25bf4a0f70b395a`

This repository contains the backend implementation that was missing from the original Android prototype. It proves that the project can generate Power BI Project (PBIP) artifacts and deploy them to Power BI/Fabric.

## Reusable architecture

The legacy backend implements this working loop:

1. Natural-language prompt through a conversational CLI.
2. Bedrock LLM converts the prompt into a `DashboardSpec`.
3. Synthetic SQLite data is generated to support the planned visuals.
4. PBIP/TMDL/PBIR project files are generated.
5. `fabric-cicd` publishes SemanticModel and Report items to a configured Fabric/Power BI workspace.
6. The deployed dataset is refreshed through the Power BI REST API.
7. The deployed report can be embedded headlessly through the Power BI JavaScript client and screenshotted with Playwright.
8. A vision-capable Bedrock model critiques the screenshot.
9. Failed deployment or visual-validation feedback can be returned to the LLM for automatic correction and redeployment.
10. CLI follow-up prompts amend the existing dashboard specification rather than starting from scratch.

## Artifacts to retain

### Active baseline already copied into this repository

- `pyproject.toml` — Python package/dependency baseline.
- `config.example.yaml` — Fabric workspace/authentication configuration template.
- `src/pbi_gen/models/schema.py` — first-generation dashboard specification types.
- `src/pbi_gen/deploy/fabric.py` — Fabric deployment and Power BI dataset-refresh pipeline.

### Legacy source to treat as reference during the Phase 1 rebuild

- `src/pbi_gen/core/cli.py` — conversational CLI, refinement state, auto-redeploy and retry orchestration.
- `src/pbi_gen/llm/bedrock.py` — Bedrock conversation and full-spec refinement pattern.
- `src/pbi_gen/db/sqlite_gen.py` — visual-aware synthetic-data generation.
- `src/pbi_gen/templates/pbip.py` — PBIP/TMDL/PBIR report and semantic-model generator, including visual JSON, layout and theme generation.
- `src/pbi_gen/validate/screenshot.py` — Power BI embed-token + Playwright screenshot pipeline.
- `src/pbi_gen/validate/vision.py` — screenshot QA via Bedrock vision.
- `tests/test_sqlite_gen.py` and `tests/test_ambiguous_relationships.py` — useful regression tests for data generation and relationship handling.

## What should not be carried forward unchanged

The old implementation is a baseline, not the target architecture. In particular:

- The `DashboardSpec` is too shallow for the required enterprise-grade design system.
- The LLM prompt couples requirements, model design and visual design too tightly.
- Confidence/clarification is informal rather than derived from explicit uncertainty criteria.
- Synthetic data is visual-aware but still heuristic and not driven by a coherent business narrative.
- The report generator has one principal layout/style system and limited page/navigation/interactivity semantics.
- Visual selection quality is mostly prompt-rule driven rather than a dedicated analytical design decision.
- Vision QA checks successful rendering and basic appeal, but the quality rubric is far below the C-suite-demo standard required for Phase 1.

## Phase 1 principle

Do not rebuild deployment plumbing without reason. Reuse or adapt the proven PBIP/Fabric pipeline while replacing and extending the design intelligence around it. The primary engineering focus is now dashboard quality: visual hierarchy, appropriate visual type, filtering/interactions, enterprise aesthetics, synthetic-data storytelling, and iterative design state.
