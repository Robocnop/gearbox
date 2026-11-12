#!/usr/bin/env python3
"""gearbox — command hook (UserPromptSubmit, SessionStart, PostModelSwitch).

UserPromptSubmit : classify the prompt and inject one line of context.
SessionStart / PostModelSwitch : record the active model family in the state file.

Fail-open: any exception, invalid JSON, missing file or timeout => exit 0 with
no output, so the prompt always goes through without injected context.
Errors go to the capped local log (see gear.py), never to the user.
"""
import json
import sys
import time
from pathlib import Path

SCRIPTS = str(Path(__file__).resolve().parent)


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def on_model(data, event):
    """Remember the active model (SessionStart: `model`, PostModelSwitch: `to_model`)."""
    import gear

    raw = data.get("to_model") if event == "PostModelSwitch" else data.get("model")
    fam = gear.family_of(raw) if raw else None
    sid = data.get("session_id")
    state = gear.load_state()
    if fam:
        state["detected"] = {"family": fam, "raw": str(raw)[:80], "event": event,
                             "session_id": sid, "at": now()}
    elif event == "SessionStart" and sid and (state.get("detected") or {}).get("session_id") == sid:
        return  # same session, model not provided this time: keep what we know
    else:
        state.pop("detected", None)  # never keep a stale model
    gear.save_state(state)


def on_prompt(data):
    import classify
    import gear
    from i18n import t

    prompt = (data.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/"):
        return None

    sid = data.get("session_id")
    cfg = classify.load_config()
    state = gear.load_state()
    forced = state.get("forced")
    if forced in (1, 2, 3, 4):
        main, src = classify.resolve_main(cfg, state, sid)
        d = classify.decision(cfg, forced, t("forced_reason"), forced=True, main=main, main_source=src)
    else:
        d = classify.classify(prompt, cfg, state, sid)

    state["last"] = dict(d, prompt=prompt[:120], at=now())
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
    event = data.get("hook_event_name") or ("UserPromptSubmit" if "prompt" in data else "")
    if event in ("SessionStart", "PostModelSwitch"):
        on_model(data, event)
        return
    out = on_prompt(data) if event == "UserPromptSubmit" else None
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
