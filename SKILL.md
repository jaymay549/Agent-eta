---
name: agent-eta
description: Forecast elapsed AI coding time with the selected model, track verified outcomes during an Agent ETA trial, and compare weekly predictions. Use for coding ETAs, a request to track coding work, or an Agent ETA weekly review.
---

# Agent ETA

Use the bundled CLI with Python 3.9+. Resolve `scripts/pilot.py` relative to the directory containing **this SKILL.md**. Pass its absolute path even when working in a different repo. Each call prints JSON. All estimates and budgets use minutes.

## Before implementation

1. Establish the finish line (e.g. passing local tests or a verified deployment), the selected host, exact model identifier and reasoning effort if exposed, and the user's available focused-session budget if given. Use the user's stated model when supplied. If the model is unknown and a model-specific forecast matters, ask once or give a provisional estimate with that limitation. Record unavailable settings as `unknown`. A marketing or provider name alone does not identify the model. Use a stable, non-sensitive project nickname.
2. Before looking up history or doing ETA-specific inspection, form an ordinary unaided best guess for the agreed scope. Hold that number fixed for `--ordinary`. Both this guess and the upcoming quote predict time from beginning execution after scoping to verified completion. If work is already under way, forecast **remaining** work from a named milestone and say so.
3. Briefly inspect concrete evidence such as an analogous code path, existing tests, a reproduction, or the normal build/deploy path. Describe what needs implementing, likely verify/fix cycles, known waits, and which steps overlap. Build low / typical / difficult-but-plausible totals for this model working with the user. Use measured local build/test durations when available. Use judgment for unknown durations and name the largest uncertainty. For unexplained failures, scope a diagnostic milestone when a repair estimate would be speculative. Do not run builds or start implementation solely to generate a quote unless requested.
4. Save the quote before implementation. Replace sample values below. `--shape` describes the dominant work. Omit `--budget` when the user hasn't given one. Only state percentage probabilities once supported by validation. A range in week one is a planning range.

```sh
python3 "/absolute/path/to/agent-eta/scripts/pilot.py" quote "Inventory export" \
  --project inventory --host codex --model unknown --effort unknown \
  --category feature --shape extend --ordinary 120 --low 35 --mid 65 --high 140 \
  --evidence "Orders already has an export route and integration fixture" \
  --done "Export works and the integration test passes" --risk "Pagination behavior" --budget 180
```

Categories are `feature`, `bug`, `refactor`, `test`, `infra`, `other`. Shapes are `extend` (reuse a pattern), `new` (new capability), `diagnose` (cause unknown), `migrate` (coordinated replacement). Use a short project label and store only task summaries suitable for a local log.

Always include the concrete repo observation in `--evidence` so it can be audited later. Tell the user the typical adjusted minutes, planning range, finish line, main risk and timing basis. Round sensibly. Distinguish matching local runs from an uncalibrated first-use judgment. When there's a budget, call out a range that crosses it. A task that fits a focused afternoon may still need a later external approval. Save the returned task ID in the chat. A quote-only request ends here. If the user declines the quote, close it as abandoned without beginning it.

## During authorized work

- Run `begin ID` immediately before execution. Timed work includes model calls, tools, required waits, checks, and retries. Keep retries of the same objective under the same ID.
- Use `pause ID` when explicitly setting the task aside and `resume ID` when work resumes. Waiting for required CI stays on the clock. For a human handoff, pause if work is being set aside. Reported wall time includes these breaks. Without an observed pause, the clock keeps running. If a missed timer makes the duration unreliable, close with outcome `unmeasured` and note why.
- On significant new evidence record `checkpoint ID --remaining MINUTES --reason TEXT` and update the user. The original forecast stays frozen. If the finish line materially changes or the selected model switches, close with `--outcome scope-changed` and quote the remaining scope separately, naming the prior ID in the new task summary.
- At acceptance, run `close ID --outcome success --note "actual check and result"` before finishing the turn. Use `failed` or `abandoned` for terminal unsuccessful attempts. Report predicted and actual time briefly. Use `open` or `show ID` to recover an ID or check whether a transition succeeded before retrying.

## Weekly review

Run `week` for the rolling seven-day cohort of task starts. Use `week --days N` for a longer cohort. Compare ordinary guesses, pooled history, same-model/effort history, inspected judgments, and adjusted forecasts. Use the paired counts and errors for the same tasks. Median signed error above zero means overestimation. Identify false fits (predicted within budget but missed) and false overruns (predicted over budget but fit). Check unfinished tasks, scope changes, small samples, range misses, and pauses before recommending an adjustment. Use `show ID` to inspect an outlier's original scope and checkpoints.

The SQLite file defaults to `~/.agent-eta/history.sqlite3`. To isolate a trial, set `AGENT_ETA_DB` consistently for every call. Data stays on the machine. Invoke this skill for each new task you want included. It does not register a global hook.
