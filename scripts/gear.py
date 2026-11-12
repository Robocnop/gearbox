#!/usr/bin/env python3
"""gearbox — state, log + manual control.

  gear.py set <1-4|auto>   force or release the gear
  gear.py why              show the last decision
Data lives OUTSIDE the plugin and the repo, in ~/.claude/gearbox/
(override the folder with GEARBOX_HOME): state.json and gearbox.log.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n import t  # noqa: E402

LOG_MAX_LINES = 200


def home():
    return Path(os.environ.get("GEARBOX_HOME") or (Path.home() / ".claude" / "gearbox"))


def state_path():
    return home() / "state.json"


def log_path():
    return home() / "gearbox.log"


def log(msg):
    """Append to the local log, capped at LOG_MAX_LINES. Never raises, never prints."""
    try:
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []
        lines.append((time.strftime("%Y-%m-%d %H:%M:%S") + " " + str(msg)).replace("\n", " ")[:500])
        p.write_text("\n".join(lines[-LOG_MAX_LINES:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def load_state():
    """State dict; missing, unreadable or malformed file => empty state."""
    try:
        data = json.loads(state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"state.json unreadable ({type(e).__name__}): starting from empty state")
        return {}


def save_state(state):
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


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
    if not isinstance(last, dict) or "gear" not in last:
        print(t("none"))
        return
    print(t("why_last", at=last.get("at", "?"), prompt=repr(last.get("prompt", ""))))
    print(t("why_gear", **last) if last.get("agent") else t("why_nodeleg"))
    print(t("why_reason", reason=last.get("reason", "")))


if __name__ == "__main__":
    main(sys.argv[1:])
