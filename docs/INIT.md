# One-Time Kiro Initialization

**Type:** one-time repository bootstrap instruction  
**Status:** ready

This is not a product-development stage. Run it once before beginning numbered stage work.

## Objective

Establish the local development workspace and verify that the repository is ready for the staged autonomous workflow described in `KIRO.md`.

## Instructions

1. Pull the latest `main` branch and confirm the working tree is clean before making changes.
2. Read `README.md` and `KIRO.md` completely.
3. Inspect the current repository tree and Git history sufficiently to understand that the previous Android/WebView prototype was intentionally removed from `main` and preserved on the `archive/pre-agentic-rebuild` branch.
4. Do **not** restore or copy the legacy Android implementation into `main`.
5. Confirm that your local environment can use Git and a modern Python 3 installation suitable for the forthcoming CLI/core-engine work. Do not introduce a Python framework or product architecture yet; those decisions belong to numbered stage tasks.
6. Ensure common local/generated files will not be accidentally committed by creating a minimal root `.gitignore` if one does not exist. It should cover Python bytecode/cache, virtual environments, test/tool caches, environment/secret files, IDE metadata and OS junk without ignoring source, documentation or lock files generically.
7. Do not implement dashboard-generation functionality, LLM calls, schemas, synthetic data generation, rendering, Android code, or speculative scaffolding in this initialization step.
8. Create `docs/INIT_REPORT.md` documenting:
   - repository state verified;
   - local Git and Python versions detected;
   - files changed;
   - checks performed and their results;
   - any environment issue that could block the first numbered stage.
9. Commit and push the initialization changes and report.

## Completion condition

Initialization is complete when the repository can be cleanly pulled, the operating instructions have been understood, local prerequisites have been checked, accidental generated/secret files are ignored, and `docs/INIT_REPORT.md` is committed.

After completion, wait for a numbered `docs/stages/.../TASK.md`. Future owner instruction **"check for new instructions"** is governed by `KIRO.md`, not this file.
