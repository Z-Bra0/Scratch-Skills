# Development

## Repo Layout

- `skills/scratch-blocks/`: the Scratch skill, references, and scripts
- `example/`: checked-in fixtures and expected extracted output
- `tests/`: pytest coverage for extractor and ASCII rendering behavior
- `tools/`: one-off helper scripts and reference data

## Main Scripts

### `skills/scratch-blocks/scripts/extract.py`

Converts `.sb3`, `.sprite3`, or raw Scratch `project.json` / `sprite.json` into the repository's extracted `scratch-json` format and prints the output JSON path.

The extractor writes one combined `.blocks.json` file by default, or uses the exact path passed to `--output`.

### `skills/scratch-blocks/scripts/render_ascii.py`

Renders extracted `scratch-json` into a boxed ASCII view for user-facing display.

This script does not accept raw Scratch `project.json` / `sprite.json`; run `extract.py` first.

## Python Setup

This repo is set up for `uv`.

Install dependencies:

```bash
uv sync --dev
```

Run tests:

```bash
uv run pytest -q
```

## Local Examples

Extract the checked-in example fixture:

```bash
python3 skills/scratch-blocks/scripts/extract.py example/project.json
```

This writes `example/project.blocks.json`.

Render the extracted project view:

```bash
python3 skills/scratch-blocks/scripts/render_ascii.py example/project.blocks.json
```

Render the example sprite view:

```bash
python3 skills/scratch-blocks/scripts/render_ascii.py example/sprite.json
```

## Release Archive

Build a zip archive for the `scratch-blocks` skill by passing a version number:

```bash
tools/release_skill.sh v0.0.2
```

This writes `dist/scratch-blocks-v0.0.2.zip`.

The script packages only `.md`, `.json`, and `.py` files from `skills/scratch-blocks/`.
