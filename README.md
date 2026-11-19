# Agent ETA

**Agent ETA v0.1** is a local-first prototype for forecasting how long AI-assisted coding tasks take **to complete successfully**, not merely how fast a model generates tokens.

It records agent, model, task category, complexity and actual completion time, then uses comparable successful tasks to produce a historical P20/P50/P80 duration range.

## Quick start

Requires Python 3.9+ and uses only the standard library.

```bash
python scripts/eta.py config --mode on-demand --share no
python scripts/eta.py estimate "Build inventory API" --agent claude-code --model claude-sonnet --category feature --complexity 3
python scripts/eta.py start "Build inventory API" --agent claude-code --model claude-sonnet --category feature --complexity 3
# Save the returned task ID, then after verifying completion:
python scripts/eta.py finish TASK_ID --outcome success
python scripts/eta.py history
```

The first estimate will report insufficient data until comparable successful tasks have been recorded. The database lives at `~/.agent-eta/history.sqlite3` (override with `AGENT_ETA_DB`).

## Skill installation

The root `SKILL.md` contains the reusable agent instructions. Copy this repository's skill files into your agent's supported skills directory and invoke the skill according to that agent's documentation. This release does **not** install hooks or register commands automatically.

## Current limitations

- Automatic versus on-demand is a stored preference; **automatic triggering is not implemented**.
- Agent and model names must be provided manually; no automatic detection.
- Start/finish calls are manual; idle time is not distinguished from active time.
- Estimates are based only on successful local observations, not live provider benchmarks.
- No network telemetry or anonymous community data sharing exists. `--share yes` records consent preference only and sends nothing.
- Mixed-model sessions are not segmented automatically.

## Roadmap

1. Claude Code hooks for reliable model/session detection and timing.
2. Adapter interface for Codex, Cursor and other agents.
3. Task boundary and idle-time measurement with acceptance criteria.
4. Calibrated cold-start priors and evaluation of forecast accuracy.
5. Privacy-reviewed, explicitly opt-in aggregate community benchmarks with no prompts or source code transmitted.

See [SKILL.md](SKILL.md) for the estimation workflow.
