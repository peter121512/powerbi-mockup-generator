# Stage 01 — Rich Dashboard Specification Foundation: REPORT

## Summary

Delivered a comprehensive canonical `DashboardSpec` Pydantic model that replaces the legacy flat dataclass schema. The new specification supports multi-page reports, rich visual semantics, structured filters/interactions, enterprise design system intent, analytical mock-data narratives, evidence-based confidence/assumptions, and revision metadata for conversational iteration.

## Files changed

| File | Action | Purpose |
|------|--------|---------|
| `src/pbi_gen/models/dashboard_spec.py` | **Added** | New canonical DashboardSpec with 30+ Pydantic models |
| `src/pbi_gen/models/__init__.py` | **Added** | Package init, re-exports all public symbols |
| `src/pbi_gen/__init__.py` | **Added** | Top-level package init |
| `src/pbi_gen/deploy/__init__.py` | **Added** | Deploy package init |
| `tests/__init__.py` | **Added** | Tests package init |
| `tests/test_dashboard_spec.py` | **Added** | 64 comprehensive tests |
| `pyproject.toml` | **Modified** | Added pydantic, pytest, pytest-cov; relaxed Python to >=3.11; added pytest config |
| `.gitignore` | **Added** | Standard Python gitignore |
| `docs/stages/01-dashboard-spec/REPORT.md` | **Added** | This report |

The legacy `src/pbi_gen/models/schema.py` is **preserved unchanged**. It remains importable but is superseded by `dashboard_spec.py`.

## Implementation decisions

### Why Pydantic v2

- **LLM structured output**: Pydantic models export JSON Schema directly, which enables constraining LLM output (Bedrock, OpenAI) to match the spec exactly.
- **Validation at boundaries**: Validators reject duplicate IDs, invalid field references, and missing required fields at parse time rather than deep in rendering logic.
- **Serialization**: Native `model_dump_json()` / `model_validate_json()` round-trip without custom serializers.
- **IDE support**: Type-checked, autocomplete-friendly models across the codebase.

### Schema design choices

1. **Stable IDs via UUID defaults** — Pages and visuals get auto-generated UUIDs if not provided, but accept explicit strings for deterministic testing and revision stability.

2. **FieldRef with validator** — A single model that references either a column or a measure (never both, never neither). This avoids separate binding types while keeping the contract tight.

3. **Enums with string values** — `VisualType`, `PageRole`, `FilterType`, etc. use `str, Enum` so they serialize as readable strings in JSON but remain type-safe in code.

4. **Design intent over rendering config** — The spec describes *what* the design should communicate (e.g. `formatting_intent: "no data labels, emphasize trend"`) rather than embedding Power BI JSON config. The renderer translates intent to PBIR.

5. **Evidence-based confidence** — Instead of arbitrary confidence percentages, `ConfidenceAssessment` captures evidence for/against decisions on specific dimensions. A later deterministic gate can score these.

6. **Mock data as narrative** — `MockDataNarrative` describes the business story (growth rates, outliers, seasonal patterns) rather than random value ranges. This enables coherent synthetic data generation.

7. **Interaction model is separate from pages** — Drill-through, tooltip pages, and navigation are modelled at report level in `InteractionConfig` while page-level slicers sit within `PageSpec.filters`.

### What was NOT built

- No designer agent or LLM integration.
- No PBIR renderer changes.
- No synthetic data generator rewrite.
- No persistence layer.
- No CLI changes.

## Task compliance

| Acceptance criterion | Status | Evidence |
|---------------------|--------|----------|
| Materially richer canonical DashboardSpec exists | ✅ | 30+ models vs. 4 legacy dataclasses |
| Supports pages, layout, visuals | ✅ | `PageSpec`, `PageLayout`, `VisualSpec`, `VisualPosition` |
| Supports filters/interactions | ✅ | `FilterSpec`, `InteractionConfig`, `DrillThroughConfig` |
| Supports design intent | ✅ | `ThemeSpec`, `ColourRole`, `TypographySpec`, `DensityPreference` |
| Supports confidence/assumptions | ✅ | `SpecConfidence`, `ConfidenceAssessment`, `Assumption` |
| Supports mock-data narrative | ✅ | `MockDataNarrative`, `DataPattern`, `DataPatternType` |
| Supports revision identity | ✅ | `RevisionMetadata` with spec_id, version, parent_spec_id |
| Serializable/deserializable | ✅ | JSON round-trip tested (8 tests) |
| Representative tests pass | ✅ | 64 tests, all passing |
| No secrets committed | ✅ | `.gitignore` excludes `config.yaml`; no secrets in source |
| Scope not expanded | ✅ | No renderer/designer/agent code added |
| Committed and pushed | ✅ | See git log |
| REPORT.md created | ✅ | This file |

## Tests and verification

```
$ .venv\Scripts\pytest.exe tests\ -v
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-8.3.5, pluggy-1.6.0
64 passed in 0.56s
```

