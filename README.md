# gearbox

**English** | [Français](README.fr.md)

Automatic gear shifting for Claude Code: every prompt is classified locally (zero API calls) and routed to the right model and effort level.

| Gear | Agent | Model | Effort | Typical work |
|---|---|---|---|---|
| 1 | `gear-haiku` | Haiku 5.5 | low | typo, rename, formatting |
| 2 | `gear-sonnet` | Sonnet 5.5 | medium | simple bug, tests, small refactor |
| 3 | `gear-opus` | Opus 5.5 | high | architecture, multi-file changes, hard debugging |
| 4 | `gear-opus` (`gear-fable` if enabled) | Opus 5.5 (Fable 5.2) | high (xhigh) | system design, from scratch, security |

Gear 0 means "no delegation": questions (ending with `?` or starting with what/how/why/quoi/comment/pourquoi…) and short prompts without an action verb. The hook injects nothing for them.

Delegation rules:

- gearbox never suggests an agent whose model ranks at or above your main model (Haiku < Sonnet < Opus < Fable), unless you forced the gear with `/gear`. Tell it which model you use with `main_model` in `gears.json` (`haiku`, `sonnet`, `opus`, `fable`; empty disables the check). Claude Code does not pass the active model to `UserPromptSubmit` hooks, so it cannot be detected automatically: update `main_model` when you switch models.
- Gear 4 uses `gear-opus` by default. `gear-fable` is only used if `"allow_fable": true` in `gears.json`, or with `/gear 4`.

## Install

Requires `python` (3.8+) on your PATH.

From GitHub:

```
/plugin marketplace add Robocnop/gearbox
/plugin install gearbox@gearbox
```

From a local clone:

```
git clone https://github.com/Robocnop/gearbox.git
/plugin marketplace add ./gearbox
/plugin install gearbox@gearbox
```

To try it without installing: `claude --plugin-dir ./gearbox`

## How it works

1. The `UserPromptSubmit` hook sends your prompt to `scripts/classify.py`.
2. The classifier returns `{gear, model, effort, reason}` based on `gears.json`.
3. The hook injects one line of context: `[gearbox] gear 2 (auto) → delegate to agent gearbox:gear-sonnet …`.
4. The main session delegates the work to that agent, which runs on its own model.

Commands:

- `/gear <1-4|auto>` — force a gear, or go back to automatic.
- `/gear-why` — show the decision and the reason for the last prompt.

State is stored in `~/.claude/gearbox/state.json`.

## Language

Messages (the injected context line, `/gear` and `/gear-why` output, reasons) are shown in French when the system language is French, and in English otherwise. Set the `GEARBOX_LANG` environment variable to `en` or `fr` to override. Agent prompts are in English; agents answer in the user's language.

## Customising `gears.json`

- `gears`: model, agent and effort for each gear.
- `keywords`: keywords per gear (matched at the start of a word, case-insensitive; the highest matching gear wins). English and French keywords are included.
- `main_model` / `allow_fable`: see "Delegation rules" above.
- `zero_gear`: gear 0 thresholds and word lists (`short_max_chars`, `question_max_chars`, `question_starters`, `action_verbs`).
- `default_gear` / `short_prompt_chars`: gear used when no keyword matches (a very short prompt goes to gear 1).
- `length_chars`, `files_mentioned`: thresholds that shift up to gear 3 or 4.
- `file_extensions`: extensions counted as a "mentioned file".
- `stack_trace_patterns` / `stack_trace_gear`: regexes that detect a stack trace, and the minimum gear it triggers.

Test a rule: `echo "my prompt" | python scripts/classify.py`. Run the test suite: `python -m unittest discover tests`.

If you change the model of a gear, also change `model:` in the matching `agents/gear-*.md`.

## License

[MIT](LICENSE) © 2026 Robocnop

## Known limitations

- **A hook cannot change the model of the main session.** gearbox only *suggests* a delegation; the main model decides whether to follow it (it usually does, with no guarantee).
- You only save quota when the main session runs on a model at least as expensive as the target agent, and every delegation starts cold (the agent re-reads the context).
- The agents' `effort:` field depends on your Claude Code version; if it is ignored, the effort guidance in each agent's system prompt still applies.
- The classifier is purely heuristic and will misjudge ambiguous prompts; use `/gear` to override.
- Prompts starting with `/` (slash commands) are not classified.