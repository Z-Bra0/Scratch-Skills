# Scratch Skills

This repo contains skills that help AI read and speak Scratch in plain text.

## Overview

This repo defines `scratch-yaml`, a compact format that converts large Scratch `project.json` files into a more AI-friendly representation.
The extractor writes split target YAML files plus an `index.yaml` by default, or one combined file when `--output` is used.
When showing Scratch code to users, it renders `scratch-yaml` as boxed plain text for a clearer chat experience.


## What is here
- `skills/scratch-blocks/`: the Scratch skill, references, and scripts
- `example/`: small checked-in fixtures and expected extracted output
- `tests/`: pytest coverage for the extractor
- `tools/`: one-off helper scripts and reference data

## Main scripts
- `skills/scratch-blocks/scripts/extract.py`
  Converts `.sb3`, `.sprite3`, or Scratch JSON into extracted
  `scratch-yaml` target files and prints the `index.yaml` path.
- `skills/scratch-blocks/scripts/render_ascii.py`
  Renders `scratch-yaml` into a boxed ASCII view for user-facing display.

## Python setup

This repo is set up for `uv`.

```bash
uv sync --dev
uv run pytest -q
```

## Example

Extract the checked-in example fixture:

```bash
python3 skills/scratch-blocks/scripts/extract.py example/project.json
```

This writes `example/project.blocks/index.yaml`.

Render the example sprite view:

```bash
python3 skills/scratch-blocks/scripts/render_ascii.py example/sprite.yaml
```
