# Scratch Skills

A skill that helps AI read and speak Scratch in a text-friendly format.

## What This Skill Does

```
┌───────────────────┐
│ when Flag clicked │
├────────────┬──────┘
│ repeat (5) │
│ ┌──────────┴─────────┐
│ │ say (Hello World!) │
│ └──────────┬─────────┘
│          ↺ │
└────────────┘
```

Ask any question about a Scratch project.

If you need help debugging, download your project or export a single sprite, then upload it to your AI.

### Usecase 1: Ask Scratch Question

Ask questions about Scratch blocks.

![Ask Scratch Question](docs/claude_ask.png)

### Usecase 2: Upload Scratch File

Upload a Scratch file (`.sb3` or `.sprite3`), and the AI can help you understand and debug it.

![Upload Scratch File](docs/claude_upload.png)

## Install

### Method 1: Download the zip and upload it to Claude

Download the latest `scratch-blocks` release zip, then upload it to Claude as a skill.

Instructions:
[Use Skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude#h_a4222fa77b)

### Method 2: Install from command line

```bash
npx skills add https://github.com/Z-Bra0/Scratch-Skills --skill scratch-blocks
```

## Tool Permission Note

Your AI may ask for permission to run these scripts:

- `skills/scratch-blocks/scripts/extract.py` to extract data from `.sb3`, `.sprite3`, `project.json`, or `sprite.json`
- `skills/scratch-blocks/scripts/render_ascii.py` to render extracted blocks as ASCII


## Development

Repo setup and repository details live in [docs/development.md](docs/development.md).
