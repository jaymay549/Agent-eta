import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import pilot


class TrialTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(pilot.SCHEMA)
        self.parser = pilot.parser()
        self.clock = 1000000

    def act(self, *args):
        a = self.parser.parse_args(args)
        with self.db:
            if a.cmd == "quote":
                return pilot.create(self.db, a, self.clock)
            if a.cmd == "week":
                return pilot.report(self.db, a, self.clock)
            return pilot.change(self.db, a, self.clock)

    def quote(self, model="A"):
        return self.act("quote", "Export", "--project", "store", "--host", "codex",
                        "--category", "feature", "--shape", "extend", "--model", model,
                        "--ordinary", "300", "--low", "5", "--mid", "20", "--high", "40",
                        "--budget", "30", "--done", "tests pass", "--risk", "pagination")

    def test_freezes_forecast_and_excludes_breaks(self):
        first = self.quote()
        key = first["id"]
        self.clock += 6000
        self.act("begin", key)
        self.clock += 600
        self.act("pause", key)
        self.clock += 3600
        self.act("resume", key)
        self.clock += 600
        self.act("checkpoint", key, "--remaining", "3", "--reason", "test failure")
        self.clock += 180
        result = self.act("close", key, "--outcome", "success", "--note", "suite passed")
        self.assertEqual((result["session_minutes"],result["wall_minutes"]),(23,83))
        shown = self.act("show", key)
        self.assertEqual(shown["task"]["forecast"]["minutes"], first["minutes"])
        self.assertEqual(shown["checkpoints"][0]["remaining"], 3)
        with self.assertRaises(ValueError):
            self.act("close", key, "--outcome", "success", "--note", "duplicate")
        other = self.quote("B")
        self.assertEqual(other["minutes"]["history"], 23)
        self.assertIsNone(other["minutes"]["model_history"])
        self.assertEqual(other["minutes"]["adjusted"], 20)
        self.assertIsNone(self.quote("unknown")["minutes"]["model_history"])
        next_run = self.quote()
        self.assertEqual(next_run["minutes"]["model_history"], 23)
        self.assertGreater(next_run["minutes"]["adjusted"], 20)
        self.assertLess(next_run["minutes"]["adjusted"], 23)

    def test_deadline_scoring_and_matched_cohorts(self):
        for outcome in ("success", "failed", "abandoned", "scope-changed", None):
            key = self.quote()["id"]
            self.act("begin", key)
            self.clock += (10 if outcome=="success" else 31)*60
            if outcome:
                self.act("close", key, "--outcome", outcome, "--note", "observed outcome")
        self.quote()  # a quote that did not start
        self.act("begin", self.quote()["id"])  # still within budget
        report = self.act("week")
        inspected = report["methods"]["inspected"]["method"]
        self.assertEqual(report["started"], 6)
        self.assertEqual((inspected["decisions"], inspected["false_fits"]), (4, 3))
        self.assertEqual(inspected["verified"], 1)
        self.assertEqual(report["methods"]["ordinary"]["method"]["false_overruns"], 1)
        paired = report["methods"]["model_history"]
        self.assertEqual(paired["method"]["decisions"], 3)
        self.assertEqual(paired["adjusted_on_same_tasks"]["verified"], 0)
        self.clock += 8*86400
        self.assertEqual(self.act("week")["started"], 0)

    def test_close_while_paused_and_failed_timing(self):
        key = self.quote()["id"]
        with self.assertRaises(ValueError):
            self.act("pause", key)
        self.act("begin", key)
        self.clock += 600
        self.act("pause", key)
        self.clock += 7200
        result = self.act("close", key, "--outcome", "abandoned", "--note", "stopped")
        self.assertEqual(result["session_minutes"], 10)
        self.assertIsNone(self.quote()["minutes"]["history"])

    def test_unreliable_timing_excluded_and_model_comparison_paired(self):
        key = self.quote()["id"]
        self.act("begin", key)
        self.clock += 5000
        self.act("close", key, "--outcome", "unmeasured", "--note", "missed pause")
        self.assertIsNone(self.quote()["minutes"]["history"])
        for model in ("A", "B", "A"):
            key = self.quote(model)["id"]
            self.act("begin", key)
            self.clock += 900
            self.act("close", key, "--outcome", "success", "--note", "checks passed")
        week = self.act("week")
        self.assertEqual(week["outcomes"]["unmeasured"], 1)
        paired = week["history_model_comparison_on_same_tasks"]
        self.assertEqual(paired["history"]["verified"], 1)
        self.assertEqual(paired["model_history"]["verified"], 1)
        self.assertEqual(week["methods"]["ordinary"]["method"]["decisions"], 3)

    def test_declined_quote_does_not_enter_week(self):
        key = self.quote()["id"]
        self.act("close", key, "--outcome", "abandoned", "--note", "declined")
        self.assertEqual(self.act("show", key)["status"], "abandoned")
        self.assertEqual(self.act("week")["started"], 0)

    def test_installed_entrypoint_and_legacy_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, AGENT_ETA_DB=str(Path(tmp) / "history.sqlite3"))
            def run(script, *args):
                output = subprocess.check_output([sys.executable,str(SCRIPTS/script),*args],
                                                 cwd=tmp,env=env)
                return json.loads(output)
            task = run("eta.py","start","existing timer")
            self.assertEqual(run("pilot.py","week")["started"],0)
            self.assertEqual(run("eta.py","finish",task["id"])["outcome"],"success")
            self.assertEqual(run("pilot.py","open"),[])


if __name__ == "__main__":
    unittest.main()
