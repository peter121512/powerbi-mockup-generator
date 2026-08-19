# Kiro Operating Instructions

## Purpose

This repository is developed in discrete, reviewable stages. ChatGPT and the project owner agree each stage and place the resulting task contract in the repository. Kiro is the implementation agent.

## Trigger phrase

When the project owner tells you **"check for new instructions"** (or clearly equivalent wording), execute this workflow autonomously.

1. Pull/fetch the latest repository state and ensure your working tree is based on the current remote branch.
2. Read this `KIRO.md` in full.
3. Inspect `docs/stages/` and identify the newest `TASK.md` whose stage does not yet have a completed `REPORT.md`.
4. Read the complete task contract and the relevant existing source, tests and documentation.
5. Make an internal implementation plan before editing code.
6. Implement the complete stage without asking the owner for routine decisions or approval.
7. Run appropriate automated tests, static checks and practical verification. Fix failures caused by your work.
8. Write the stage's `REPORT.md` beside its `TASK.md`.
9. Commit all intended source, test, documentation and report changes with clear commit messages and push them to the repository.
10. Tell the owner that the stage is complete and that the report is ready for review.

## Autonomy

Default to making sound engineering decisions yourself. Do not stop for approval merely because multiple reasonable implementation choices exist. Prefer the simplest design that satisfies the task and preserves the documented architecture.

Only request owner input when genuinely blocked, for example:

- required credentials or external access are unavailable;
- the task contains a material contradiction that cannot safely be resolved from repository context;
- proceeding would require an irreversible/destructive action not explicitly authorised;
- a required third-party capability is unavailable and there is no reasonable local substitute.

If a non-blocking ambiguity exists, make a reasonable assumption, continue, and record the assumption in `REPORT.md`.

## Scope discipline

`TASK.md` is the implementation contract. Complete it, but do not silently broaden it.

If you identify desirable refactors, features or architectural improvements that are not necessary to satisfy the current task, record them under **Recommended future work** in the report instead of implementing them.

Do not modify the task contract to make the implementation appear compliant. The task file is a historical record of what was requested.

## Engineering expectations

- Prefer explicit, typed, testable boundaries between AI/LLM behaviour and deterministic application logic.
- Prefer structured data contracts over free-form text between pipeline stages.
- Validate external and model-generated data at boundaries.
- Keep the core engine independent of any eventual Android UI.
- Do not hard-code secrets, API keys or machine-specific paths.
- Keep dependencies intentional and minimal.
- Add tests for meaningful behaviour introduced by each stage.
- Preserve backwards compatibility only when the task or current architecture requires it.
- Fail clearly rather than silently swallowing errors.

## Stage report contract

Every completed stage must contain a `REPORT.md` with at least:

1. **Summary** — what was delivered.
2. **Files changed** — important files added, modified or removed.
3. **Implementation decisions** — notable design/architecture choices and why.
4. **Task compliance** — each acceptance criterion and whether/how it was met.
5. **Tests and verification** — commands/checks run and results.
6. **Assumptions and deviations** — anything inferred or implemented differently from the task. State `None` if there were none.
7. **Known limitations** — current limitations relevant to later stages.
8. **Recommended future work** — useful ideas deliberately left outside this stage.

The report is a handoff document, not a substitute for correct code. It must accurately describe the repository state.

## Repository workflow

Stage work lives under:

`docs/stages/<stage-number>-<short-name>/TASK.md`

and completion is reported at:

`docs/stages/<stage-number>-<short-name>/REPORT.md`

A stage with a `TASK.md` and no completed `REPORT.md` is considered pending. Do not re-run completed stages unless explicitly instructed.
