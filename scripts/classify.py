#!/usr/bin/env python3
"""gearbox — classifieur local (stdlib uniquement, zéro appel API).

stdin : le prompt.  stdout : JSON {gear, model, effort, reason, ...}.
Les règles vivent dans gears.json (à la racine du plugin).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n import t  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "gears.json"
RANK = {"haiku": 1, "sonnet": 2, "opus": 3, "fable": 4}


def load_config(path=CONFIG):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def decision(cfg, gear, reason, forced=False):
    if gear == 0:
        return {"gear": 0, "model": None, "model_name": None, "agent": None,
                "effort": None, "reason": reason, "forced": forced, "delegate": False}
    src = gear
    if gear == 4 and not forced and not cfg.get("allow_fable"):
        src = 3
        reason += " ; " + t("fable_off")
    g = cfg["gears"][str(src)]
    delegate = True
    main = cfg.get("main_model")
    if not forced and main in RANK and RANK.get(g["model"], 0) >= RANK[main]:
        delegate = False
        reason += " ; " + t("capped", main=main, model=g.get("model_name", g["model"]))
    return {
        "gear": gear,
        "model": g["model"],
        "model_name": g.get("model_name", g["model"]),
        "agent": g["agent"],
        "effort": g["effort"],
        "reason": reason,
        "forced": forced,
        "delegate": delegate,
    }


def classify(prompt, cfg=None):
    cfg = cfg or load_config()
    text = prompt.strip()
    low = text.lower()
    reasons = []

    # 0) Pas de délégation : question, ou prompt court sans verbe d'action.
    z = cfg.get("zero_gear", {})
    n = len(text)
    starters = z.get("question_starters", [])
    is_q = text.endswith("?") or any(
        re.match(re.escape(s.lower()) + r"\b", low) for s in starters)
    if is_q and n <= z.get("question_max_chars", 400):
        return decision(cfg, 0, t("g0_question"))
    verbs = z.get("action_verbs", [])
    if n < z.get("short_max_chars", 60) and not any(
            re.search(r"(?<!\w)" + re.escape(v.lower()), low) for v in verbs):
        return decision(cfg, 0, t("g0_short"))

    # 1) Mots-clés : la vitesse la plus haute qui matche l'emporte (match en début de mot).
    gear = None
    for g in (4, 3, 2, 1):
        hits = [k for k in cfg["keywords"].get(str(g), [])
                if re.search(r"(?<!\w)" + re.escape(k.lower()), low)]
        if hits:
            gear = g
            reasons.append(t("kw", x=", ".join(hits[:3])))
            break
    if gear is None:
        if len(text) < cfg.get("short_prompt_chars", 40):
            gear = 1
            reasons.append(t("short"))
        else:
            gear = cfg.get("default_gear", 2)
            reasons.append(t("nosignal"))

    # 2) Signaux qui ne peuvent que monter la vitesse.
    def bump(min_gear, why):
        nonlocal gear
        if min_gear > gear:
            gear = min_gear
            reasons.append(why)

    n = len(text)
    for g in (4, 3):
        lim = cfg.get("length_chars", {}).get(str(g))
        if lim and n >= lim:
            bump(g, t("length", n=n))
            break

    exts = "|".join(re.escape(e) for e in cfg.get("file_extensions", []))
    if exts:
        files = set(re.findall(r"[\w\-./\\]*\w\.(?:" + exts + r")(?!\w)", low))
        for g in (4, 3):
            lim = cfg.get("files_mentioned", {}).get(str(g))
            if lim and len(files) >= lim:
                bump(g, t("files", n=len(files)))
                break

    if any(re.search(p, text, re.M) for p in cfg.get("stack_trace_patterns", [])):
        bump(cfg.get("stack_trace_gear", 3), t("trace"))

    return decision(cfg, gear, " ; ".join(reasons))


if __name__ == "__main__":
    prompt = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(classify(prompt), ensure_ascii=False))
