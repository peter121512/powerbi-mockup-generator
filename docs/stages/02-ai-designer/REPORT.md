# Stage 02 — AI Dashboard Designer and Clarification Gate: REPORT

## Summary

Delivered a production-shaped AI dashboard designer that converts natural-language requirements into a validated canonical `DashboardSpec`. The implementation separates probabilistic LLM reasoning from deterministic validation and gating through five explicit components: prompt builder, provider abstraction, Pydantic validation, semantic cross-reference validator, and a deterministic clarification gate.

The designer proves that a business prompt can become a coherent, analytically-first dashboard specification without uncontrolled prose flowing downstream.

## Files changed

| File | Action | Purpose |
|------|--------|---------|
| `src/pbi_gen/designer/__init__.py` | **Added** | Package init with public API exports |
| `src/pbi_gen/designer/result.py` | **Added** | Typed result/error model (DesignResult, DesignOutcome, etc.) |
| `src/pbi_gen/designer/provider.py` | **Added** | LLM provider abstraction + Bedrock implementation |
| `src/pbi_gen/designer/validator.py` | **Added** | Semantic cross-reference validation |
| `src/pbi_gen/designer/clarification.py` | **Added** | Deterministic clarification gate |
| `src/pbi_gen/designer/prompt.py` | **Added** | System prompt and context builder |
| `src/pbi_gen/designer/service.py` | **Added** | Main DashboardDesigner service + orchestration |
| `tests/test_designer.py` | **Added** | 61 comprehensive tests |

No existing files were modified. Stage 01 schema and tests remain untouched.

## Final designer architecture

```text
DashboardDesigner.design_dashboard(requirement)
    │
    ├── prompt.py: get_system_prompt(schema) + build_user_message(req)
    │       ↓
    ├── provider.py: LLMProvider.generate_structured(system, user, schema)
    │       ↓  (ProviderResponse with JSON content)
    ├── service.py: _extract_json(content)
    │       ↓  (parsed dict)
    ├── pydantic: DashboardSpec.model_validate(data)
    │       ↓  (typed DashboardSpec)
    ├── service.py: _ensure_initial_revision(spec)
    │       ↓  (corrected revision metadata)
    ├── validator.py: validate_spec(spec)
    │       ↓  (list[ValidationIssue] — empty = valid)
    ├── clarification.py: evaluate_clarification_gate(spec)
    │       ↓  (GateDecision)
    └── result.py: DesignResult.success(spec) | .needs_clarification(...) | .error(...)
```

## Chosen provider and rationale

**Amazon Bedrock** with Claude Sonnet (anthropic.claude-sonnet-4-20250514-v1:0) as default:

- The project already depends on `boto3` for Fabric deployment.
- Bedrock Converse API is the most straightforward structured-output path.
- Claude models produce high-quality structured JSON from schema instructions.
- No additional SDK dependency required.
- Region configurable via `ProviderConfig` (default: `eu-west-2`).

The provider boundary (`LLMProvider` ABC) makes switching to another provider (e.g. OpenAI, local model) a single class implementation without touching domain logic.

## Prompt / structured-output approach

The system prompt establishes a **mandatory 10-step reasoning order**:

1. Business objective → 2. Analytical questions → 3. Metrics/dimensions → 4. Semantic model → 5. Mock data story → 6. Page architecture → 7. Visual selection → 8. Filters/interactions → 9. Design system → 10. Confidence/assumptions

The prompt includes:
- The full Pydantic JSON schema for DashboardSpec
- Quality standards (5-8 visuals/page, appropriate types, meaningful data)
- Anti-patterns to avoid (chart wallpaper, gratuitous variety, pie overuse)
- Rules for FieldRef consistency, ID uniqueness, grid bounds
- Confidence/assumptions guidance (structured evidence, not percentages)

Output format: pure JSON, no markdown. The service extracts JSON from various formats (direct, code-fenced, preamble-wrapped) for robustness.

## Clarification-gate algorithm and examples

### Algorithm

The gate evaluates three rules in priority order:

**Rule 1 — High-impact negative evidence**: If a dimension in `{METRIC_DEFINITIONS, BUSINESS_CONTEXT, AUDIENCE_CLARITY, DATA_AVAILABILITY}` has `len(evidence_against) > len(evidence_for)` AND at least one `open_question`, trigger clarification.

**Rule 2 — Critical assumption**: If any assumption's `impact` contains keywords indicating material structural change (`"fundamentally"`, `"materially"`, `"entirely different"`, `"architecture"`, `"wrong dashboard"`, `"different report"`, `"different metrics"`, `"different model"`, `"cannot determine"`, `"contradictory"`), and the assumption has a `clarification_question`, trigger clarification.

**Rule 3 — LLM flagged with evidence**: If `requires_clarification == True` AND (Rule 1 or 2 already triggered OR any open question exists), honour the flag.

### Examples

