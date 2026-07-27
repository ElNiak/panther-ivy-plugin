"""README count parity test.

The plugin README publishes component counts (agents, skills, hooks, rules,
commands) in two places: the Components table and the directory-tree
comments. The counts are the source of truth for new contributors orienting
in the codebase.

This test:
  1. Runs ``scripts/inventory_counts.py`` to compute current on-disk counts.
  2. Reads the plugin README.
  3. Asserts each count claim in the README matches the live inventory.

If this test fails after a structural change, regenerate the counts
(``python3 scripts/inventory_counts.py``) and update the README's two
count surfaces (Components table near line 50; directory-tree comments
near line 138).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

Inventory = dict[str, Any]

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "scripts" / "inventory_counts.py"
README = PLUGIN_ROOT.parent.parent / "README.md"


def _load_inventory() -> Inventory:
    spec = importlib.util.spec_from_file_location("inventory_counts", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.collect(PLUGIN_ROOT)


@pytest.fixture(scope="module")
def inventory() -> Inventory:
    return _load_inventory()


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text()


def test_components_table_agents(inventory: Inventory, readme_text: str) -> None:
    a = inventory["agents"]
    expected = f"{a['total']} ({a['specialist_count']} specialist + {a['critic_count']} critic)"
    assert expected in readme_text, (
        f"README Components-table 'Agents' row should claim '{expected}'; "
        f"if components changed, run scripts/inventory_counts.py and update the README."
    )


def test_components_table_commands(inventory: Inventory, readme_text: str) -> None:
    c = inventory["commands"]
    expected = f"{c['total']} (shortcuts)"
    assert expected in readme_text, (
        f"README Components-table 'Commands' row should claim '{expected}'."
    )


def test_components_table_skills(inventory: Inventory, readme_text: str) -> None:
    s = inventory["skills"]
    expected = (
        f"{s['total']} ({s['orchestrator_count']} orchestrator + "
        f"{s['ops_count']} ops + {s['knowledge_count']} knowledge)"
    )
    assert expected in readme_text, (
        f"README Components-table 'Skills' row should claim '{expected}'."
    )


def test_components_table_hooks(inventory: Inventory, readme_text: str) -> None:
    h = inventory["hooks"]
    expected = (
        f"{h['command_total']} commands / {h['matcher_total']} matchers "
        f"across {h['event_count']} events"
    )
    assert expected in readme_text, (
        f"README Components-table 'Hooks' row should claim '{expected}'."
    )


def test_components_table_rules(inventory: Inventory, readme_text: str) -> None:
    r = inventory["rules"]
    needle = f"| Rules | {r['total']} |"
    assert needle in readme_text, (
        f"README Components-table 'Rules' row should claim {r['total']}."
    )


def test_directory_tree_hooks_count(inventory: Inventory, readme_text: str) -> None:
    h = inventory["hooks"]
    expected = (
        f"{h['command_total']} commands / {h['matcher_total']} matchers "
        f"across {h['event_count']} events"
    )
    assert readme_text.count(expected) >= 2, (
        "README hooks count should appear in both the Components table and "
        f"the directory-tree comment ('{expected}' x2)."
    )


def test_directory_tree_skills_count(inventory: Inventory, readme_text: str) -> None:
    s = inventory["skills"]
    needle = (
        f"# {s['total']} skills: {s['orchestrator_count']} orchestrator "
        f"+ {s['ops_count']} ops + {s['knowledge_count']} knowledge"
    )
    assert needle in readme_text, (
        f"README directory-tree skills comment should read '{needle}'."
    )


def test_directory_tree_agents_count(inventory: Inventory, readme_text: str) -> None:
    a = inventory["agents"]
    needle = (
        f"# {a['total']} agents: {a['specialist_count']} specialist (ivy-*) "
        f"+ {a['critic_count']} critic (g-*)"
    )
    assert needle in readme_text, (
        f"README directory-tree agents comment should read '{needle}'."
    )


def test_directory_tree_commands_count(inventory: Inventory, readme_text: str) -> None:
    c = inventory["commands"]
    needle = f"# {c['total']} shortcut commands"
    assert needle in readme_text, (
        f"README directory-tree commands comment should read '{needle}'."
    )
