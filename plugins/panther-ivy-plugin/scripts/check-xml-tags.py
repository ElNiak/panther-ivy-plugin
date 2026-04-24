#!/usr/bin/env python3
"""Lint the plugin's XML-tag usage in skills, agents, commands, rules.

Checks performed per file:
  1. Reserved template-placeholder tags (substituted by plugin engines) must
     not wrap content — only appear inline as self-closing or paired with
     placeholder text.
  2. <severity class="..." value="..."/> must use one of the three
     orthogonal taxonomies defined in .claude/rules/ivy-formatting.md:
       class="tool-outcome" + value in {PASS, FAIL, WARN}
       class="gate"         + value in {SOUND, UNSOUND, ABSTAIN}
       class="finding"      + value in {ERROR, WARNING, INFO}
  3. <dispatch target="..." via="..."/> must use via in {skill, agent,
     pending_dispatch}.
  4. Paired tags (<role>, <context>, <phase>, <branch>, <outcome>,
     <checkpoint>, <iron-law>, <instructions>, <integration>,
     <anti-rationalization>, <dispatch-context>, <allowed_tools>,
     <forbidden_tools>, <discipline_contract>, <output_schema>, <example>,
     <commentary>) must balance.

Exit status: 0 if all checks pass, 1 otherwise.

Usage:
    python scripts/check-xml-tags.py [file1] [file2] ...
    python scripts/check-xml-tags.py --all
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RESERVED_PLACEHOLDERS = frozenset(
    {"protocol", "project", "file", "timestamp", "workspace"}
)

SEVERITY_VALUES: dict[str, frozenset[str]] = {
    "tool-outcome": frozenset({"PASS", "FAIL", "WARN"}),
    "gate": frozenset({"SOUND", "UNSOUND", "ABSTAIN"}),
    "finding": frozenset({"ERROR", "WARNING", "INFO"}),
}

DISPATCH_VIAS = frozenset({"skill", "agent", "pending_dispatch"})

PAIRED_TAGS = frozenset(
    {
        "role",
        "context",
        "phase",
        "branch",
        "outcome",
        "checkpoint",
        "iron-law",
        "instructions",
        "integration",
        "anti-rationalization",
        "dispatch-context",
        "allowed_tools",
        "forbidden_tools",
        "discipline_contract",
        "output_schema",
        "example",
        "commentary",
        "purpose",
        "thought",
        "rebuttal",
        "catalog_slice",
        "artifact",
        "check_procedure",
    }
)


def lint_file(path: Path) -> list[str]:
    """Return a list of violation strings for the given file."""
    text = path.read_text(encoding="utf-8")
    # Strip fenced code blocks and inline code so we only lint prose tags.
    text_no_fenced = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text_no_inline = re.sub(r"`[^`\n]+`", "", text_no_fenced)
    problems: list[str] = []

    for match in re.finditer(r"<severity\s+([^/>]*)/?>", text_no_inline):
        attrs = _parse_attrs(match.group(1))
        cls = attrs.get("class", "")
        val = attrs.get("value", "")
        if cls not in SEVERITY_VALUES:
            problems.append(
                f"{path}: <severity> has invalid class={cls!r}; expected one of {sorted(SEVERITY_VALUES)}"
            )
            continue
        if val and val not in SEVERITY_VALUES[cls]:
            problems.append(
                f"{path}: <severity class={cls!r}> has invalid value={val!r}; expected one of {sorted(SEVERITY_VALUES[cls])}"
            )

    for match in re.finditer(r"<dispatch\s+([^/>]*)/?>", text_no_inline):
        attrs = _parse_attrs(match.group(1))
        via = attrs.get("via", "")
        if via and via not in DISPATCH_VIAS:
            problems.append(
                f"{path}: <dispatch> has invalid via={via!r}; expected one of {sorted(DISPATCH_VIAS)}"
            )

    for name in RESERVED_PLACEHOLDERS:
        for match in re.finditer(rf"<{name}>([^<]*)</{name}>", text_no_inline):
            body = match.group(1).strip()
            if body and not body.startswith("<"):
                problems.append(
                    f"{path}: reserved placeholder <{name}> wraps content ({body[:40]!r}); placeholders must be self-closing or hold template text only"
                )

    for tag in PAIRED_TAGS:
        opens = len(re.findall(rf"<{tag}(\s[^>]*)?>", text_no_inline))
        closes = len(re.findall(rf"</{tag}>", text_no_inline))
        selfclose = len(re.findall(rf"<{tag}(\s[^>]*)?/>", text_no_inline))
        real_opens = opens - selfclose
        if real_opens != closes:
            problems.append(
                f"{path}: <{tag}> unbalanced — {real_opens} opens, {closes} closes"
            )

    return problems


def _parse_attrs(attr_text: str) -> dict[str, str]:
    return {
        m.group(1): m.group(2)
        for m in re.finditer(r'([a-z_-]+)="([^"]*)"', attr_text)
    }


def find_plugin_files() -> list[Path]:
    plugin_root = Path(__file__).resolve().parent.parent
    patterns = [
        "skills/*/SKILL.md",
        "skills/*/references/*.md",
        "agents/*.md",
        "commands/*.md",
        ".claude/rules/*.md",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(plugin_root.glob(pattern))
    backup_marker = ".backup"
    return [p for p in files if backup_marker not in p.parts]


def main(argv: list[str]) -> int:
    if not argv or argv == ["--all"]:
        files = find_plugin_files()
    else:
        files = [Path(a) for a in argv]

    all_problems: list[str] = []
    for path in files:
        if not path.is_file():
            print(f"SKIP: {path} (not a file)", file=sys.stderr)
            continue
        all_problems.extend(lint_file(path))

    if not all_problems:
        print(f"PASS: {len(files)} files checked, 0 violations")
        return 0

    for prob in all_problems:
        print(prob)
    print(f"FAIL: {len(all_problems)} violations across {len(files)} files")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
