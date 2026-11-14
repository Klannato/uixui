---
name: ui-spec
description: Use whenever you build, change, or review a user interface. Reads the annotated UI spec the user made with the uispec app (screenshots with numbered elements, per-element descriptions, a layout grid, and textures) and implements it. Also offers to open the annotator when no spec exists yet.
---

# ui-spec

The user annotates screenshots in the `uispec` app and exports a spec. The spec is the source of truth for the UI.

## Step 1: find the spec

1. Work out the project name: the git repo root name, or the current directory name if there is no repo.
2. Check for `~/ui-specs/<project>/current/spec.md`.
3. If it exists, read it. Then read every `screens/*/annotated.png` and `screens/*/elements.json` it lists. The annotated PNG shows the numbered outlines, pins, arrows, and textures; the JSON has the same content in machine-readable form.
4. If it does not exist, say so and offer to open the annotator:
   - `uispec app open --project ~/ui-specs/<project>` (or `uispec project new` for a new one)
   - Then ask the user to annotate and export, and wait for them to confirm.
   - Do not start building the UI before a spec exists unless the user says to skip it.

## Step 2: read the spec carefully

- **Project brief** and **design tokens** apply to every screen. Use the tokens exactly (colors, fonts, spacing, radii).
- **Layout grid** (`## Layout grid` in `spec.md`) is the spacing system. Place and size elements on multiples of the grid size, e.g. 8px. If snapping is on, the user drew elements on the grid on purpose.
- **Screen flow** gives the order and the transitions (`leads to`).
- **Each numbered element** has fields: name, purpose, behavior, states, content, constraints, notes, reference, and texture. Implement each one against its fields. Treat `states` as the states that must exist, not optional extras.
- **Textures** describe what the element's surface looks like:
  - `image` textures are picture fills. The file is in the screen folder under `textures/`. `tile` repeats it at the given scale, `stretch` fills the element once. Use the image as the background of that element, and apply the stated opacity and tint.
  - `pattern` textures are generated surfaces (noise, grain, stripes, dots, hatch) in a color. Recreate the look with CSS, SVG, or canvas. Keep them subtle when the opacity is low.
  - A texture is a background fill. Text and controls on top of it must stay readable.
- **Arrows** describe relationships between elements. Respect them when wiring navigation or data flow.
- **Screen notes** are free-form context for that screen.
- Missing fields are marked `⚠`. Ask the user about those before guessing.

## Step 3: implement

- Build each numbered element as described. Keep the element's number in code comments or test names when it helps trace back to the spec.
- Use the grid size for spacing between elements. Line up elements the way the annotations show; elements the user aligned in the app share an edge or a center.
- Do not add elements, states, copy, or textures that are not in the spec without asking.

## Step 4: verify against the annotations

1. Render or run the UI.
2. Compare the result with `annotated.png` for each screen, element by element. Check positions, grid alignment, and textures.
3. Report mismatches to the user. Do not silently diverge from the spec. If the spec seems wrong, say which element and why.

## Working with the annotator

All changes go through the `uispec` command. It talks to the running app and starts it if needed. Use `--json` for machine-readable output. Edits appear live in the app, so the user can follow along.

**Project and screens**
- `uispec project info` / `uispec project brief --set purpose="..."` / `uispec project tokens --set colors="..."`
- `uispec project grid --size 8 --snap on|off` sets the layout grid. Snapping applies to drawing, moving, and resizing in the app.
- `uispec screen list` / `uispec screen add FILE --name N` / `uispec screen capture` (the user picks the region)
- `uispec screen select NAME` / `uispec screen set NAME --leads-to "..."` / `uispec screen reorder NAME --index N` / `uispec screen remove NAME`

**Elements** (numbers are the pins; later elements renumber after a delete)
- `uispec element list [--screen S]`
- `uispec element add --kind rect|ellipse --box x,y,w,h` (image pixels, top-left origin)
- `uispec element edit N --set name="..." --set purpose="..." --set states="default,hover,disabled"`. Fields: name, purpose, behavior, states, content, constraints, notes, reference
- `uispec element resize N --box x,y,w,h` (minimum 4px per side)
- `uispec element align --numbers 1,2,3 --mode left|hcenter|right|top|vcenter|bottom|dist_h|dist_v` lines up or spaces several elements. Align needs two elements; distribute needs three
- `uispec element texture N --file IMG [--mode tile|stretch] [--scale 2] [--opacity 0.6] [--tint "#3366ff"]`
- `uispec element texture N --pattern noise|grain|stripes|dots|hatch [--color "#ccc"] [--scale 1] [--opacity 0.4]`
- `uispec element texture N --scale 2` (or any other setting) changes an existing texture without re-picking it
- `uispec element texture N --clear` removes the texture
- `uispec element delete N`

**Arrows, notes, and rendering**
- `uispec arrow add --from N --to M --label "..."` (or `--to-point x,y`)
- `uispec label add "note" --x 10 --y 10`
- `uispec render --screen S --out /path.png` renders the annotated view so you can check your work

**Export and history**
- `uispec export` writes a new timestamped bundle and updates `current/`
- `uispec undo` / `uispec redo`

Do not edit `project.json` directly while the app is open. Use the commands above.
