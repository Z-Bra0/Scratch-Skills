# Uploaded Scratch Files

Use this reference only when the user provides or uploads a Scratch project
file and you need to inspect it.

## Supported files
- `.sb3`
- `.sprite3`

## Handling
- Use the uploaded file path directly when one is available in the workspace or
  thread context.
- If you need to inspect the project structure, run:

```bash
python3 <SKILL_DIR>/scripts/extract.py "<FILE>"
```

- For `.sb3` or `.sprite3` inputs, this writes split target YAML files plus
  `index.yaml` under `/tmp/scratchcode/<file md5>/blocks/`.
- Wait for extraction to finish, then use the printed file path as the source
  of truth.
- After extraction, do not go back to the original `.sb3` or `.sprite3` file
  unless you need to rerun the extractor.
- Combine the extracted content with the user's question, if there is one.
- Reason about the project in `scratch-yaml`, following the format in
  `SKILL.md`.
- Use `scripts/render_ascii.py` only if you want to show the Scratch code back
  to the user in a more visual block layout.
