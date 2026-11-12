#!/usr/bin/env python3
"""gearbox — classifieur local (stdlib uniquement, zéro appel API).

stdin : le prompt.  stdout : JSON {gear, model, effort, reason, ...}.
Les règles vivent dans gears.json (à la racine du plugin).
"""
import copy
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gear  # noqa: E402
from i18n import t  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "gears.json"
RANK = {"haiku": 1, "sonnet": 2, "opus": 3, "fable": 4}


# Built-in defaults: used for any missing/invalid key, or when gears.json is unusable.
# Kept identical to the shipped gears.json (a test enforces it).
DEFAULTS = {
    "gears": {
        "1": {"model": "haiku", "model_name": "Haiku 5.5", "agent": "gear-haiku", "effort": "low"},
        "2": {"model": "sonnet", "model_name": "Sonnet 5.5", "agent": "gear-sonnet", "effort": "medium"},
        "3": {"model": "opus", "model_name": "Opus 5.5", "agent": "gear-opus", "effort": "high"},
        "4": {"model": "fable", "model_name": "Fable 5.2", "agent": "gear-fable", "effort": "xhigh"},
    },
    "default_gear": 2,
    "short_prompt_chars": 40,
    "main_model": "sonnet",
    "allow_fable": False,
    "zero_gear": {
        "short_max_chars": 60,
        "question_max_chars": 400,
        "question_starters": ["quoi", "comment", "pourquoi", "quand", "quel", "quelle", "quels", "quelles",
                              "qui", "est-ce", "what", "how", "why", "when", "where", "which", "who"],
        "action_verbs": ["fix", "add", "create", "write", "make", "build", "implement", "refactor", "rename",
                         "remove", "delete", "update", "change", "run", "test", "debug", "install", "generate",
                         "optimi", "migrat", "corrige", "ajoute", "crée", "cree", "écris", "ecris", "fais",
                         "implémente", "implemente", "supprime", "modifie", "lance", "teste", "renomme",
                         "génère", "genere", "conçois", "concois", "construis", "installe", "migre"],
    },
    "keywords": {
        "1": ["typo", "rename", "renomme", "format", "lint", "indent", "faute", "orthograph", "whitespace"],
        "2": ["bug", "test", "refactor", "erreur", "error", "implement", "implémente", "ajoute", "function",
              "fonction", "endpoint"],
        "3": ["architecture", "multi-fichier", "multi-file", "plusieurs fichiers", "multiple files", "across",
              "migration", "migrate", "performance", "optimi", "race condition", "deadlock", "memory leak",
              "fuite mémoire", "intermittent", "flaky", "concurren"],
        "4": ["from scratch", "de zéro", "system design", "conception système", "conçois", "distributed",
              "distribué", "sécurité", "security", "vulnérab", "vulnerab", "threat model", "cryptograph",
              "preuve", "proof", "trade-off", "scalab"],
    },
    "length_chars": {"3": 800, "4": 2500},
    "files_mentioned": {"3": 3, "4": 7},
    "file_extensions": ["py", "js", "jsx", "ts", "tsx", "json", "md", "lua", "luau", "cs", "java", "kt", "go",
                        "rs", "c", "h", "cpp", "hpp", "rb", "php", "html", "css", "scss", "sql", "sh", "ps1",
                        "yml", "yaml", "toml", "xml", "vue", "swift"],
    "stack_trace_gear": 3,
    "stack_trace_patterns": [r"Traceback \(most recent call last\)", r'File ".+", line \d+',
                             r"^\s+at .+[(:]\d+", r"Exception in thread", r"^panic: ", r"error\[E\d+\]",
                             r"stack traceback:"],
}


def _int(lo, hi):
    return lambda v: isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


def _strs(v):
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def _regexes(v):
    if not _strs(v):
        return False
    try:
        for p in v:
            re.compile(p)
    except re.error:
        return False
    return True


def validate(raw):
    """Merge raw (parsed gears.json) over DEFAULTS. Returns (config, warnings)."""
    cfg, warns = copy.deepcopy(DEFAULTS), []
    if not isinstance(raw, dict):
        return cfg, ["gears.json is not a JSON object"]

    def scalar(key, ok):
        if key not in raw:
            warns.append(f"missing {key}")
        elif ok(raw[key]):
            cfg[key] = copy.deepcopy(raw[key])
        else:
            warns.append(f"invalid {key}")

    def table(key, checks):
        src = raw.get(key)
        if not isinstance(src, dict):
            warns.append(f"invalid {key}")
            return
        for k, ok in checks.items():
            if k not in src:
                warns.append(f"missing {key}.{k}")
            elif ok(src[k]):
                cfg[key][k] = copy.deepcopy(src[k])
            else:
                warns.append(f"invalid {key}.{k}")

    scalar("default_gear", _int(1, 4))
    scalar("short_prompt_chars", _int(0, 100000))
    scalar("main_model", lambda v: isinstance(v, str) and (v == "" or v in RANK))
    scalar("allow_fable", lambda v: isinstance(v, bool))
    scalar("stack_trace_gear", _int(1, 4))
    scalar("file_extensions", _strs)
    scalar("stack_trace_patterns", _regexes)
    table("zero_gear", {"short_max_chars": _int(0, 100000), "question_max_chars": _int(0, 100000),
                        "question_starters": _strs, "action_verbs": _strs})
    table("keywords", {k: _strs for k in "1234"})
    table("length_chars", {k: _int(1, 10 ** 6) for k in "34"})
    table("files_mentioned", {k: _int(1, 1000) for k in "34"})

    gears = raw.get("gears")
    if isinstance(gears, dict):
        for k in "1234":
            entry = gears.get(k)
            if not isinstance(entry, dict):
                warns.append(f"invalid gears.{k}")
                continue
            for f in ("model", "model_name", "agent", "effort"):
                v = entry.get(f)
                if isinstance(v, str) and v.strip() and (f != "model" or v in RANK):
                    cfg["gears"][k][f] = v
                else:
                    warns.append(f"invalid gears.{k}.{f}")
    else:
        warns.append("invalid gears")
    return cfg, warns


def load_config(path=None):
    """Never raises: a missing/corrupt gears.json falls back to DEFAULTS (warnings go to the log)."""
    path = path or os.environ.get("GEARBOX_CONFIG") or CONFIG
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        gear.log(f"gears.json unusable ({type(e).__name__}): built-in defaults used")
        return copy.deepcopy(DEFAULTS)
    cfg, warns = validate(raw)
    for w in warns:
        gear.log(f"gears.json: {w} -> default used")
    return cfg


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
