# Agent ETA

A local one-week experiment for estimating AI-assisted coding time with the selected model. Requires Python 3.9+ and uses the standard library.

## Try it in Codex

Install this folder as `agent-eta` in your Codex skills directory, including `SKILL.md`, `agents/`, and `scripts/`. Start a fresh chat and use it on consecutive coding tasks, including the awkward ones. Example requests:

- “Use $agent-eta. I have two hours. Estimate this bug fix and then implement it.”
- “Use $agent-eta to estimate this change. I only want the estimate.”
- “Use $agent-eta to review my last week. Which method worked best?”

The skill records a quote before starting the clock. It tracks a focused session through verification and separately reports elapsed wall time. The week command compares tasks started within the previous seven days, as of the moment it is run. The skill runs when invoked. You can also use its CLI directly, from any repo:

```sh
python3 ~/.codex/skills/agent-eta/scripts/pilot.py open
python3 ~/.codex/skills/agent-eta/scripts/pilot.py week
```

## How estimates work

The ordinary estimate is the agent's first guess for the same finish line. It is collected by the same agent as the inspected forecast, so anchoring between guesses is possible. The inspected estimate considers reuse, testing, external waits and rework. The agent supplies the inspected range and midpoint. On the first task this is a judgment-based planning estimate for the stated setup. The script has no built-in model timing benchmarks.

Two independent baselines use the median successful session duration for a matching host, category and work shape. They prefer the same project when it has matches and otherwise use other projects, retaining up to 30 recent matches. The second baseline further requires the same named model and recorded effort. Unknown effort can match unknown effort. Unknown model identities do not qualify for model-specific evidence.

The adjusted estimate corrects the inspected midpoint and both range endpoints using historical ratios of actual minutes to inspected minutes in the model-specific cohort. It applies the median log ratio with weight n/(n+4), shrinking toward a neutral correction on thin history. Four neutral observations and the cohort rules are provisional design choices. The report directly compares adjusted vs. unadjusted estimates. Calibration uses prior verified successes only. Failed, abandoned, and overdue unfinished tasks count as missed budgets in the report. Unresolved cases still within budget, tasks with unreliable timing, and changed-scope tasks are excluded from budget scoring. Missing baselines stay missing. Timing accuracy uses verified completions and each baseline is paired with the adjusted method on the same available cases.

The stored budget is available session minutes. Leaving a task aside pauses that clock only if the pause was recorded. Wall time always includes breaks. A model switch starts a new forecast for remaining work. Baseline scores describe the observed mix of tasks and cannot establish a causal model speed difference.

## Storage and compatibility

Both CLIs use the local SQLite path `~/.agent-eta/history.sqlite3` or `AGENT_ETA_DB`. The pilot adds its own tables. The original `scripts/eta.py` commands and historical records remain available. Legacy timers lack frozen forecasts and pause information and are excluded from the prospective trial. No account or upload is required.

Use `python3 scripts/pilot.py --help` for CLI operations. Use `python3 -m unittest discover -s tests` to run the trial regression tests.
