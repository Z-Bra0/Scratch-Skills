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

## Output Contract
- `scratch-yaml` is internal-only. Never paste it into the final user reply.
- If you show Scratch code or block structure to the user, you must run `scripts/render_ascii.py` and use its exact output.
- Raw `scratch-yaml` is allowed only for tool input and internal reasoning.
- If you mention Scratch code, show rendered blocks instead of describing the code only in prose whenever practical.
- Use rendered block output in fenced code blocks.
- Do not add a follow-up like "Want me to render an example?".
- Do not rewrite, add, split, or restyle the rendered Scratch blocks.
- Do not hand-draw, imitate, or approximate Scratch block ASCII from memory.

## Goal
Help with Scratch code questions by representing Scratch projects into
`scratch-yaml` when needed, reasoning over that internal representation, and
showing Scratch code to the user through `scripts/render_ascii.py` instead of
raw YAML. For conceptual questions, prefer a visual rendered example over prose-only explanation.

## Dependencies
```bash
python3 -m pip install pyyaml
```

## Repo Usage
- Read files under `references/` when you need skill guidance or file-handling instructions.
- Files under `data/` are runtime assets used by `scripts/`, not AI-facing reference docs.
- Do not read files under `data/` as reference material.

## Internal `scratch-yaml` Reference
`scratch-yaml` is an internal working format for the AI. Do not return it to the user.

`scratch-yaml` is a list of Scratch target objects. Each target can represent a `Sprite` or the `Stage`.

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

### Format
This format is for internal reasoning and tool input, not for user-facing replies.

Internal shape example:

`name`, `variables`, `lists`, `blocks`

### Display
- Must use `scripts/render_ascii.py` before showing Scratch code to the user
- Treat `scratch-yaml` as intermediate data only
- If the output is for the user, render first and reply with the rendered blocks, not YAML
- Wrap rendered block output in fenced code blocks so it is visually separated from the explanation

```bash
# Preferred: write scratch-yaml to a temp file, then render that file.
# This avoids shell quoting issues and very long CLI arguments.
tmp_yaml=/tmp/scratchcode/blocks.yaml
python3 <SKILL_DIR>/scripts/render_ascii.py "$tmp_yaml"

# For scratch-yaml file path, optionally narrowed to target names:
python3 <SKILL_DIR>/scripts/render_ascii.py "<SCRATCH_YAML_PATH>" --targets Sprite1 Stage
```

## Workflow

### Step 1. Decide whether file extraction is needed
- If the user is asking a general Scratch code question, go to step 2 and prefer a rendered example plus brief explanation.
- If the user provides a `.sb3` or `.sprite3` file, follow the process in
  `references/UPLOADS.md`.

### Step 2. Reason Internally
- Use `scratch-yaml` only as an internal representation for analysis.
- For simple conceptual questions, create a minimal internal example when needed so you can render it.
- When you create scratch-yaml yourself, write it to a temp file and pass the file path to `scripts/render_ascii.py`.

### Step 3. Reply to the User
- Never return `scratch-yaml` data to the user.
- For "how to" or "what does this do" questions, prefer rendered Scratch blocks first.
- If you want to show Scratch code, always run `scripts/render_ascii.py` first.
- Put rendered Scratch output inside a fenced code block.
- If you did not run `render_ascii.py`, do not output boxed ASCII at all; answer in prose or run the renderer first.
- After rendering, explain the answer in short prose around the rendered block output when useful.
- Before sending the final answer, check: "Am I about to paste `scratch-yaml`?" If yes, stop and render it first.
