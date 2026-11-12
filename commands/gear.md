---
description: Force the gearbox gear (1-4), go back to automatic, or set the main model
argument-hint: <1-4|auto> | main <haiku|sonnet|opus|fable|auto>
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/gear.py" set $ARGUMENTS`

Repeat the result above to the user verbatim, in one line, and do nothing else.
