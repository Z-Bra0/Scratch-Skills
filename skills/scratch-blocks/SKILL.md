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
- If you show Scratch code or block structure to the user, you must run `scripts/render_ascii.py` first.
- Raw `scratch-yaml` is allowed only for tool input and internal reasoning.
- Scratch users prefer visual explanations. Use rendered block output in fenced code blocks by default when explaining how something works.
- Do not add a follow-up like "Want me to render an example?" unless the user explicitly asks for options.
- If you mention Scratch code, show rendered blocks instead of describing the code only in prose whenever practical.
- Bad: replying with a fenced `scratch-yaml` block.
- Good: run `render_ascii.py`, put the rendered result in a fenced code block, then add a short explanation if needed.

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
- Do not read files under `data/` as reference material by default.
- Files under `data/` are runtime assets used by `scripts/`, not AI-facing reference docs.

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
# For Raw `scratch-yaml` string:
python3 <SKILL_DIR>/scripts/render_ascii.py --yaml '<SCRATCH_YAML>'

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
- If you need to inspect blocks, variables, or lists from a file, extract them into `scratch-yaml` first.
- Do not stop at `scratch-yaml` if the user expects to see the Scratch code itself.

### Step 3. Reply to the User
- Never return `scratch-yaml` data to the user.
- For "how to" or "what does this do" questions, prefer rendered Scratch blocks first.
- If you want to show Scratch code, always run `scripts/render_ascii.py` first.
- Put rendered Scratch output inside a fenced code block.
- Do not rewrite, add, split, or restyle the rendered Scratch blocks.
- After rendering, explain the answer in short prose around the rendered block output when useful.
- Before sending the final answer, check: "Am I about to paste `scratch-yaml`?" If yes, stop and render it first.
- Do not end with an offer like "Want me to render an example?" If an example is clearly useful, include it directly.

## Preferred Response Pattern
1. For conceptual questions, prepare a minimal internal example if needed.
2. Extract or inspect Scratch internally in `scratch-yaml` only when needed.
3. Run `scripts/render_ascii.py`.
4. Reply with the rendered blocks in a fenced code block.
5. Add a short explanation after the code block.
6. Do not include raw `scratch-yaml` in the final answer.

## Examples
- User asks: "How do I do loops in Scratch?"
  Show a rendered example of `repeat`, `forever`, or `repeat until` in a fenced code block, then explain briefly.
- User asks: "Show me what a repeat loop looks like."
  Create a minimal internal example if needed, render it with `scripts/render_ascii.py`, then show the rendered blocks.
- User uploads a project and asks: "What does this code do?"
  Extract internally, analyze in `scratch-yaml`, render the relevant blocks, and answer briefly in prose.
- User asks: "How do loops work?"
  Do not end with "Want me to render an example?" Include one rendered example directly.

## Enforcement
- When the user asks what the Scratch code does, render it first if showing code helps.
- When the user uploads `.sb3`, `.sprite3`, or Scratch JSON, do not return extracted YAML directly.
- When the user asks for a code walkthrough, prefer rendered ASCII blocks in fenced code blocks plus brief explanation.
- Only expose raw YAML if the user explicitly asks for the YAML format itself.
