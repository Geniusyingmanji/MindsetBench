"""Text-level split downgrade for case YAML files.

The v1 YAML files rely on anchors/aliases (``&source`` / ``*source``) that a
``yaml.safe_load`` → ``yaml.dump`` round trip would destroy, so the downgrade is
applied as a line-level edit: ``split: calibration`` → ``split: sanity`` plus a
``history_note`` documenting why, for the case ids listed in a JSON plan.

Usage::

    python scripts/downgrade_to_sanity.py plan.json

where ``plan.json`` maps a YAML path to ``{"note": "...", "case_ids": [...] | "*"}``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CASE_START = re.compile(r"^- id: (\S+)\s*$")
SPLIT_LINE = re.compile(r"^  split: (\S+)\s*$")


def downgrade_file(path: Path, note: str, case_ids: set[str] | None) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changed: list[str] = []
    current: str | None = None
    output: list[str] = []
    for line in lines:
        start = CASE_START.match(line)
        if start:
            current = start.group(1)
        split = SPLIT_LINE.match(line)
        if split and current and (case_ids is None or current in case_ids):
            if split.group(1) != "sanity":
                output.append("  split: sanity\n")
                output.append("  history_note: >-\n")
                output.append(f"    {note}\n")
                changed.append(current)
                continue
        output.append(line)
    if changed:
        path.write_text("".join(output), encoding="utf-8")
    return changed


def main(argv: list[str]) -> int:
    plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    total = 0
    for relative, spec in plan.items():
        ids = spec["case_ids"]
        selected = None if ids == "*" else set(ids)
        changed = downgrade_file(Path(relative), spec["note"], selected)
        total += len(changed)
        print(f"{relative}: {len(changed)} downgraded")
    print(f"total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
