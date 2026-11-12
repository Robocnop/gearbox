#!/usr/bin/env python3
"""gearbox — command hook (UserPromptSubmit).

Fail-open: any exception, invalid JSON, missing file or timeout => exit 0 with
no output, so the prompt always goes through without injected context.
Errors go to the capped local log (see gear.py), never to the user.
"""
import json
import sys
import time
from pathlib import Path

SCRIPTS = str(Path(__file__).resolve().parent)


def on_prompt(data):
    import classify
    import gear
    from i18n import t

    prompt = (data.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/"):
        return None

    cfg = classify.load_config()
    state = gear.load_state()
    forced = state.get("forced")
    if forced in (1, 2, 3, 4):
        d = classify.decision(cfg, forced, t("forced_reason"), forced=True)
    else:
        d = classify.classify(prompt, cfg)

    state["last"] = dict(d, prompt=prompt[:120], at=time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        gear.save_state(state)
    except Exception as e:
        gear.log(f"could not save state ({type(e).__name__}): {e}")

    if not d.get("delegate", True):
        return None
    ctx = t("ctx", mode=t("mode_forced" if d["forced"] else "mode_auto"), **d)
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}


def main():
    sys.path.insert(0, SCRIPTS)
    data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    if not isinstance(data, dict):
        return
    out = on_prompt(data)
    if out:
        sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail-open: never block or break the prompt
        try:
            sys.path.insert(0, SCRIPTS)
            import gear
            gear.log(f"hook error {type(e).__name__}: {e}")
        except Exception:
            pass
    sys.exit(0)
