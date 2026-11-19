"""Prospective, local AI coding ETA trial. Python 3.9+, standard library."""
import argparse
import json
import math
import os
import sqlite3
import statistics
import time
import uuid
from pathlib import Path

METHODS = ("ordinary", "history", "model_history", "inspected", "adjusted")
SCHEMA = """
CREATE TABLE IF NOT EXISTS eta_trial (
    id TEXT PRIMARY KEY, created REAL NOT NULL, started REAL, ended REAL,
    paused REAL, away REAL NOT NULL DEFAULT 0, outcome TEXT, verification TEXT,
    project TEXT NOT NULL, host TEXT NOT NULL, model TEXT NOT NULL, effort TEXT NOT NULL,
    category TEXT NOT NULL, shape TEXT NOT NULL, title TEXT NOT NULL,
    done TEXT NOT NULL, risk TEXT NOT NULL, ordinary REAL NOT NULL,
    low REAL NOT NULL, mid REAL NOT NULL, high REAL NOT NULL, budget REAL,
    forecast TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eta_checkpoint (
    task_id TEXT NOT NULL REFERENCES eta_trial(id), at REAL NOT NULL,
    remaining REAL NOT NULL, reason TEXT NOT NULL
);
"""


def positive(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0 or result > 1e9:
        raise argparse.ArgumentTypeError("use positive finite minutes or days (at most 1 billion)")
    return result


def elapsed(row, now):
    if row["started"] is None:
        return 0.0
    stop = row["ended"] or row["paused"] or now
    return max(0, (stop - row["started"] - row["away"]) / 60)


def median(values):
    return statistics.median(values) if values else None


def forecast(db, a, now):
    if not a.low <= a.mid <= a.high:
        raise ValueError("expected low <= mid <= high")
    rows = db.execute("""
        SELECT * FROM eta_trial WHERE outcome='success' AND host=? AND category=?
        AND shape=? AND ended<=? ORDER BY ended DESC
    """, (a.host, a.category, a.shape, now)).fetchall()
    local = [r for r in rows if r["project"] == a.project]
    cohort = (local or rows)[:30]
    same = [r for r in cohort if a.model != "unknown" and r["model"] == a.model
            and r["effort"] == a.effort]
    def timing(group):
        return median([elapsed(r, now) for r in group])
    # Shrink the observed multiplicative bias toward 1 with four neutral observations.
    # This trial parameter is evaluated against the unadjusted estimate in the report.
    ratios = [elapsed(r, now) / r["mid"] for r in same if elapsed(r, now) > 0]
    factor = math.exp(statistics.median(map(math.log, ratios)) * len(ratios) /
                      (len(ratios) + 4)) if ratios else 1.0
    return {
        "minutes": dict(ordinary=a.ordinary, history=timing(cohort),
                        model_history=timing(same), inspected=a.mid, adjusted=a.mid * factor),
        "planning_range_minutes": [a.low * factor, a.high * factor],
        "basis": "local timing correction" if ratios else "repo-informed judgment",
        "history_scope": "same project" if local else "across projects",
        "comparable_successes": len(cohort), "model_setting_matches": len(same),
        "correction_factor": factor,
        "inspection_evidence": a.evidence,
        "comparable_ids": [r["id"] for r in cohort],
        "model_setting_ids": [r["id"] for r in same],
    }


def create(db, a, now):
    prediction = forecast(db, a, now)
    key = uuid.uuid4().hex[:12]
    db.execute("""
        INSERT INTO eta_trial (id,created,project,host,model,effort,category,shape,title,
        done,risk,ordinary,low,mid,high,budget,forecast) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (key, now, a.project, a.host, a.model, a.effort, a.category, a.shape, a.title,
          a.done, a.risk, a.ordinary, a.low, a.mid, a.high, a.budget, json.dumps(prediction)))
    return dict(id=key, status="quoted", model=a.model, effort=a.effort, budget=a.budget, **prediction)


def status(r):
    if r["outcome"]:
        return r["outcome"]
    if r["started"] is None:
        return "quoted"
    return "paused" if r["paused"] is not None else "running"


def change(db, a, now):
    r = db.execute("SELECT * FROM eta_trial WHERE id=?", (a.id,)).fetchone()
    if not r:
        raise ValueError("unknown trial ID")
    state = status(r)
    if a.cmd == "show":
        return dict(task={**dict(r), "forecast": json.loads(r["forecast"])}, status=state,
                    session_minutes=elapsed(r, now), checkpoints=[dict(x) for x in db.execute(
                        "SELECT * FROM eta_checkpoint WHERE task_id=? ORDER BY at", (a.id,))])
    if a.cmd == "begin" and state == "quoted":
        db.execute("UPDATE eta_trial SET started=? WHERE id=?", (now, a.id))
    elif a.cmd == "pause" and state == "running":
        db.execute("UPDATE eta_trial SET paused=? WHERE id=?", (now, a.id))
    elif a.cmd == "resume" and state == "paused":
        db.execute("UPDATE eta_trial SET away=away+?, paused=NULL WHERE id=?", (now-r["paused"], a.id))
    elif a.cmd == "checkpoint" and state in ("running", "paused"):
        db.execute("INSERT INTO eta_checkpoint VALUES (?,?,?,?)", (a.id, now, a.remaining, a.reason))
    elif a.cmd == "close" and state == "quoted" and a.outcome == "abandoned":
        db.execute("UPDATE eta_trial SET ended=?, outcome=?, verification=? WHERE id=?",
                   (now, a.outcome, a.note, a.id))
        return dict(id=a.id, outcome=a.outcome, started=False)
    elif a.cmd == "close" and state in ("running", "paused"):
        if not a.note.strip():
            raise ValueError("supply verification or a reason for the outcome")
        extra = now-r["paused"] if state == "paused" else 0
        db.execute("UPDATE eta_trial SET ended=?, away=away+?, paused=NULL, outcome=?, verification=? WHERE id=?",
                   (now, extra, a.outcome, a.note, a.id))
        return dict(id=a.id, outcome=a.outcome, session_minutes=round(elapsed(r, now), 2),
                    wall_minutes=round((now-r["started"])/60, 2),
                    predicted_minutes=json.loads(r["forecast"])["minutes"]["adjusted"])
    else:
        raise ValueError(f"cannot {a.cmd} a {state} trial")
    return dict(id=a.id, action=a.cmd)


def score(cases, method, now):
    errors, signed, calls = [], [], []
    for r, f in cases:
        guess = f["minutes"][method]
        if guess is None:
            continue
        actual = elapsed(r, now)
        if r["outcome"] == "success":
            errors.append(abs(guess-actual))
            signed.append(guess-actual)
        if r["budget"] is None or r["outcome"] in ("scope-changed", "unmeasured"):
            continue
        if r["outcome"] is None and actual <= r["budget"]:
            continue
        fit = r["outcome"] == "success" and actual <= r["budget"]
        calls.append((guess <= r["budget"], fit))
    return dict(verified=len(errors), median_absolute_minutes=median(errors),
                median_signed_minutes=median(signed), decisions=len(calls),
                false_fits=sum(p and not y for p,y in calls),
                false_overruns=sum(not p and y for p,y in calls))


def report(db, a, now):
    cutoff = now - a.days * 86400
    rows = db.execute("SELECT * FROM eta_trial WHERE started BETWEEN ? AND ? ORDER BY started",
                      (cutoff, now)).fetchall()
    cases = [(r, json.loads(r["forecast"])) for r in rows]
    methods = {}
    for method in METHODS:
        matched = [(r,f) for r,f in cases if f["minutes"][method] is not None]
        methods[method] = {"method": score(matched, method, now),
                           "adjusted_on_same_tasks": score(matched, "adjusted", now)}
    statuses = {s: sum(status(r)==s for r in rows) for s in
                ("success","failed","abandoned","scope-changed","unmeasured","running","paused")}
    model_cases = [(r,f) for r,f in cases if f["minutes"]["model_history"] is not None]
    model_comparison = {name: score(model_cases, name, now)
                        for name in ("history", "model_history")}
    hits = []
    for r, f in cases:
        if r["outcome"] == "success":
            lo, hi = f["planning_range_minutes"]
            hits.append(lo <= elapsed(r, now) <= hi)
    return dict(days=a.days, started=len(rows), outcomes=statuses, methods=methods,
                history_model_comparison_on_same_tasks=model_comparison,
                adjusted_range=dict(inside=sum(hits), verified=len(hits)),
                tasks=[dict(id=r["id"], title=r["title"], model=r["model"], effort=r["effort"],
                            outcome=status(r), budget=r["budget"], session_minutes=elapsed(r,now),
                            wall_minutes=((r["ended"] or now)-r["started"])/60,
                            predictions=f["minutes"], basis=f["basis"], note=r["verification"])
                       for r,f in cases])


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="cmd", required=True)
    quote = commands.add_parser("quote", help="record pre-work forecasts without starting the clock")
    quote.add_argument("title")
    for key in ("project","host","done","risk"):
        quote.add_argument("--"+key, required=True)
    quote.add_argument("--evidence", help="brief repo observation supporting the inspected estimate")
    for key in ("model","effort"):
        quote.add_argument("--"+key, default="unknown")
    quote.add_argument("--category", choices=("feature","bug","refactor","test","infra","other"), required=True)
    quote.add_argument("--shape", choices=("extend","new","diagnose","migrate"), required=True)
    for key in ("ordinary","low","mid","high","budget"):
        quote.add_argument("--"+key, type=positive, required=key!="budget")
    for key in ("begin","pause","resume","close","checkpoint","show"):
        cmd = commands.add_parser(key)
        cmd.add_argument("id")
        if key=="close":
            cmd.add_argument("--outcome",choices=("success","failed","abandoned","scope-changed","unmeasured"),required=True)
            cmd.add_argument("--note",required=True)
        if key=="checkpoint":
            cmd.add_argument("--remaining",type=positive,required=True)
            cmd.add_argument("--reason",required=True)
    commands.add_parser("open", help="list pending and active task IDs")
    review = commands.add_parser("week")
    review.add_argument("--days",type=positive,default=7)
    return p


def main():
    p = parser()
    a = p.parse_args()
    path = Path(os.getenv("AGENT_ETA_DB", "~/.agent-eta/history.sqlite3")).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=10) as db:
            db.row_factory = sqlite3.Row
            db.executescript(SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            now = time.time()
            if a.cmd == "quote":
                result = create(db, a, now)
            elif a.cmd == "week":
                result = report(db, a, now)
            elif a.cmd == "open":
                result = [dict(id=r["id"], title=r["title"], project=r["project"], state=status(r))
                          for r in db.execute("SELECT * FROM eta_trial WHERE outcome IS NULL ORDER BY created DESC")]
            else:
                result = change(db, a, now)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, sqlite3.Error, ValueError) as exc:
        p.exit(2, f"agent-eta: {exc}\n")


if __name__ == "__main__":
    main()
