---
name: ui-spec
description: Use whenever you build, change, or review a user interface. Reads the annotated UI spec the user made with the uispec app (screenshots with numbered elements and per-element descriptions) and implements it. Also offers to open the annotator when no spec exists yet.
---

# ui-spec

The user annotates screenshots in the `uispec` app and exports a spec. The spec is the source of truth for the UI.

## Step 1: find the spec

1. Work out the project name: the git repo root name, or the current directory name if there is no repo.
2. Check for `~/ui-specs/<project>/current/spec.md`.
3. If it exists, read it. Then read every `screens/*/annotated.png` and `screens/*/elements.json` it lists. The annotated PNG shows the numbered outlines; the JSON has the same content in machine-readable form.
4. If it does not exist, say so and offer to open the annotator:
   - `uispec app open --project ~/ui-specs/<project>` (or `uispec project new` for a new one)
   - Then ask the user to annotate and export, and wait for them to confirm.
   - Do not start building the UI before a spec exists unless the user says to skip it.

## Step 2: read the spec carefully

- **Project brief** and **design tokens** apply to every screen. Use the tokens exactly (colors, fonts, spacing, radii).
- **Screen flow** gives the order and the transitions (`leads to`).
- **Each numbered element** has fields: name, purpose, behavior, states, content, constraints, notes, reference. Implement each one against its fields. Treat `states` as the states that must exist, not optional extras.
- **Arrows** describe relationships between elements. Respect them when wiring navigation or data flow.
- **Screen notes** are free-form context for that screen.
- Missing fields are marked `⚠`. Ask the user about those before guessing.

## Step 3: implement

- Build each numbered element as described. Keep the element's number in code comments or test names when it helps trace back to the spec.
- Do not add elements, states, or copy that are not in the spec without asking.

## Step 4: verify against the annotations

1. Render or run the UI.
2. Compare the result with `annotated.png` for each screen, element by element.
3. Report mismatches to the user. Do not silently diverge from the spec. If the spec seems wrong, say which element and why.

## Working with the annotator

All changes go through the `uispec` command (it talks to the running app and starts it if needed). Use `--json` for machine-readable output.

- `uispec project info` / `uispec screen list` / `uispec element list [--screen S]`
- `uispec element edit N --set purpose="..." --set states="default,hover,disabled"`
- `uispec element add --kind rect --box x,y,w,h` (image pixels, top-left origin)
- `uispec element resize N --box x,y,w,h` (image pixels; minimum 4px per side)
- `uispec element delete N` (later elements renumber automatically)
- `uispec arrow add --from N --to M --label "..."`
- `uispec label add "note" --x 10 --y 10`
- `uispec screen capture` opens the desktop region picker for the user to choose the region
- `uispec render --screen S --out /path.png` renders the annotated view so you can check your work
- `uispec export` writes a new timestamped bundle and updates `current/`
- `uispec undo` / `uispec redo`

Prefer editing through the CLI so the user sees the change live in the app. Do not edit `project.json` directly while the app is open.
