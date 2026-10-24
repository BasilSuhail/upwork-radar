"""Radar tests with a fake model: no Claude calls, no credits spent.  Run: python3 -m unittest discover tests"""
import importlib
import json
import os
import tempfile
import unittest


class RadarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["RADAR_HOME"] = self.tmp
        with open(os.path.join(self.tmp, "profile.md"), "w") as f:
            f.write("Test Person. n8n, Python, Power BI.")
        import radar.core
        self.core = importlib.reload(radar.core)

    def test_parse_strips_markdown_and_clamps(self):
        r = self.core.parse('```json\n{"score": 14, "verdict": "nope", "proposal": null}\n```')
        self.assertEqual(r["score"], 10)
        self.assertEqual(r["verdict"], "apply")
        self.assertEqual(r["proposal"], "")
        self.assertEqual(r["red_flags"], [])

    def test_parse_rejects_non_json(self):
        with self.assertRaises(ValueError):
            self.core.parse("I can't help with that.")

    def test_score_job_stores_history_and_status(self):
        seen = {}

        def fake(system, prompt, model):
            seen["system"], seen["prompt"] = system, prompt
            return json.dumps({"title": "n8n CRM sync", "score": 8, "verdict": "apply",
                               "niche": "ai-automation", "reasons": ["core niche"],
                               "red_flags": [], "proposal": "Hi, ..."})

        r = self.core.score_job("Need n8n workflow to sync HubSpot to Sheets", "https://x/job", ask=fake)
        self.assertIn("Test Person", seen["system"])
        self.assertIn("HubSpot", seen["prompt"])
        h = self.core.history()
        self.assertEqual(h[0]["id"], r["id"])
        self.assertEqual(h[0]["status"], "new")
        self.core.set_status(r["id"], "sent")
        self.assertEqual(self.core.history()[0]["status"], "sent")

    def test_empty_job_rejected(self):
        with self.assertRaises(ValueError):
            self.core.score_job("   ", ask=lambda *a, **k: "{}")


if __name__ == "__main__":
    unittest.main()
