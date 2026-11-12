---
description: Show the gearbox decision (gear, model, reason) for the last prompt
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/gear.py" why`

Show the result above to the user verbatim and do nothing else.
