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

- The extractor prints the output filenames on stdout.
- Read the content from those files and use that content as the Scratch code
  context for analysis.
- Combine the extracted file content with the user's question, if there is one.
- Reason about the project in `scratch-yaml`, following the format in
  `SKILL.md`.
- Use `scripts/render_ascii.py` only if you want to show the Scratch code back
  to the user in a more visual block layout.
