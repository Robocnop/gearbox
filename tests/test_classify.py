"""gearbox — tests (Python stdlib only).  Run: python -m unittest discover tests"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
os.environ["GEARBOX_LANG"] = "en"
os.environ.pop("GEARBOX_CONFIG", None)
sys.path.insert(0, str(SCRIPTS))
import classify  # noqa: E402
import gear  # noqa: E402

FABLE_PROMPT = "Design from scratch a distributed job queue with a security threat model"
TRACE_PROMPT = ('Voici l\'erreur\nTraceback (most recent call last):\n  File "app.py", line 3, in <module>\n'
                '    deploy()\nValueError: security token')
CODE_PROMPT = ("Voici le fichier:\n```python\ndef refactor_all():\n    # refactor everything across modules\n"
               "    pass\n```\nRenomme la variable foo en bar")


def cfg_with(**overrides):
    cfg = copy.deepcopy(classify.load_config())
    cfg.update(overrides)
    return cfg


class Isolated(unittest.TestCase):
    """Each test gets its own empty data folder (state + log), never the user's."""

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="gearbox-test-")
        self._old = os.environ.get("GEARBOX_HOME")
        os.environ["GEARBOX_HOME"] = self.home

    def tearDown(self):
        if self._old is None:
            os.environ.pop("GEARBOX_HOME", None)
        else:
            os.environ["GEARBOX_HOME"] = self._old
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, name, text):
        p = Path(self.home) / name
        p.write_text(text, encoding="utf-8")
        return p


# (prompt, config overrides, state, expected gear, expected agent, expected delegate)
CASES = [
    # gear 0: questions and short prompts without action verb
    ("tu peux tester ça ?", {}, None, 0, None, False),
    ("Why does this crash?", {}, None, 0, None, False),
    ("merci beaucoup", {}, None, 0, None, False),
    # gears 1-4 and the rank rule
    ("Fix the typo in README.md", {"main_model": "opus"}, None, 1, "gear-haiku", True),
    ("Add a unit test for parse_date and fix the bug", {"main_model": "sonnet"}, None, 2, "gear-sonnet", False),
    ("Refactor the module across a.py b.py c.py d.py", {"main_model": "fable"}, None, 3, "gear-opus", True),
    (FABLE_PROMPT, {"main_model": "fable"}, None, 4, "gear-opus", True),  # Fable off by default
    (FABLE_PROMPT, {"main_model": "", "allow_fable": True}, None, 4, "gear-fable", True),
    # simple negations (FR + EN): the negated keyword must not count
    ("pas besoin de tester, juste renomme la variable x en y dans utils", {"main_model": ""}, None,
     1, "gear-haiku", True),
    ("Don't refactor anything, just fix the typo in the docs please", {"main_model": ""}, None,
     1, "gear-haiku", True),
    # code blocks are ignored for keywords ("refactor", "across" inside the fence)
    (CODE_PROMPT, {"main_model": ""}, None, 1, "gear-haiku", True),
    # accents and case are normalized
    ("CORRIGE LA FAUTE D'ORTHOGRAPHE DANS LE TITRE", {"main_model": ""}, None, 1, "gear-haiku", True),
    ("Fais une revue de sécurité du module login", {"main_model": ""}, None, 4, "gear-opus", True),
    ("Fais une revue de securite du module login", {"main_model": ""}, None, 4, "gear-opus", True),
    # a stack trace is only a boolean signal: gear 3, and "security" inside it does not make it gear 4
    (TRACE_PROMPT, {"main_model": ""}, None, 3, "gear-opus", True),
    # detected main model beats gears.json
    ("Fix the typo in README.md", {"main_model": ""}, {"detected": {"family": "opus"}}, 1, "gear-haiku", True),
    ("Fix the typo in README.md", {"main_model": "opus"}, {"detected": {"family": "haiku"}}, 1, "gear-haiku", False),
    ("Fix the typo in README.md", {"main_model": "opus"}, {"main_override": "haiku"}, 1, "gear-haiku", False),
]


class ClassifierTests(Isolated):
    def test_cases(self):
        for prompt, overrides, state, gear_n, agent, delegate in CASES:
            with self.subTest(prompt=prompt[:40], overrides=overrides, state=state):
                d = classify.classify(prompt, cfg_with(**overrides), state)
                self.assertEqual((d["gear"], d["agent"], d["delegate"]), (gear_n, agent, delegate), d["reason"])

    def test_forced_gear_ignores_rank_rule(self):
        cfg = cfg_with()
        self.assertFalse(classify.decision(cfg, 3, "x", main="sonnet")["delegate"])
        self.assertTrue(classify.decision(cfg, 3, "x", forced=True, main="sonnet")["delegate"])
        forced4 = classify.decision(cfg, 4, "x", forced=True, main="opus")
        self.assertEqual((forced4["agent"], forced4["delegate"]), ("gear-fable", True))

    def test_main_model_priority(self):
        cfg = cfg_with(main_model="sonnet")
        both = {"detected": {"family": "opus", "session_id": "a"}, "main_override": "haiku"}
        self.assertEqual(classify.resolve_main(cfg, both, "a"), ("opus", "detected"))
        self.assertEqual(classify.resolve_main(cfg, both, "b"), ("haiku", "manual"))  # other session
        self.assertEqual(classify.resolve_main(cfg, {"main_override": "haiku"}), ("haiku", "manual"))
        self.assertEqual(classify.resolve_main(cfg, {}), ("sonnet", "config"))
        self.assertEqual(classify.resolve_main(cfg, {"detected": "junk", "main_override": 3}), ("sonnet", "config"))
        self.assertEqual(classify.resolve_main(cfg_with(main_model=""), {}), (None, "none"))

    def test_main_model_detection_from_model_ids(self):
        self.assertEqual(gear.family_of("claude-opus-5-5"), "opus")
        self.assertEqual(gear.family_of("Claude Sonnet 5.5"), "sonnet")
        self.assertEqual(gear.family_of({"id": "claude-haiku-5-5"}), "haiku")
        self.assertEqual(gear.family_of("claude-fable-5-2[1m]"), "fable")
        self.assertIsNone(gear.family_of("some-other-model"))