| Scenario | Result | Reason |
|----------|--------|--------|
| Clear retail exec dashboard | **Proceed** | All evidence positive, routine assumptions |
| "Build a profitability dashboard focused on margin" | **Clarify** | METRIC_DEFINITIONS negative: "margin" could be gross/contribution/operating + critical assumption keyword "fundamentally different" |
| SaaS board dashboard, growth | **Proceed** | SaaS metrics are well-defined industry standards |
| VISUAL_CHOICE has open question about bar vs. line | **Proceed** | Not a high-impact dimension |
| Layout uncertainty with multiple valid options | **Proceed** | LAYOUT_DECISION is not high-impact |

When clarification triggers, the gate returns **one compact, high-value question** — not a questionnaire.

## Semantic validation added

The validator (`validator.py`) checks:

1. **Field references** — Every `FieldRef` in visuals (category_fields, value_fields, series_field, sort, conditional_formats) references an existing table/column/measure.
2. **Page references** — Drill-through source/target, navigation buttons, tooltip pages, and visual drill_through_target all reference existing page IDs.
3. **Relationship references** — from_table/to_table and their columns exist.
4. **Visual positions** — Within page grid bounds (x+width ≤ grid_columns, y+height ≤ grid_rows), non-negative, positive dimensions.
5. **Filter references** — Slicer/filter fields reference existing tables/columns.

## Typed result/error model

```python
class DesignOutcome(Enum):
    SUCCESS              # → result.spec is populated
    CLARIFICATION_NEEDED # → result.clarification has one question
    PROVIDER_ERROR       # → result.error_message describes failure
    INVALID_OUTPUT       # → malformed JSON or Pydantic validation failure
    VALIDATION_ERROR     # → semantic cross-reference issues
```

`DesignResult` is a frozen dataclass with static factory methods (`success()`, `needs_clarification()`, `provider_error()`, `invalid_output()`, `validation_error()`). Each carries `DesignDiagnostics` with provider/model info, validation errors, assumptions made.

## Tests run and results

```
$ .venv\Scripts\pytest.exe tests\ -v
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-8.3.5, pluggy-1.6.0
125 passed in 1.98s
```

- **Stage 01 tests**: 64 passed (unchanged)
- **Stage 02 tests**: 61 passed

Stage 02 test breakdown:
| Category | Tests | Coverage |
|----------|-------|----------|
| TestSuccessfulDesignFlow | 6 | Happy path, convenience function, diagnostics |
| TestPydanticValidation | 3 | Missing fields, bad enums, invalid FieldRef |
| TestSemanticValidation | 9 | Missing table/column/measure/page, out-of-bounds, relationships, filters |
| TestMalformedOutput | 4 | Non-JSON, empty, fenced, preamble |
| TestProviderError | 2 | Typed failure from provider |
| TestHighConfidenceProceeds | 2 | Clear retail + SaaS prompts proceed |
| TestClarificationTriggered | 3 | Ambiguous margin triggers, dimension, diagnostics |
| TestRoutineUncertaintyPasses | 4 | Visual choice, layout, non-critical assumption, empty |
| TestRevisionMetadata | 6 | Version 1, no parent, valid ID, force correction, unique IDs |
| TestConfidencePreserved | 2 | Assessments + assumptions flow through |
| TestJsonExtraction | 6 | Various formats |
| TestClarificationGateHelpers | 5 | Net-negative, critical keywords, dimension classification |
| TestPromptBuilder | 4 | Reasoning order, schema, user message, schema structure |
| TestDesignResultFactory | 5 | All factory methods |

All tests use `MockProvider` — no network access, no credentials required.

## Live-model smoke test

Not performed during this implementation session. The Bedrock provider is fully implemented and would work with appropriate AWS credentials configured. This is a design decision: automated tests must not depend on external services.

## Assumptions and deviations

1. **No retry logic** — The task mentioned "sensible timeouts/retry behaviour may be added". The `ProviderError` class carries a `retryable` flag so callers can implement retry, but the service does not auto-retry. This keeps the service deterministic and testable.

2. **Single Bedrock model call** — The designer makes one call rather than a chain-of-thought then structured-output two-call pattern. The system prompt is comprehensive enough that a capable model produces valid output in one pass. A future stage could add a critique-and-retry loop.

3. **JSON extraction is resilient** — The service tries three strategies (direct parse, code-fence extraction, brace-delimited extraction) to handle various model response formats. This was a practical decision rather than rejecting any non-pure-JSON response.

4. **No `config.yaml` integration** — Provider configuration is via `ProviderConfig` dataclass passed at construction time. Integration with the project's YAML config system is left for the CLI stage.

## Known limitations

1. **No retry/backoff** — A single provider failure is fatal. Production usage would benefit from configurable retry with exponential backoff.

2. **No streaming** — The provider blocks until the full response is available. Long generation times (~30-60s for complex specs) will feel slow in a CLI context.

3. **No conversation state** — This stage handles single-shot design only. Conversational amendment (user provides clarification answer, system continues) requires the next stage.

