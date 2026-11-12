#!/usr/bin/env python3
"""gearbox — state + manual control.

  gear.py set <1-4|auto>   force or release the gear
  gear.py why              show the last decision
State: ~/.claude/gearbox/state.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n import t  # noqa: E402

STATE = Path.home() / ".claude" / "gearbox" / "state.json"


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cmd = argv[0] if argv else "why"
    state = load_state()
    forced = state.get("forced")
    cur = t("cur_forced", g=forced) if forced else t("mode_auto")

    if cmd == "set":
        arg = (argv[1] if len(argv) > 1 else "").strip().lower()
        if arg == "auto":
            state.pop("forced", None)
            save_state(state)
            print(t("set_auto"))
        elif arg in ("1", "2", "3", "4"):
            state["forced"] = int(arg)
            save_state(state)
            print(t("set_forced", g=arg))
        else:
            print(t("usage", cur=cur))
        return

    last = state.get("last")
    print(t("why_mode", cur=cur))
    if not last:
        print(t("none"))
        return
    print(t("why_last", at=last.get("at", "?"), prompt=repr(last.get("prompt", ""))))
    print(t("why_gear", **last) if last.get("agent") else t("why_nodeleg"))
    print(t("why_reason", reason=last["reason"]))


if __name__ == "__main__":
    main(sys.argv[1:])
