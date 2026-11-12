#!/usr/bin/env python3
"""gearbox — messages in English or French, picked from the system language.

Override with the GEARBOX_LANG environment variable ("en" or "fr").
"""
import locale
import os

MESSAGES = {
    "en": {
        "kw": "keywords: {x}",
        "short": "very short prompt",
        "nosignal": "no strong signal",
        "length": "length {n} chars",
        "files": "{n} files mentioned",
        "trace": "stack trace detected",
        "g0_question": "question, no delegation",
        "g0_short": "short prompt without action verb, no delegation",
        "fable_off": "Fable disabled (allow_fable=false) → Opus",
        "capped": "no delegation: {model} ranks at or above the main model ({main})",
        "why_nodeleg": "Gear 0 → no delegation",
        "forced_reason": "gear forced via /gear",
        "mode_auto": "auto",
        "mode_forced": "forced",
        "ctx": ("[gearbox] gear {gear} ({mode}) → delegate to agent gearbox:{agent} ({model_name}), "
                "effort {effort}. Reason: {reason}. Delegate this request to that agent via the Agent tool "
                "(complete, self-contained brief), unless it is a simple conversational exchange or the "
                "user explicitly declines."),
        "set_auto": "[gearbox] auto mode: the classifier picks the gear again.",
        "set_forced": "[gearbox] gear forced to {g} (until `/gear auto`).",
        "usage": "[gearbox] usage: /gear <1-4|auto> | /gear main <haiku|sonnet|opus|fable|auto> — currently: {cur}.",
        "set_main": "[gearbox] main model set to {m} (used unless a model is detected).",
        "set_main_auto": "[gearbox] manual main model cleared.",
        "why_main": "Main model: {main} (source: {source})",
        "src_detected": "detected",
        "src_manual": "/gear main",
        "src_config": "gears.json",
        "src_none": "unknown, no rank limit",
        "cur_forced": "forced to {g}",
        "why_mode": "[gearbox] mode: {cur}",
        "none": "No decision recorded yet.",
        "why_last": "Last prompt ({at}): {prompt}",
        "why_gear": "Gear {gear} → agent {agent} ({model_name}), effort {effort}",
        "why_reason": "Reason: {reason}",
    },
    "fr": {
        "kw": "mots-clés: {x}",
        "short": "prompt très court",
        "nosignal": "aucun signal fort",
        "length": "longueur {n} car.",
        "files": "{n} fichiers mentionnés",
        "trace": "stack trace détectée",
        "g0_question": "question, pas de délégation",
        "g0_short": "prompt court sans verbe d'action, pas de délégation",
        "fable_off": "Fable désactivé (allow_fable=false) → Opus",
        "capped": "pas de délégation : {model} est de rang égal ou supérieur au modèle principal ({main})",
        "why_nodeleg": "Vitesse 0 → pas de délégation",
        "forced_reason": "vitesse forcée via /gear",
        "mode_auto": "auto",
        "mode_forced": "forcée",
        "ctx": ("[gearbox] vitesse {gear} ({mode}) → déléguer à l'agent gearbox:{agent} ({model_name}), "
                "effort {effort}. Raison : {reason}. Délègue l'exécution de cette demande à cet agent via "
                "l'outil Agent (brief complet et autonome), sauf simple échange conversationnel ou refus "
                "explicite de l'utilisateur."),
        "set_auto": "[gearbox] mode auto : la vitesse est de nouveau choisie par le classifieur.",
        "set_forced": "[gearbox] vitesse forcée sur {g} (jusqu'à `/gear auto`).",
        "usage": "[gearbox] usage : /gear <1-4|auto> | /gear main <haiku|sonnet|opus|fable|auto> — actuellement : {cur}.",
        "set_main": "[gearbox] modèle principal réglé sur {m} (utilisé tant qu'aucun modèle n'est détecté).",
        "set_main_auto": "[gearbox] modèle principal manuel effacé.",
        "why_main": "Modèle principal : {main} (source : {source})",
        "src_detected": "détecté",
        "src_manual": "/gear main",
        "src_config": "gears.json",
        "src_none": "inconnu, pas de limite de rang",
        "cur_forced": "forcée sur {g}",
        "why_mode": "[gearbox] mode : {cur}",
        "none": "Aucune décision enregistrée pour l'instant.",
        "why_last": "Dernier prompt ({at}) : {prompt}",
        "why_gear": "Vitesse {gear} → agent {agent} ({model_name}), effort {effort}",
        "why_reason": "Raison : {reason}",
    },
}


def lang():
    v = os.environ.get("GEARBOX_LANG", "")
    if not v:
        try:
            if os.name == "nt":
                import ctypes
                v = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
            else:
                v = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
                     or os.environ.get("LANG") or "")
        except Exception:
            v = ""
    return "fr" if v.lower().startswith("fr") else "en"


def t(key, **kw):
    return MESSAGES[lang()][key].format(**kw)
