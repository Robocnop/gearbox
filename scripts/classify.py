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
import unicodedata
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
    "negations": ["pas besoin", "pas la peine", "inutile", "sans", "ne pas", "ne fais pas", "ne faites pas",
                  "jamais", "au lieu de", "don't", "dont", "do not", "never", "no need", "without", "avoid",
                  "skip", "instead of"],
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
    scalar("negations", _strs)
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


FENCE = re.compile(r"```.*?(?:```|\Z)", re.S)


def norm(s):
    """Lower-case, strip accents, unify apostrophes, so FR/EN matching ignores them."""
    s = unicodedata.normalize("NFKD", s.replace("’", "'").replace("‘", "'"))
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def hit(text, word):
    """True if `word` (accent/case-insensitive) occurs at the start of a word in normalized text."""
    return re.search(r"(?<!\w)" + re.escape(norm(word)), text) is not None


def has_trace(text, patterns):
    return any(re.search(p, text, re.M) for p in patterns)


def strip_traces(text, patterns):
    """Drop stack-trace blocks: from the first matching line up to the next blank line."""
    out, skipping = [], False
    for line in text.splitlines():
        if any(re.search(p, line) for p in patterns):
            skipping = True
        elif not line.strip():
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out)


def strip_negations(text, phrases):
    """Remove negated fragments ("pas besoin de tester", "don't refactor") from normalized text."""
    alts = sorted({r"\s+".join(re.escape(w) for w in norm(p).split()) for p in phrases if norm(p).strip()},
                  key=len, reverse=True)
    if not alts:
        return text
    return re.sub(r"(?<!\w)(?:" + "|".join(alts) + r")(?:\s+[\w'-]+){1,2}", " ", text)


def classify(prompt, cfg=None):
    cfg = cfg or load_config()
    raw = prompt.strip()
    pats = cfg["stack_trace_patterns"]
    trace = has_trace(raw, pats)  # a stack trace is only a boolean signal
    clean = strip_traces(FENCE.sub(" ", raw), pats).strip()  # no code blocks, no traces
    nk = norm(clean)
    kw = strip_negations(nk, cfg["negations"])  # text used for keyword / verb detection
    n = len(clean)
    reasons = []

    # 0) No delegation: a question, or a short prompt without action verb.
    z = cfg["zero_gear"]
    is_q = clean.endswith("?") or any(re.match(re.escape(norm(s)) + r"\b", nk) for s in z["question_starters"])
    if is_q and n <= z["question_max_chars"]:
        return decision(cfg, 0, t("g0_question"))
    if n < z["short_max_chars"] and not trace and not any(hit(kw, v) for v in z["action_verbs"]):
        return decision(cfg, 0, t("g0_short"))

    # 1) Keywords: the highest matching gear wins.
    level = None
    for g in (4, 3, 2, 1):
        hits = [k for k in cfg["keywords"][str(g)] if hit(kw, k)]
        if hits:
            level = g
            reasons.append(t("kw", x=", ".join(hits[:3])))
            break
    if level is None:
        if n < cfg["short_prompt_chars"]:
            level = 1
            reasons.append(t("short"))
        else:
            level = cfg["default_gear"]
            reasons.append(t("nosignal"))

    # 2) Signals that can only raise the gear.
    def bump(min_gear, why):
        nonlocal level
        if min_gear > level:
            level = min_gear
            reasons.append(why)

    for g in (4, 3):
        if len(raw) >= cfg["length_chars"][str(g)]:
            bump(g, t("length", n=len(raw)))
            break

    exts = "|".join(re.escape(e) for e in cfg["file_extensions"])
    files = set(re.findall(r"[\w\-./\\]*\w\.(?:" + exts + r")(?!\w)", nk))
    for g in (4, 3):
        if len(files) >= cfg["files_mentioned"][str(g)]:
            bump(g, t("files", n=len(files)))
            break

    if trace:
        bump(cfg["stack_trace_gear"], t("trace"))

    return decision(cfg, level, " ; ".join(reasons))


if __name__ == "__main__":
    prompt = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(classify(prompt), ensure_ascii=False))
