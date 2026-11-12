#!/usr/bin/env python3
"""gearbox — classifieur local (stdlib uniquement, zéro appel API).

stdin : le prompt.  stdout : JSON {gear, model, effort, reason, ...}.
Les règles vivent dans gears.json (à la racine du plugin).
"""
import json
import re
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "gears.json"


def load_config(path=CONFIG):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def decision(cfg, gear, reason, forced=False):
    g = cfg["gears"][str(gear)]
    return {
        "gear": gear,
        "model": g["model"],
        "model_name": g.get("model_name", g["model"]),
        "agent": g["agent"],
        "effort": g["effort"],
        "reason": reason,
        "forced": forced,
    }


def classify(prompt, cfg=None):
    cfg = cfg or load_config()
    text = prompt.strip()
    low = text.lower()
    reasons = []

    # 1) Mots-clés : la vitesse la plus haute qui matche l'emporte (match en début de mot).
    gear = None
    for g in (4, 3, 2, 1):
        hits = [k for k in cfg["keywords"].get(str(g), [])
                if re.search(r"(?<!\w)" + re.escape(k.lower()), low)]
        if hits:
            gear = g
            reasons.append("mots-clés: " + ", ".join(hits[:3]))
            break
    if gear is None:
        if len(text) < cfg.get("short_prompt_chars", 40):
            gear = 1
            reasons.append("prompt très court")
        else:
            gear = cfg.get("default_gear", 2)
            reasons.append("aucun signal fort")

    # 2) Signaux qui ne peuvent que monter la vitesse.
    def bump(min_gear, why):
        nonlocal gear
        if min_gear > gear:
            gear = min_gear
            reasons.append(why)

    n = len(text)
    for g in (4, 3):
        t = cfg.get("length_chars", {}).get(str(g))
        if t and n >= t:
            bump(g, f"longueur {n} car.")
            break

    exts = "|".join(re.escape(e) for e in cfg.get("file_extensions", []))
    if exts:
        files = set(re.findall(r"[\w\-./\\]*\w\.(?:" + exts + r")(?!\w)", low))
        for g in (4, 3):
            t = cfg.get("files_mentioned", {}).get(str(g))
            if t and len(files) >= t:
                bump(g, f"{len(files)} fichiers mentionnés")
                break

    if any(re.search(p, text, re.M) for p in cfg.get("stack_trace_patterns", [])):
        bump(cfg.get("stack_trace_gear", 3), "stack trace détectée")

    return decision(cfg, gear, " ; ".join(reasons))


if __name__ == "__main__":
    prompt = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(classify(prompt), ensure_ascii=False))
