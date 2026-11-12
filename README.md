# gearbox

Boîte de vitesses automatique pour Claude Code : chaque prompt est classé localement (zéro appel API) et orienté vers le bon modèle et le bon niveau d'effort.

| Vitesse | Agent | Modèle | Effort | Cas typiques |
|---|---|---|---|---|
| 1 | `gear-haiku` | Haiku 5.5 | low | typo, renommage, formatage |
| 2 | `gear-sonnet` | Sonnet 5.5 | medium | bug simple, tests, petit refactor |
| 3 | `gear-opus` | Opus 5.5 | high | architecture, multi-fichiers, débogage difficile |
| 4 | `gear-fable` | Fable 5.2 | xhigh | conception système, from scratch, sécurité |

## Installation (locale)

Prérequis : `python` (3.8+) dans le PATH.

```
/plugin marketplace add C:\Users\roboc\Documents\gearbox
/plugin install gearbox@gearbox-local
```

Ou, pour un essai sans installation : `claude --plugin-dir C:\Users\roboc\Documents\gearbox`

## Fonctionnement

1. Le hook `UserPromptSubmit` passe le prompt à `scripts/classify.py`.
2. Le classifieur renvoie `{gear, model, effort, reason}` selon `gears.json`.
3. Le hook injecte une ligne de contexte : `[gearbox] vitesse 2 (auto) → déléguer à l'agent gearbox:gear-sonnet …`.
4. La session principale délègue le travail à l'agent indiqué, qui tourne sur son propre modèle.

Commandes :
- `/gear <1-4|auto>` — force une vitesse, ou repasse en automatique.
- `/gear-why` — affiche la décision et la raison du dernier prompt.

État : `~/.claude/gearbox/state.json`.

## Modifier `gears.json`

- `gears` : modèle, agent et effort de chaque vitesse.
- `keywords` : mots-clés par vitesse (match en début de mot, insensible à la casse ; la vitesse la plus haute gagne).
- `default_gear` / `short_prompt_chars` : vitesse sans mot-clé (prompt très court → 1).
- `length_chars`, `files_mentioned` : seuils qui font monter en vitesse 3 / 4.
- `file_extensions` : extensions comptées comme « fichier mentionné ».
- `stack_trace_patterns` / `stack_trace_gear` : regex de détection de stack trace et vitesse minimale associée.

Tester une règle : `echo "mon prompt" | python scripts/classify.py`

Si tu changes le modèle d'une vitesse, change aussi `model:` dans `agents/gear-*.md`.

## Limites connues

- **Un hook ne peut pas changer le modèle de la session principale.** gearbox ne fait que *suggérer* une délégation ; c'est le modèle principal qui décide de suivre (il le fait en général, sans garantie).
- L'économie n'existe que si la session principale tourne sur un modèle au moins aussi cher que l'agent visé ; chaque délégation démarre à froid (l'agent relit le contexte).
- Le champ `effort:` des agents dépend de la version de Claude Code ; s'il est ignoré, la consigne d'effort du prompt système reste active.
- Classifieur purement heuristique : il se trompe sur les prompts ambigus → `/gear` pour corriger.
- Les prompts commençant par `/` (slash commands) ne sont pas classés.
