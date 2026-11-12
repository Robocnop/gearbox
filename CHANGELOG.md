# Changelog

## 0.4.0

Reliability release.

- **Main model detection**: the active model is read from the `SessionStart` (`model`) and `PostModelSwitch` (`to_model`) hooks and stored in the state file. New `/gear main <haiku|sonnet|opus|fable|auto>`. Priority: detected > `/gear main` > `gears.json`; `/gear-why` shows the source used.
- **Fail-open hook**: any exception, invalid JSON, missing file or timeout exits 0 silently and the prompt goes through without injected context. Hook timeout is 3 s. Errors go to a local log capped at 200 lines.
- **Robust config**: `gears.json` is validated on load; a missing or invalid key falls back to a built-in default with a warning in the log. A broken file never breaks the plugin.
- **Better classifier**: code blocks and stack traces are ignored for keyword detection (a stack trace is only a boolean signal); simple negations ("pas besoin de tester", "don't refactor"); accents and case are normalized (FR/EN).
- **State and log outside the repo**: `~/.claude/gearbox/state.json` and `gearbox.log` (override the folder with `GEARBOX_HOME`); `.gitignore` updated.
- **Tests and CI**: 15 tests (18 classified prompts, main-model priority, rank rule, fail-open hook, corrupt config/state, capped log) and a GitHub Actions workflow (Ubuntu + Windows, Python 3.9 + 3.13, stdlib only).

## 0.3.0

- Gear 0 ("no delegation") for questions and short prompts without an action verb.
- Never delegates to a model at or above the main model (`main_model`), unless the gear is forced with `/gear`.
- Gear 4 uses `gear-opus` unless `allow_fable` is true or the gear is forced.
- MIT license.

## 0.2.0

- Messages in English or French depending on the system language (`GEARBOX_LANG` to override).

## 0.1.0

- Local classifier, `UserPromptSubmit` hook, four gear agents, `/gear` and `/gear-why`.
