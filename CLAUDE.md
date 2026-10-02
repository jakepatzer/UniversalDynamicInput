# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A texture pack for Dolphin's [Dynamic Input Textures](https://forums.dolphin-emu.org/Thread-introducing-dynamic-input-textures-a-new-feature-for-controller-icons) feature. The pack is almost all data (PNGs and JSON). Dolphin reads it at runtime to replace in-game button prompts with icons for the user's actual controller. The repo root **is** the `DynamicInputTextures` folder: users clone it into Dolphin's `Load/` directory. There is no build and there are no tests.

Contributor guides live on the GitHub wiki: [Create a Package](https://github.com/Venomalia/UniversalDynamicInput/wiki/Create-a-Package) and [Add a Devices](https://github.com/Venomalia/UniversalDynamicInput/wiki/Add-a-Devices).

## Commands

```sh
pre-commit run --all-files                              # all formatters/linters + asset generator
python "#DefaultDevices/generate_alternate_assets.py"   # regenerate derived device images only (needs imageio, numpy, tqdm; hook pins py3.12)
python "#Assets/generate_or_aliases.py"                 # add OR-mapping keys to every template and game JSON (stdlib only, idempotent)
```

pre-commit.ci runs the same hooks on PRs and pushes its auto-fixes back (that's where the `[pre-commit.ci] auto fixes` commits come from). The hooks:

- `pretty-format-json --autofix --no-ensure-ascii --no-sort-keys`: JSON is reformatted to 2-space indent, key order is preserved, and non-ASCII stays literal. Prettier is deliberately excluded from JSON.
- Prettier handles Markdown and YAML. Ruff lints and formats the Python.
- LF line endings are enforced, and `check-case-conflict` rejects paths that differ only by case.
- `generate_alternate_assets` runs on **every** commit (`pass_filenames: false`) and rebuilds all derived image folders.
- `generate_or_aliases` runs whenever a JSON file is staged.

## Architecture

Data moves through three layers:

### 1. `#DefaultDevices/<Device>/<Style>/<Key>.png`: source button images

Each physical controller (`XBOX ONE`, `DualShock4`, `Switch_Pro Controller`, `Steam Deck`, `Wii_Remote`, …) has one subfolder per visual style: `Defaultstyle`, `Flat`, `Simple-Default`, `Text-Default`, `Text-Outlines`, plus the `*_Pressed` and `*_Mask` variants. `Device/Icon.png` is the controller icon. File names are the controller's own button names (`Button A.png`, `Cross.png`, `Pad NS.png`, …).

**Derived folders: never edit them by hand.** `_Mirror/`, `_Rotated90/`, `_TwoPalettes_RG/` and `_TwoPalettes_BA/` are committed outputs of `generate_alternate_assets.py`. The script deletes them and rebuilds them from every source PNG:

- `_Mirror`: a vertical flip (`flipud`) of every image, for games that store textures upside-down.
- `_Rotated90`: produced only from `Defaultstyle` sources.
- `_TwoPalettes_RG` / `_TwoPalettes_BA`: channel-remapped copies, made only from color `Flat` images that are not `_Mask` images, plus every `Device/Icon.png`. They are also produced under `_Mirror/`.

If you add a style or device that one of these variants needs, update the filters in the script. Do not add files to the derived folders.

### 2. `#Assets/UniversalDIT_<Style>[_Variant].json`: style templates

Each template holds one `default_host_controls` map. It works like this:

- Top-level keys are Dolphin host device strings in the form `<backend>/<index>/<device name>`, e.g. `XInput/0/Gamepad`, `SDL/0/DualSense Wireless Controller`, `evdev/0/...`, `DInput/0/...`, `Android/1/...`.
- Inside each device entry, Dolphin input expressions map to a texture path. Expressions appear both backtick-quoted (`` `Button A` ``) and bare. The entry whose key equals the device string itself points to `Device/Icon.png`.
- Paths are relative to a _game_ folder: `../#DefaultDevices/<Device>/<Style>/<Key>.png`. Both `\\` and `/` separators exist in the data.
- Many host device strings share one image folder. Most Xbox-like pads map to `XBOX ONE` and most PlayStation pads map to `DualShock4`.

To support a new controller, add its device-string entry to **every** template.

**Dolphin matches the whole mapping expression as one string.** Before the lookup, it reads the controller's mapping expression from the controller ini and does not parse it. If the exact string isn't a key in the device map, Dolphin leaves the base image untouched, which usually shows the pack's `?` placeholder. A mapping like `` `Trigger R` | `Button B` `` therefore needs its own key.

- `generate_or_aliases.py` adds keys for each group in its `OR_GROUPS`, covering every ordering, both with and without spaces around `|`. Each key points at the image of the first input listed. Dolphin's mapping UI writes alternatives sorted alphabetically with no spaces, while hand-written profiles usually include the spaces.
- To support another OR mapping, add a group there and re-run the script. Don't hand-edit the keys. (`` `Click 0` | RETURN `` is an older entry that was added by hand.)

`Dit_StartupPack.dit` is a project file for DolphinDynamicInputTextureCreator, the Windows authoring tool (its `.exe`/`.dll` are gitignored). `unused texture dumps/` is reference material only.

### 3. `<Game Name>/`: one package per game

- `GameID/<ID>.txt` is an empty marker file. Dolphin matches its name against the game ID. It is usually a 3-char region-agnostic prefix (e.g. `RMC.txt`) and occasionally a full ID or a system-menu ID.
- `tex1_<w>x<h>_<hash>[_<tlut>]_<fmt>.png` files are the game's dumped textures, which serve as base images. `unuse/` holds dumps that are not wired up. GC/Wii releases of the same game are separate folders with `_GC`/`_Wii` suffixes.
- `UniversalDIT_<Style>.json` is one file per style the game uses. Each is a **copy** of the matching `#Assets` template's `default_host_controls`, plus these game-specific fields:
  - `generated_folder_name`: usually `#Generated_<Game Name>`.
  - `preserve_aspect_ratio`.
  - `output_textures`, keyed by texture file name. Each entry has `image` and `emulated_controls`, a map shaped like `{"GCPad1"|"Wiimote1"|…: {"Buttons/A": [[x1, y1, x2, y2]], …}}` that gives the pixel regions to overwrite.
- `UniversalDIT_Devices.json` (in some games) has no `default_host_controls`. Instead, each texture carries its own `host_controls` that map device strings to `Device/Icon.png`. Its emulated control is `"Device"` and covers the whole texture, for "which controller" icons.

**Template changes must be propagated.** Game JSONs embed the template data instead of referencing it. Any edit to an `#Assets` template must be copied into the `default_host_controls` of every game JSON built from that template. In the history these show up as the maintainer's "Rebuild jsons from assets" commits. The repo has no script for this step, except for OR aliases: `generate_or_aliases.py` writes those to the templates and the game JSONs. Most game JSON names match the template name (`UniversalDIT_Flat.json` ← `#Assets/UniversalDIT_Flat.json`), but some games use custom names (`UniversalDIT_ShyGuy.json`, `UniversalDIT_Tak.json`, …).

## Gotchas

- **Path casing must be exact.** Dolphin on Linux/Android/SteamOS is case-sensitive, so a JSON path whose casing doesn't match the file breaks there. macOS and Windows filesystems are case-insensitive, so local existence checks won't catch these errors (see the "Fix DualSense casing" commit).
- `#DefaultDevices/DevicesTextureChanger.bat` is a Windows tool for end users. It swaps device image folders in place and renames the originals to `<Device>_backup`. `*_backup` folders are local user state and should never be committed.
- Directory names include spaces, `&`, `'` and a leading `#`, so always quote paths in shell commands.
