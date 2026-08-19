# Power BI Mockup Generator

An AI-powered system for designing enterprise-quality Power BI dashboard solutions from business requirements.

## Long-term goal

The product should accept natural-language dashboard requirements and ultimately produce deployable Power BI mock-ups with exceptional enterprise visual quality. The intelligence should reason about the analytical problem before it reasons about visuals.

The engine is intended to support two permanent data-model routes:

1. **Prescribed/modelled route** — the user describes the dashboard they need. The system determines the analytical requirements, prescribes an appropriate Power BI semantic model, generates credible synthetic test data, designs the report, and explains how source data should be shaped to fit the recommended model.
2. **Supplied-model route** — the user supplies a real or described data model. The system assesses whether it can support the requested analytics, recommends modelling changes where appropriate, identifies unavailable metrics, and designs the report against the viable model.

## Delivery phases

### Phase 1 — Mock-data engine

CLI-first development. From dashboard requirements, create a structured analytical specification, recommended semantic model, representative synthetic data, measures, dashboard specification and high-quality rendered preview.

### Phase 2 — Real and prescribed models

Retain the mock/prescribed route while adding support for user-provided models and data descriptions. Analyse feasibility, recommend modelling changes, map data to analytical requirements and eventually consume richer Power BI semantic-model metadata.

### Phase 2.5 — Power BI artefact generation

Translate the validated internal dashboard specification into real Power BI-compatible artefacts: semantic model, measures, report pages, visuals, themes and related configuration.

### Phase 3 — Android product

Build the polished Android user experience on top of the mature engine. Android is a client of the engine, not the location of the core intelligence.

## Architectural principles

The intended reasoning flow is broadly:

```text
Business requirements
        ↓
Analytical questions
        ↓
Required metrics
        ↓
Required data
        ↓
Model prescription OR supplied-model assessment
        ↓
Synthetic data generation OR real-data mapping
        ↓
Measures / calculations
        ↓
Dashboard design specification
        ↓
Rendering / Power BI generation
        ↓
Validation and critique
        ↓
Revision
```

Key principles:

- Separate business/analytical semantics from visual presentation.
- Use structured contracts between stages rather than passing uncontrolled prose.
- Make the core engine UI-independent.
- Prefer deterministic application logic where an LLM is unnecessary.
- Treat generated synthetic data as a coherent business scenario, not random filler.
- Build an explicit enterprise dashboard design system rather than relying on prompts to "make it pretty".
- Validate that requested metrics, models, generated data and visuals are mutually consistent.
- Add agentic behaviour incrementally where autonomy or critique provides genuine value.

## Development workflow

Development is intentionally staged so the project also serves as a practical AI/agentic-engineering learning project.

Standing implementation-agent instructions are in [`KIRO.md`](KIRO.md). Individual stage contracts and implementation reports live under `docs/stages/`.

The original Android/WebView proof of concept is preserved in the Git branch `archive/pre-agentic-rebuild`. It demonstrated the end-to-end idea but is not the architectural foundation for the new engine.
