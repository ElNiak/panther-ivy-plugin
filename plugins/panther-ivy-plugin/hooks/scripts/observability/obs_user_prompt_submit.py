#!/usr/bin/env python3
"""Observability hook: UserPromptSubmit — logs user prompt metadata."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    prompt = data.get("prompt", "")

    log_event(
        "UserPromptSubmit",
        session_id,
        {
            "prompt_length": len(prompt) if isinstance(prompt, str) else 0,
            "prompt_preview": prompt[:100] if isinstance(prompt, str) else "",
        },
    )
except Exception:
    pass
