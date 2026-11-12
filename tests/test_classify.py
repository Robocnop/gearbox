"""gearbox — classifier tests.  Run: python -m unittest discover tests"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import classify  # noqa: E402

FABLE_PROMPT = "Design from scratch a distributed job queue with a security threat model"

# (prompt, config overrides, expected gear, expected agent, expected delegate)
CASES = [
    ("tu peux tester ça ?", {}, 0, None, False),
    ("merci beaucoup", {}, 0, None, False),
    ("Fix the typo in README.md", {"main_model": "opus"}, 1, "gear-haiku", True),
    ("Add a unit test for parse_date and fix the bug", {"main_model": "sonnet"},
     2, "gear-sonnet", False),
    (FABLE_PROMPT, {"main_model": "fable"}, 4, "gear-opus", True),
    (FABLE_PROMPT, {"main_model": "", "allow_fable": True}, 4, "gear-fable", True),
]


class ClassifyTests(unittest.TestCase):
    def test_cases(self):
        base = classify.load_config()
        for prompt, overrides, gear, agent, delegate in CASES:
            with self.subTest(prompt=prompt, overrides=overrides):
                cfg = copy.deepcopy(base)
                cfg.update(overrides)
                d = classify.classify(prompt, cfg)
                self.assertEqual((d["gear"], d["agent"], d["delegate"]), (gear, agent, delegate), d["reason"])


if __name__ == "__main__":
    unittest.main()
