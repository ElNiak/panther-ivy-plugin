#!/usr/bin/env python3
"""Compute canonical component counts for the panther-ivy-plugin.

Produces the inventory the README publishes (agents, skills, hooks, rules,
commands). The output is the source of truth; tests/test_readme_counts.py
asserts the README matches.

Run:
    python3 scripts/inventory_counts.py            # human summary
    python3 scripts/inventory_counts.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Directories named *-ops/ are workflow ops skills; "ivy/" is the orchestrator;
# everything else under skills/ is a knowledge skill.
ORCHESTRATOR_SKILL = "ivy"

Inventory = dict[str, Any]


def _list_dirs(parent: Path) -> list[str]:
    return sorted(p.name for p in parent.iterdir() if p.is_dir())


def _list_md(parent: Path, exclude: tuple[str, ...] = ("README.md",)) -> list[str]:
    return sorted(
        p.name for p in parent.iterdir() if p.suffix == ".md" and p.name not in exclude
    )


def count_agents(root: Path) -> Inventory:
    files = _list_md(root / "agents")
    specialists = [n for n in files if n.startswith("ivy-")]
    critics = [n for n in files if n.startswith("g-")]
    return {
        "total": len(files),
        "specialist_count": len(specialists),
        "critic_count": len(critics),
        "specialists": specialists,
        "critics": critics,
    }


def count_skills(root: Path) -> Inventory:
    dirs = _list_dirs(root / "skills")
    orchestrator = [d for d in dirs if d == ORCHESTRATOR_SKILL]
    ops = [d for d in dirs if d.endswith("-ops")]
    knowledge = [d for d in dirs if d not in orchestrator and d not in ops]
    return {
        "total": len(dirs),
        "orchestrator_count": len(orchestrator),
        "ops_count": len(ops),
        "knowledge_count": len(knowledge),
        "ops": ops,
        "knowledge": knowledge,
    }


def count_hooks(root: Path) -> Inventory:
    hooks_json = json.loads((root / "hooks" / "hooks.json").read_text())
    events = hooks_json.get("hooks", {})
    matcher_total = 0
    command_total = 0
    by_event: dict[str, dict[str, int]] = {}
    for event, entries in events.items():
        m = len(entries)
        c = sum(len(e.get("hooks", [])) for e in entries)
        by_event[event] = {"matchers": m, "commands": c}
        matcher_total += m
        command_total += c
    return {
        "event_count": len(events),
        "matcher_total": matcher_total,
        "command_total": command_total,
        "by_event": by_event,
    }


def count_rules(root: Path) -> Inventory:
    files = _list_md(root / ".claude" / "rules")
    return {"total": len(files), "files": files}


def count_commands(root: Path) -> Inventory:
    files = _list_md(root / "commands")
    return {"total": len(files), "files": files}


def collect(root: Path = PLUGIN_ROOT) -> Inventory:
    return {
        "agents": count_agents(root),
        "skills": count_skills(root),
        "hooks": count_hooks(root),
        "rules": count_rules(root),
        "commands": count_commands(root),
    }


def render_summary(inv: Inventory) -> str:
    a = inv["agents"]
    s = inv["skills"]
    h = inv["hooks"]
    return "\n".join(
        [
            "panther-ivy-plugin inventory",
            "============================",
            f"Agents:   {a['total']} ({a['specialist_count']} specialist + {a['critic_count']} critic)",
            f"Skills:   {s['total']} ({s['orchestrator_count']} orchestrator + {s['ops_count']} ops + {s['knowledge_count']} knowledge)",
            f"Hooks:    {h['command_total']} commands / {h['matcher_total']} matchers across {h['event_count']} events",
            f"Rules:    {inv['rules']['total']}",
            f"Commands: {inv['commands']['total']}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of summary")
    args = parser.parse_args(argv)

    inv = collect()
    if args.json:
        print(json.dumps(inv, indent=2))
    else:
        print(render_summary(inv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
