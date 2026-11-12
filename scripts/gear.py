#!/usr/bin/env python3
"""gearbox — état + contrôle manuel.

  gear.py set <1-4|auto>   force ou relâche la vitesse
  gear.py why              affiche la dernière décision
État : ~/.claude/gearbox/state.json
"""
import json
import sys
from pathlib import Path

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

    if cmd == "set":
        arg = (argv[1] if len(argv) > 1 else "").strip().lower()
        if arg == "auto":
            state.pop("forced", None)
            save_state(state)
            print("[gearbox] mode auto : la vitesse est de nouveau choisie par le classifieur.")
        elif arg in ("1", "2", "3", "4"):
            state["forced"] = int(arg)
            save_state(state)
            print(f"[gearbox] vitesse forcée sur {arg} (jusqu'à `/gear auto`).")
        else:
            forced = state.get("forced")
            print(f"[gearbox] usage : /gear <1-4|auto> — actuellement : "
                  f"{'forcée sur ' + str(forced) if forced else 'auto'}.")
        return

    last = state.get("last")
    forced = state.get("forced")
    print(f"[gearbox] mode : {'forcé sur ' + str(forced) if forced else 'auto'}")
    if not last:
        print("Aucune décision enregistrée pour l'instant.")
        return
    print(f"Dernier prompt ({last.get('at', '?')}) : {last.get('prompt', '')!r}")
    print(f"Vitesse {last['gear']} → agent {last['agent']} ({last['model_name']}), effort {last['effort']}")
    print(f"Raison : {last['reason']}")


if __name__ == "__main__":
    main(sys.argv[1:])
