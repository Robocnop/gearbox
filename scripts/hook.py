#!/usr/bin/env python3
"""gearbox — hook UserPromptSubmit.

Classe le prompt et injecte une ligne de contexte. Ne bloque jamais :
toute erreur => sortie silencieuse, code 0.
"""
import json
import sys
import time
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import classify
    import gear
    from i18n import t

    data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    prompt = (data.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/"):
        return

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
    except Exception:
        pass

    if not d.get("delegate", True):
        return

    ctx = t("ctx", mode=t("mode_forced" if d["forced"] else "mode_auto"), **d)
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
