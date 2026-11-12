# gearbox

[English](README.md) | **Français**

Boîte de vitesses automatique pour Claude Code : chaque prompt est classé localement (zéro appel API) et orienté vers le bon modèle et le bon niveau d'effort.

| Vitesse | Agent | Modèle | Effort | Cas typiques |
|---|---|---|---|---|
| 1 | `gear-haiku` | Haiku 5.5 | low | typo, renommage, formatage |
| 2 | `gear-sonnet` | Sonnet 5.5 | medium | bug simple, tests, petit refactor |
| 3 | `gear-opus` | Opus 5.5 | high | architecture, multi-fichiers, débogage difficile |
| 4 | `gear-opus` (`gear-fable` si activé) | Opus 5.5 (Fable 5.2) | high (xhigh) | conception système, from scratch, sécurité |

La vitesse 0 signifie « pas de délégation » : questions (finissant par `?` ou commençant par quoi/comment/pourquoi/what/how/why…) et prompts courts sans verbe d'action. Le hook n'injecte rien dans ce cas.

Règles de délégation :

- gearbox ne suggère jamais un agent dont le modèle est de rang égal ou supérieur à ton modèle principal (Haiku < Sonnet < Opus < Fable), sauf si tu as forcé la vitesse avec `/gear`. Indique ton modèle avec `main_model` dans `gears.json` (`haiku`, `sonnet`, `opus`, `fable` ; vide désactive la vérification). Claude Code ne transmet pas le modèle actif aux hooks `UserPromptSubmit`, il ne peut donc pas être détecté automatiquement : mets `main_model` à jour quand tu changes de modèle.
- La vitesse 4 utilise `gear-opus` par défaut. `gear-fable` n'est utilisé que si `"allow_fable": true` dans `gears.json`, ou avec `/gear 4`.

## Installation

Prérequis : `python` (3.8+) dans le PATH.

Depuis GitHub :

```
/plugin marketplace add Robocnop/gearbox
/plugin install gearbox@gearbox
```

Depuis un clone local :

```
git clone https://github.com/Robocnop/gearbox.git
/plugin marketplace add ./gearbox
/plugin install gearbox@gearbox
```

Pour un essai sans installation : `claude --plugin-dir ./gearbox`

## Fonctionnement

1. Le hook `UserPromptSubmit` passe le prompt à `scripts/classify.py`.
2. Le classifieur renvoie `{gear, model, effort, reason}` selon `gears.json`.
3. Le hook injecte une ligne de contexte : `[gearbox] vitesse 2 (auto) → déléguer à l'agent gearbox:gear-sonnet …`.
4. La session principale délègue le travail à l'agent indiqué, qui tourne sur son propre modèle.

Commandes :

- `/gear <1-4|auto>` — force une vitesse, ou repasse en automatique.
- `/gear-why` — affiche la décision et la raison du dernier prompt.

L'état est stocké dans `~/.claude/gearbox/state.json`.

## Langue

Les messages (ligne de contexte injectée, sortie de `/gear` et `/gear-why`, raisons) s'affichent en français quand la langue du système est le français, et en anglais sinon. La variable d'environnement `GEARBOX_LANG` (`en` ou `fr`) permet de forcer la langue. Les prompts des agents sont en anglais ; les agents répondent dans la langue de l'utilisateur.

## Modifier `gears.json`

- `gears` : modèle, agent et effort de chaque vitesse.
- `keywords` : mots-clés par vitesse (match en début de mot, insensible à la casse ; la vitesse la plus haute gagne). Des mots-clés anglais et français sont fournis.
- `main_model` / `allow_fable` : voir « Règles de délégation » ci-dessus.
- `zero_gear` : seuils et listes de mots de la vitesse 0 (`short_max_chars`, `question_max_chars`, `question_starters`, `action_verbs`).
- `default_gear` / `short_prompt_chars` : vitesse utilisée sans mot-clé (un prompt très court part en vitesse 1).
- `length_chars`, `files_mentioned` : seuils qui font monter en vitesse 3 ou 4.
- `file_extensions` : extensions comptées comme « fichier mentionné ».
- `stack_trace_patterns` / `stack_trace_gear` : regex de détection de stack trace, et vitesse minimale associée.

Tester une règle : `echo "mon prompt" | python scripts/classify.py`. Lancer les tests : `python -m unittest discover tests`.

Si tu changes le modèle d'une vitesse, change aussi `model:` dans le fichier `agents/gear-*.md` correspondant.

## Licence

Libre d'utilisation, de modification et de redistribution pour n'importe quel usage, à condition de citer le projet d'origine : *Based on gearbox by Robocnop - https://github.com/Robocnop/gearbox*. Voir [LICENSE](LICENSE) (en anglais).

## Limites connues

- **Un hook ne peut pas changer le modèle de la session principale.** gearbox ne fait que *suggérer* une délégation ; c'est le modèle principal qui décide de la suivre (il le fait en général, sans garantie).
- L'économie n'existe que si la session principale tourne sur un modèle au moins aussi cher que l'agent visé, et chaque délégation démarre à froid (l'agent relit le contexte).
- Le champ `effort:` des agents dépend de la version de Claude Code ; s'il est ignoré, la consigne d'effort du prompt système de chaque agent reste active.
- Le classifieur est purement heuristique et se trompe sur les prompts ambigus ; utilise `/gear` pour corriger.
- Les prompts commençant par `/` (slash commands) ne sont pas classés.