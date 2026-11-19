---
name: agent-eta
description: Estimate AI-assisted coding task durations and learn from completed work across Claude Code, Codex, Cursor, and other agents. Use when a user asks how long coding work will take, requests an ETA, or wants to track and calibrate model-specific task completion time. Supports on-demand and automatic estimate preferences with a local CLI and opt-in future telemetry design.
---
# Agent ETA v0.1

Estimate time to *successful task completion*, not token generation speed. Distinguish agent execution, human waiting, external dependencies, and verification. Never imply a measured model speed without actual observations.

## Setup

Ask whether estimates should be `automatic` (before substantial tasks) or `on-demand` (only on request). Store the preference using `python scripts/eta.py config --mode automatic` or `--mode on-demand`. The setting is a preference only: automatic invocation requires integration with the host agent; the CLI does not install hooks. Ask separately whether anonymous data sharing is permitted; default `--share no`. **No upload implementation exists in v0.1**, even if consent is recorded. The local database is `~/.agent-eta/history.sqlite3` or `AGENT_ETA_DB`.

## Workflow

1. Identify agent, exact model/version when exposed, task category, and complexity (1-5). If model is unknown, use `unknown`; never infer from provider branding.
2. Inspect requirements, codebase, tests, external dependencies, and definition of done. Split multi-part projects into tasks; do not count overlapping parallel durations twice.
3. Call `python scripts/eta.py estimate "task" --agent claude-code --model MODEL --category feature --complexity 3`. If insufficient data, explain that and give only a clearly labeled judgment-based range if useful; do not represent it as calibrated.
4. At execution start, call `python scripts/eta.py start "task" --agent claude-code --model MODEL --category feature --complexity 3`; retain returned ID.
5. When finished, call `python scripts/eta.py finish ID --outcome success` (or `failed` / `abandoned`). Only successful outcomes train v0.1 estimates. A finished task means acceptance criteria were checked, not merely code generated.
6. Report predicted vs actual minutes and sample count. Flag uncertain estimates and sparse data. Record a new task if the model changes midstream; v0.1 does not automatically segment mixed-model sessions.

## Scope and limitations

The bundled Python CLI is dependency-free and stores data locally. It is an **MVP**, not a working universal telemetry adapter. It cannot automatically discover agent/model identity, detect task boundaries, install Claude hooks, or aggregate other users' results. Model routing benchmarks may inform future cold-start priors but should not be treated as observed completion times. Do not transmit prompts, source code, or paths to shared analytics. Require separate opt-in, privacy review, and minimum cohort thresholds before implementing community benchmarks.