Test categories:
- **TestRealisticConstruction** (8 tests): Full multi-page UK retail executive dashboard.
- **TestSerialization** (8 tests): JSON round-trip, dict conversion, enum preservation.
- **TestValidation** (8 tests): Duplicate IDs, invalid field refs, missing required fields.
- **TestRevisionMetadata** (5 tests): Version tracking, linked revisions, stable IDs.
- **TestConfidence** (6 tests): Structured uncertainty, assumptions, clarification flag.
- **TestInteractionsAndFilters** (8 tests): Slicers, drill-through, navigation, tooltip pages.
- **TestMockDataNarrative** (9 tests): Patterns, parameters, field refs, constraints.
- **TestThemeDesignSystem** (6 tests): Colour roles, typography, density, dark mode.
- **TestEdgeCases** (6 tests): Minimal spec, auto-IDs, large spec serialization.

## Assumptions and deviations

1. **Python 3.11 instead of 3.12** — The only available Python on this system is 3.11. The code uses `from __future__ import annotations` for `X | None` syntax and is otherwise compatible. `requires-python` was relaxed to `>=3.11`. This is a minor deviation; restoring `>=3.12` is trivial once a newer interpreter is available.

2. **Legacy schema preserved** — The task said "do not casually break the imported Fabric deployment baseline". `schema.py` is untouched. The new `dashboard_spec.py` lives alongside it. The next stage should update imports in `fabric.py` when ready.

3. **Pydantic 2.11.3** — Latest stable release at time of implementation. Pinned exactly to avoid surprising breaks.

## Compatibility implications for legacy renderer/data generator

The legacy `src/pbi_gen/deploy/fabric.py` imports from `src/pbi_gen/models/schema.py`. That file is **unchanged and still importable**. No existing code is broken.

However, the legacy schema and the new `DashboardSpec` are **not interchangeable**. A future stage must either:
- write a converter from `DashboardSpec` → legacy `DashboardSpec` (for gradual migration), or
- update the renderer/deployer to consume the new spec directly.

The new schema's `TableSpec`, `MeasureSpec`, and `Relationship` models are richer but semantically compatible with the legacy equivalents. Field names differ (`dtype` → `data_type`, `dict` relationships → typed `Relationship` model).

## Known limitations

1. **No cross-reference validation** — The schema does not currently validate that `FieldRef` references correspond to actual tables/columns/measures in the spec. This is intentional for this stage; a future validation pass can check referential integrity.

2. **No layout constraint solver** — `VisualPosition` uses a simple grid system but does not validate that visuals don't overlap or exceed page boundaries.

3. **No schema versioning** — If the schema itself changes between code versions, there's no migration path for persisted JSON specs yet. `RevisionMetadata` tracks *dashboard* versions, not schema versions.

4. **Single relationship between two tables** — The model doesn't prevent duplicate relationships between the same table pair. A validator could be added if needed.

## Recommended next stage

**Stage 02: AI Designer Agent** — An LLM-backed agent that accepts natural-language requirements and produces a valid `DashboardSpec`. This would:
- Use the Pydantic JSON Schema as LLM structured output constraint.
- Apply the confidence/assumption model to decide when to ask for clarification.
- Demonstrate the typed-contract handoff between probabilistic and deterministic components.

Alternative: **Stage 02: Synthetic Data Generation** — Use `MockDataNarrative` patterns to generate SQLite data that tells a coherent business story, enabling end-to-end preview without the full designer agent.

## Agentic learning explanation

### Why a typed intermediate state between LLM and tooling

An LLM generating a dashboard design is inherently probabilistic — it can choose different layouts, visual types, or measures each time. Downstream tools (PBIR generators, data generators, deployers) are deterministic and require exact, structured input.

The `DashboardSpec` sits at this boundary. It captures the *outcome* of LLM reasoning in a form that:
- Can be validated immediately (are all fields present? are IDs unique? do bindings make sense?).
- Can be passed to any downstream tool without re-interpretation.
- Can be persisted and diff'd for revision tracking.
- Can be critiqued by a separate LLM/agent without access to the original conversation.

Without this contract, each tool would need to parse free-form text, leading to fragile coupling and non-reproducible results.

### What should be LLM-generated vs. deterministically derived

| Concern | Reasoning agent (LLM) | Deterministic logic |
|---------|----------------------|---------------------|
| Which visuals to show | ✅ Requires analytical judgement | |
| Visual type selection | ✅ Contextual decision | |
| Layout/positioning | ✅ Design judgement | Validated for grid bounds |
| Stable IDs | | ✅ UUID generation |
| Filter field choices | ✅ Analytical relevance | |
| Colour palette | ✅ Aesthetic/brand choice | Validated for contrast |
| DAX measure expressions | ✅ Analytical logic | Syntax-checked |
| Mock data patterns | ✅ Business story decisions | Data generation is deterministic from patterns |
| Confidence assessment | ✅ Self-reflection on evidence | Score derivation is deterministic |
| Revision metadata | | ✅ Version incrementing, parent linking |

### How this enables agent communication without prose

Future pipeline stages communicate exclusively through `DashboardSpec`:

```
Designer Agent  ──(DashboardSpec)──▶  Data Generator
                                           │
                                     (DashboardSpec + SQLite)
                                           │
                                           ▼
                                    PBIR Renderer
                                           │
                                     (deployed report)
                                           │
                                           ▼
                                    Critic Agent  ──(amended DashboardSpec)──▶  back to top
```

Each agent reads the spec, performs its function, and either passes the same spec downstream or produces an amended version with updated `RevisionMetadata`. No stage needs to interpret natural language from another stage — the structured contract is the communication medium.