class ConfigTests(Isolated):
    def test_shipped_gears_json_is_valid_and_matches_defaults(self):
        shipped = json.loads((ROOT / "gears.json").read_text(encoding="utf-8"))
        cfg, warnings = classify.validate(shipped)
        self.assertEqual(warnings, [])
        self.assertEqual(cfg, classify.DEFAULTS)

    def test_corrupt_or_missing_config_falls_back_to_defaults(self):
        for text in ("{{{ not json", "[1, 2]", ""):
            with self.subTest(text=text):
                self.assertEqual(classify.load_config(self.write("g.json", text)), classify.DEFAULTS)
        self.assertEqual(classify.load_config(Path(self.home) / "missing.json"), classify.DEFAULTS)
        self.assertEqual(classify.classify("Fix the typo in README.md", classify.DEFAULTS)["gear"], 1)

    def test_invalid_values_are_replaced_individually_and_logged(self):
        bad = {"default_gear": "abc", "main_model": "gpt", "keywords": {"1": "typo"},
               "stack_trace_patterns": ["(("], "gears": {"2": 5}, "allow_fable": True}
        cfg = classify.load_config(self.write("g.json", json.dumps(bad)))
        self.assertEqual(cfg["default_gear"], classify.DEFAULTS["default_gear"])
        self.assertEqual(cfg["main_model"], classify.DEFAULTS["main_model"])
        self.assertEqual(cfg["keywords"]["1"], classify.DEFAULTS["keywords"]["1"])
        self.assertEqual(cfg["stack_trace_patterns"], classify.DEFAULTS["stack_trace_patterns"])
        self.assertEqual(cfg["gears"]["2"], classify.DEFAULTS["gears"]["2"])
        self.assertTrue(cfg["allow_fable"])  # a valid value is kept
        self.assertIn("invalid default_gear", gear.log_path().read_text(encoding="utf-8"))


class StateAndLogTests(Isolated):
    def test_absent_state_is_empty(self):
        self.assertEqual(gear.load_state(), {})

    def test_corrupt_state_is_empty_and_logged(self):
        for text in ("{{{", "[1]", '"str"'):
            with self.subTest(text=text):
                self.write("state.json", text)
                self.assertEqual(gear.load_state(), {})

    def test_log_is_capped(self):
        for i in range(gear.LOG_MAX_LINES + 50):
            gear.log(f"line {i}")
        lines = gear.log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), gear.LOG_MAX_LINES)
        self.assertTrue(lines[-1].endswith(f"line {gear.LOG_MAX_LINES + 49}"))

    def test_data_lives_outside_the_repo(self):
        self.assertFalse(str(gear.state_path()).startswith(str(ROOT)))
        self.assertFalse(str(gear.log_path()).startswith(str(ROOT)))


class HookTests(Isolated):
    def run_hook(self, payload, **env):
        data = payload if isinstance(payload, str) else json.dumps(payload)
        r = subprocess.run([sys.executable, str(SCRIPTS / "hook.py")], input=data.encode("utf-8"),
                           capture_output=True, env=dict(os.environ, **env), timeout=15)
        return r.returncode, r.stdout.decode("utf-8", "replace")

    def prompt(self, text="Fix the typo in README.md", sid="s1"):
        return {"hook_event_name": "UserPromptSubmit", "session_id": sid, "prompt": text}

    def test_fail_open_on_invalid_input(self):
        for bad in ("not json", "", "[1, 2]", '{"prompt": 5}'):
            with self.subTest(bad=bad):
                code, out = self.run_hook(bad)
                self.assertEqual((code, out), (0, ""))
        self.assertIn("hook error", gear.log_path().read_text(encoding="utf-8"))

    def test_fail_open_with_broken_config(self):
        broken = self.write("broken.json", "{{{")
        for cfg_path in (str(broken), str(Path(self.home) / "missing.json")):
            with self.subTest(cfg=cfg_path):
                code, out = self.run_hook(self.prompt(), GEARBOX_CONFIG=cfg_path)
                self.assertEqual(code, 0)
                self.assertIn("additionalContext", out)  # defaults still work

    def test_detected_model_drives_delegation(self):
        start = {"hook_event_name": "SessionStart", "session_id": "s1", "model": "claude-opus-5-5"}
        self.assertEqual(self.run_hook(start), (0, ""))
        self.assertIn("additionalContext", self.run_hook(self.prompt())[1])  # haiku < opus
        switch = {"hook_event_name": "PostModelSwitch", "session_id": "s1", "to_model": "claude-haiku-5-5"}
        self.assertEqual(self.run_hook(switch), (0, ""))
        self.assertEqual(self.run_hook(self.prompt()), (0, ""))  # haiku is not above haiku
        self.assertEqual(gear.load_state()["last"]["main_source"], "detected")

    def test_question_injects_nothing(self):
        self.assertEqual(self.run_hook(self.prompt("tu peux tester ça ?")), (0, ""))
        self.assertEqual(gear.load_state()["last"]["gear"], 0)


if __name__ == "__main__":
    unittest.main()
