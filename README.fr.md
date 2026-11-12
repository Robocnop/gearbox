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

- gearbox ne suggère jamais un agent dont le modèle est de rang égal ou supérieur à ton modèle principal (Haiku < Sonnet < Opus < Fable), sauf si tu as forcé la vitesse avec `/gear`.
- **Priorité du modèle principal** : 1) *détecté* via les hooks `SessionStart` / `PostModelSwitch` (valable seulement pour la session où il a été vu), 2) réglé à la main avec `/gear main <haiku|sonnet|opus|fable|auto>`, 3) `main_model` dans `gears.json` (`haiku`, `sonnet`, `opus`, `fable` ; vide = inconnu, pas de limite de rang). `/gear-why` indique la source utilisée. `UserPromptSubmit` ne reçoit pas le modèle et `SessionStart` ne le fournit pas toujours, d'où ces solutions de repli.
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
- `/gear main <haiku|sonnet|opus|fable|auto>` — règle ton modèle principal à la main (utilisé quand aucun n'est détecté).
- `/gear-why` — affiche la décision et la raison du dernier prompt.

## Fiabilité

- **Fail-open** : si quoi que ce soit échoue dans le hook (exception, JSON invalide, fichier manquant, timeout de 3 s), il sort en silence et ton prompt passe sans contexte injecté.
- **Config robuste** : `gears.json` est validé au chargement. Une clé manquante ou invalide prend une valeur par défaut codée en dur ; un fichier absent ou corrompu donne tous les défauts. Rien ne t'est affiché.
- **Données locales, hors du plugin et du dépôt** : `~/.claude/gearbox/state.json` (vitesse forcée, modèle principal manuel et détecté, dernière décision) et `~/.claude/gearbox/gearbox.log` (erreurs et avertissements de config, plafonné à 200 lignes). `GEARBOX_HOME` permet de choisir un autre dossier. Regarde d'abord le log si gearbox semble ne rien faire.

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

[MIT](LICENSE) © 2026 Robocnop

## Limites connues

- **Un hook ne peut pas changer le modèle de la session principale.** gearbox ne fait que *suggérer* une délégation ; c'est le modèle principal qui décide de la suivre (il le fait en général, sans garantie).
- L'économie n'existe que si la session principale tourne sur un modèle au moins aussi cher que l'agent visé, et chaque délégation démarre à froid (l'agent relit le contexte).
- Le champ `effort:` des agents dépend de la version de Claude Code ; s'il est ignoré, la consigne d'effort du prompt système de chaque agent reste active.
- Le classifieur est purement heuristique et se trompe sur les prompts ambigus ; utilise `/gear` pour corriger.
- Les prompts commençant par `/` (slash commands) ne sont pas classés.
- La détection du modèle demande une version de Claude Code qui fournit le champ `model` de `SessionStart` et le hook `PostModelSwitch` ; sur une version plus ancienne, utilise `/gear main` ou `main_model`. Le format exact de la valeur n'est pas supposé : gearbox cherche seulement `haiku`, `sonnet`, `opus` ou `fable` dedans.
- Les blocs de code et les stack traces sont ignorés pour les mots-clés et les négations simples sont gérées ; les phrases à négation complexe peuvent encore être mal jugées.

Voir [CHANGELOG.md](CHANGELOG.md).