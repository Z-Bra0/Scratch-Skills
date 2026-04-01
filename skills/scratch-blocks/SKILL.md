---
name: scratch-blocks
description: >
  Use this skill when the user asks about Scratch code or Scratch blocks, or
  provides a `.sb3` or `.sprite3` file.
metadata:
  author: Z-Bra
  version: "0.0.1"
---

# Scratch Code Assistant

## Goal
Help with Scratch code questions by representing Scratch projects into
`scratch-yaml` when needed, reasoning over that representation, and only using
visual block rendering when it helps the user.

## Dependencies
```bash
python3 -m pip install pyyaml
```

## `scratch-yaml` Format
`scratch-yaml` is a list of Scratch target objects.

Each target can represent a sprite or the Stage. A single file contains all
targets.

Each target object includes:

| Field       | Type            | Description |
|-------------|-----------------|-------------|
| `name`      | string          | Target name |
| `variables` | mapping         | Variable name to current value |
| `lists`     | list            | List definitions |
| `blocks`    | list of scripts | Top-level scripts |

### `lists` Structure
Each list item has this shape:

| Field   | Type   | Description |
|---------|--------|-------------|
| `name`  | string | List name |
| `items` | list   | Current list items |

### Block Structure
Every block must include `opcode`. `params` and `blocks` are optional.

| Field    | Type            | Description |
|----------|-----------------|-------------|
| `opcode` | string          | Block type, Scratch block opcode |
| `params` | list            | Optional positional input values |
| `blocks` | list of scripts | Optional sub-script branches |

### `params` Item Types
| Type | Example |
|------|---------|
| number / string | `10`, `"Hello!"`, `"space"` |
| reporter block | `{ opcode: motion_xposition }` |
| variable / list / broadcast | `{ type: variable, name: score }` |

### `blocks` Branches
- Most blocks omit `blocks`.
- `control_repeat` and `control_if` use one branch for the body.
- `control_if_else` uses two branches: index `0` for `then`, index `1` for `else`.

### Output Format
When returning `scratch-yaml`, always wrap it in a fenced code block tagged
`scratch-yaml`:

````markdown
```scratch-yaml
name: Sprite1
variables: {}
lists: []
blocks:
  - - opcode: ...
```
````

See `references/SCRATCH_YAML_EXAMPLE.md` for an example.
See `references/BLOCK_CATALOG_SPEC.md` for the block catalog reference format.

## Workflow

### 1. Decide whether file extraction is needed
- If the user is asking a general Scratch code question, go to step 2.
- If the user provides a `.sb3` or `.sprite3` file, follow the process in
  `references/UPLOADS.md`.

### 2. Use `scratch-yaml` format
- Prefer `scratch-yaml` over raw Scratch JSON when explaining behavior,
  debugging logic, or answering questions about project structure.

### 3. Reply to the User
- Do not send the user `scratch-yaml` code blocks.
- Only call `scripts/render_ascii.py` when you will include the rendered output
  in your reply. Use either of these input styles:


```bash
# For Raw `scratch-yaml` string:
python3 <SKILL_DIR>/scripts/render_ascii.py --yaml '<SCRATCH_YAML>'

# For scratch-yaml file path, optionally narrowed to target names:
python3 <SKILL_DIR>/scripts/render_ascii.py "<SCRATCH_YAML_PATH>" --targets Sprite1 Stage
```

- Do not rewrite, add, split, or restyle the rendered Scratch blocks.
