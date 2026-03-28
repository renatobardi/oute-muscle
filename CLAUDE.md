# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**oute-muscle** is a greenfield project. No application code exists yet — only the SpecKit scaffolding for spec-driven development.

## SpecKit Workflow

This project uses [SpecKit v0.4.3](https://github.com/speckit) for structured feature development. The workflow is sequential:

1. `/speckit.constitution` — Define project principles (optional, template at `.specify/memory/constitution.md`)
2. `/speckit.specify <description>` — Create feature spec from natural language; creates a numbered branch (`NNN-short-name`) and `specs/<branch>/spec.md`
3. `/speckit.clarify` — Identify and resolve underspecified areas in the spec
4. `/speckit.plan` — Generate implementation plan (`plan.md`) with tech stack and architecture
5. `/speckit.tasks` — Generate dependency-ordered task list (`tasks.md`) organized by user story
6. `/speckit.analyze` — Cross-artifact consistency check across spec, plan, and tasks
7. `/speckit.checklist` — Generate validation checklist for the feature
8. `/speckit.implement` — Execute tasks phase by phase from `tasks.md`
9. `/speckit.taskstoissues` — Convert tasks to GitHub issues

## Key Scripts

All scripts are in `.specify/scripts/bash/`:

- `create-new-feature.sh` — Creates feature branch and spec directory under `specs/`. Supports `--json`, `--short-name`, `--timestamp` flags. Auto-detects next sequential number.
- `check-prerequisites.sh` — Validates feature context (branch, directories, required docs). Supports `--json`, `--require-tasks`, `--include-tasks`, `--paths-only`.
- `common.sh` — Shared utilities (repo root detection, template resolution, path helpers).

## Project Structure

```
specs/<branch-name>/       # Created per feature by /speckit.specify
  spec.md                  # Feature specification (what & why, no implementation details)
  plan.md                  # Technical implementation plan
  tasks.md                 # Ordered task checklist
  checklists/              # Validation checklists
  data-model.md            # Entity definitions (optional)
  contracts/               # API/interface contracts (optional)
  research.md              # Technical decisions (optional)
.specify/templates/        # Templates for all artifacts
.specify/memory/           # Constitution and project principles
.specify/scripts/bash/     # Automation scripts
```

## Branch Naming

Configured for **sequential** numbering (in `.specify/init-options.json`). Branches follow the pattern `NNN-short-name` (e.g., `001-user-auth`). The create script auto-increments by scanning existing branches and `specs/` directories.

## Important Conventions

- Specs focus on **what** and **why**, never implementation details (no tech stack, APIs, or code structure in `spec.md`)
- Tasks use strict checklist format: `- [ ] T001 [P] [US1] Description with file path`
- `[P]` marks parallelizable tasks; `[US1]` maps to user stories from the spec
- Constitution (`.specify/memory/constitution.md`) must be filled before it governs the project — currently contains only the template placeholders
