---
name: pdf-protect
version: "0.1.0"
description: >
  Protects any PDF file for client delivery by adding a visible watermark and
  optional permission restrictions. Use this skill whenever a user wants to
  protect a PDF, add a watermark, lock down a PDF before sending to a client,
  prepare a PDF for client delivery, or watermark a PDF. Trigger when the user
  says: "protect this PDF", "add a watermark", "lock down before sending",
  "prepare for client delivery", "watermark a PDF", or similar. Do NOT use for
  creating PDFs — use moodboard-pdf for that.
---

# PDF Protect Skill

**You protect any PDF file for client delivery.** The output is saved alongside the original as `<name>-protected.pdf`.

### Workflow

1. Ask for the PDF path (or scan the current directory for `.pdf` files if none provided — list them and ask which to protect)
2. Ask: "Recipient name? (press Enter to skip)"
3. If a name was given, ask: "Recipient email? (press Enter to skip)"
4. Ask: "Which restrictions to apply? Enter any combination of: editing, copying, printing — or press Enter for none"
5. Assemble the command and run `protect_pdf.py`
6. Report the output path

### Running the script

```bash
python "$CLAUDE_PLUGIN_ROOT/skills/pdf-protect/scripts/protect_pdf.py" \
  --input <path> \
  [--output <path>] \
  [--watermark-text "CONFIDENTIAL — Steven Castroverde — <date>"] \
  [--recipient-name "Jane Doe"] \
  [--recipient-email "jane@example.com"] \
  [--restrict editing copying printing]
```
