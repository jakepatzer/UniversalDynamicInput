#! /usr/bin/env python3
"""Adds host_controls entries for mappings that combine inputs with OR (`|`).

Dolphin looks up a control's mapping expression verbatim in host_controls, so a
mapping like "`Trigger R` | `Button B`" falls back to the placeholder texture
unless that exact string is a key. For each group below, every ordering is added
(with and without spaces around `|`) and shows the image of the first input.
"""

import json
from collections.abc import Iterator
from itertools import permutations
from pathlib import Path

root_folder = Path(__file__).parent.parent

OR_GROUPS: tuple[tuple[str, ...], ...] = (
    # Buttons/A in the "PrimeHack XInput GamePad" Wiimote profile from
    # https://github.com/shiiion/dolphin/wiki/Controllers-&-GamePads
    ("`Trigger R`", "`Button B`"),
    # The same profile with Xbox A/B swapped so Xbox A presses Wiimote A
    ("`Trigger R`", "`Button A`"),
)


def or_aliases(device_controls: dict[str, str]) -> Iterator[tuple[str, str]]:
    for group in OR_GROUPS:
        # Only devices that name every input in the group can produce this mapping
        if not all(control in device_controls for control in group):
            continue
        for ordering in permutations(group):
            image = device_controls[ordering[0]]
            yield " | ".join(ordering), image
            yield "|".join(ordering), image


def add_or_aliases(host_controls: dict[str, dict[str, str]]) -> bool:
    changed = False
    for device_controls in host_controls.values():
        for alias, image in or_aliases(device_controls):
            if device_controls.get(alias) != image:
                device_controls[alias] = image
                changed = True
    return changed


def main() -> None:
    for json_path in sorted(root_folder.glob("*/UniversalDIT_*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))

        host_controls_maps = [data.get("default_host_controls", {})]
        # #Assets templates have an empty list here instead of an object
        if isinstance(data["output_textures"], dict):
            host_controls_maps += [
                texture.get("host_controls", {})
                for texture in data["output_textures"].values()
            ]

        changed = False
        for host_controls in host_controls_maps:
            changed |= add_or_aliases(host_controls)
        if changed:
            json_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )


if __name__ == "__main__":
    main()