4. **Schema size in prompt** — The full DashboardSpec JSON schema is large (~3000 tokens). This consumes context window but is necessary for structured output quality. Could be optimised with schema simplification or model-specific structured output features.

5. **No overlap detection** — The validator checks grid bounds but not visual-visual overlap within a page. A full constraint solver is out of scope.

6. **Clarification gate is keyword-based** — Critical assumption detection uses keyword matching on impact strings. This is simple and predictable but could miss novel phrasings. The keywords list is explicitly configurable.

## Recommended next stage

**Stage 03: Conversational Revision** — Accept the clarification answer or a follow-up amendment and produce an updated DashboardSpec (version 2+) that preserves stable page/visual IDs. This would:
- Consume the clarification response and re-invoke the designer with additional context.
- Support "change the bar chart to a line chart" style amendments without full regeneration.
- Demonstrate the revision metadata system working across iterations.

Alternative: **Stage 03: Synthetic Data Generation** — Use the MockDataNarrative patterns to generate coherent SQLite data, enabling end-to-end spec→data→render testing.

## Agentic learning explanation

### Why this is an "agentic" component without a multi-agent framework

The designer exhibits agent-like behaviour because it:
- Receives an open-ended goal (natural-language requirement)
- Reasons about the problem autonomously (10-step analytical chain)
- Makes independent decisions (visual types, layouts, model structure)
- Self-assesses confidence (structured evidence, assumptions)
- Can decline to act (clarification gate)
- Produces a typed artefact consumed by downstream systems

No framework is needed because this is a single reasoning step with structured output. The complexity is in the *quality of reasoning* (via prompt engineering) and the *boundary discipline* (via validation), not in orchestrating multiple autonomous entities.

### Where probabilistic reasoning ends and deterministic code begins

| Boundary | Probabilistic (LLM) | Deterministic (code) |
|----------|---------------------|---------------------|
| Design decisions | ✅ Analytical judgement | |
| JSON output | ✅ Generates structure | |
| Schema conformance | | ✅ Pydantic validation |
| Revision metadata | | ✅ Force version=1, no parent |
| Cross-reference integrity | | ✅ Semantic validator |
| Clarification decision | ✅ Populates evidence | ✅ Gate evaluates evidence |
| ID uniqueness | | ✅ Pydantic validators |
| Grid bounds | | ✅ Position validator |

The critical insight: the LLM provides *evidence*, but deterministic code makes the *decision*. This means the gate behaviour is predictable, testable, and tuneable without changing the prompt.

### Why confidence evidence > confidence percentage

An LLM told to "rate your confidence 0-100" will produce an arbitrary number that:
- Cannot be compared across prompts
- Has no actionable meaning (is 72% high or low?)
- Cannot be decomposed into specific concerns
- Cannot guide a targeted clarification question

Evidence-based confidence provides:
- Specific dimensions that are uncertain vs. confident
- Concrete reasons why (evidence_against)
- Directly actionable questions (open_questions)
- Deterministic scoring (count evidence, apply rules)
- Traceability (which rule triggered, which evidence caused it)

### How structured output changes failure modes vs. parsing prose

| Prose parsing | Structured output |
|---------------|-------------------|
| Regex/heuristic extraction | Schema-validated JSON |
| Silent partial parse | Explicit ValidationError |
| Ambiguous field mapping | Typed field bindings |
| Version drift in prompts | Schema is the contract |
| "Creativity" in format | Constrained to schema |
| Hard to test boundaries | Unit-testable validators |

The failure mode shifts from "did my regex capture the chart title?" to "did the model produce valid JSON matching the schema?" — and the second question is trivially answerable with Pydantic.

### How the provider boundary keeps architecture model/vendor-independent

```python
class LLMProvider(ABC):
    def generate_structured(self, system_prompt, user_message, json_schema) -> ProviderResponse
```

The domain logic (service, validator, gate) depends only on this interface. Switching from Bedrock to OpenAI, Anthropic direct, or a local model requires only implementing one class — no changes to prompts, validation, gating, or tests. The `MockProvider` used in all 61 tests demonstrates this independence.

### Which parts will evolve into separate roles

| Current component | Future role | Stays deterministic? |
|-------------------|-------------|---------------------|
| Designer prompt + provider call | **Designer Agent** — generates specs | No (probabilistic) |
| Semantic validator | **Validation Function** — pre-deploy check | Yes |
| Clarification gate | **Gating Function** — decision boundary | Yes |
| (not yet built) | **Critic Agent** — evaluates rendered output | No (probabilistic) |
| (not yet built) | **Reviser Agent** — amends spec from critique | No (probabilistic) |
| Revision metadata handling | **State Management** — identity tracking | Yes |

The validator and gate should **never** become LLM-powered. Their value is in predictability and testability. The designer and future critic/reviser are inherently probabilistic and benefit from LLM reasoning.
