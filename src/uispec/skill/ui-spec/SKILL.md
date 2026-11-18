---
name: ui-spec
description: Use whenever you build, change, or review a user interface, or when the user pastes the "Implement or update the UI for …" prompt copied from the uispec app. Reads the annotated UI spec the user made with the uispec app (screenshots with numbered elements, per-element descriptions, a layout grid, and textures) and implements it in Material Design unless told otherwise, texture-mapping surfaces and baking each texture into its element as a placeholder. On first use in a project it walks the user through making a spec and handing the prompt back.
---

# ui-spec

The user annotates screenshots in the `uispec` app and exports a spec. The spec is the source of truth for the UI.

## Step 1: find the spec

1. Work out the project name: the git repo root name, or the current directory name if there is no repo.
2. Check for `~/ui-specs/<project>/current/spec.md`.
3. If it exists, read it. Then read every `screens/*/annotated.png` and `screens/*/elements.json` it lists. The annotated PNG shows the numbered outlines, pins, arrows, and textures; the JSON has the same content in machine-readable form.
4. If it does not exist, this is your **first time in this project**. Say so, then walk the user
   through making a spec and handing it back to you. Do this **once**, on this first contact only;
   once `current/spec.md` exists, never repeat the walkthrough — just read the spec and build.
   1. Offer to open the annotator on the project:
      - existing folder: `uispec app open --project ~/ui-specs/<project>`
      - brand new project: `uispec project new --name <project>`
   2. Ask the user to add their screens. In the app they can **Paste** a screenshot (Ctrl+V),
      **Add image** a file, or **Capture region** a part of a live app.
   3. Ask them to draw a **numbered element** over each part of the UI and describe it in the form:
      name, purpose, behavior, states, content, constraints, notes, reference. They can also pin a
      texture on an element; the agent texture-maps the rest by default (Step 3). They set the
      **project brief** and **design tokens** once for the whole app, and the **layout grid** sets
      spacing. The style is Material Design 3 unless they say otherwise.
   4. When the screens are described, ask them to press **Export**. That writes
      `~/ui-specs/<project>/current/spec.md` plus `screens/*/annotated.png`.
   5. Then ask them to press **Copy prompt** in the toolbar and paste it to you. That message reads
      roughly "Implement or update the UI for <project>. Read …/spec.md first and follow it exactly…"
      and names this skill. When you receive it, that is your cue to continue with Step 2.
   6. Wait for them to paste the prompt (or tell you the spec is ready). Do not build anything before
      the spec exists unless the user says to skip it.

   You may do the mechanical steps for them with the commands under "Working with the annotator"
   below (add screens, draw elements, set the brief), but the descriptions are the user's to
   confirm. Keep the walkthrough to the first time and then get out of the way.

## Step 2: read the spec carefully

- **Project brief** and **design tokens** apply to every screen. Use the tokens exactly (colors, fonts, spacing, radii).
- **Layout grid** (`## Layout grid` in `spec.md`) is the spacing system. Place and size elements on multiples of the grid size, e.g. 8px. If snapping is on, the user drew elements on the grid on purpose.
- **Screen flow** gives the order and the transitions (`leads to`).
- **Each numbered element** has fields: name, purpose, behavior, states, content, constraints, notes, reference, and texture. Implement each one against its fields. Treat `states` as the states that must exist, not optional extras.
- **Textures** describe what the element's surface looks like. A texture is a **background fill**: apply it as a real surface, never leave it as a flat color or a sentence in a description, and keep any text or controls on top readable. **Texture maps are the default surface treatment** — unless the spec or the user says otherwise, every surface should carry one (see Step 3).
  - `image` textures are picture fills. The file is in the screen folder under `textures/`. `tile` repeats it at the given scale, `stretch` fills the element once. Apply the stated opacity and tint.
  - `pattern` textures are generated surfaces (noise, grain, stripes, dots, hatch) in a color. Recreate the look as a real surface; do not leave it as a flat color.
- **Arrows** describe relationships between elements. Respect them when wiring navigation or data flow.
- **Screen notes** are free-form context for that screen.
- Missing fields are marked `⚠`. Ask the user about those before guessing.

## Step 3: implement

- **Prefer Material Design.** Unless the spec or the user names another style, build in **Material Design 3**: tonal surface colors from the spec's tokens, spacing on the spec's layout grid (usually 4dp/8dp), layered elevation and surface tints instead of heavy borders, and the token colors mapped onto Material roles. Say so if the spec's tokens clearly belong to another system.
- Build each numbered element as described. Keep the element's number in code comments or test names when it helps trace back to the spec.
- Use the grid size for spacing between elements. Line up elements the way the annotations show; elements the user aligned in the app share an edge or a center.
- Do not add elements, states, or copy that are not in the spec without asking. **Texture maps are the exception** — add them by default, as below.
- **Texture-map elements whenever possible.** Unless the spec or the user says otherwise, every surface should carry a real texture map, never a flat color:
  1. If the spec names a texture on the element (`image` or `pattern`), bake that one. Get its exact finished pixels from the annotator:
     `uispec element texture N --export /path/to/element-N-placeholder.png`
     That writes the image with its tint and opacity already applied, or the rendered pattern tile at its scale. Prefer it over re-deriving the pattern or tint by hand.
  2. If the spec names no texture, add a subtle, token-fitting pattern map yourself so the surface reads as a material:
     `uispec element texture N --pattern grain --color "<a surface tone from the tokens>" --scale 1 --opacity 0.15` — then export it with `--export` as above. Keep opacity roughly 0.15–0.35 so text and controls on top stay readable, and skip the map where a surface must stay perfectly flat (hairline dividers, plain text runs, icons).
  3. Tell the user which elements you texture-mapped on your own and why, so they can adjust the spec.
  4. Bake the exported file into the element as its real background: copy it into the app's own assets (for example `assets/`), so the running app never depends on `~/ui-specs`. If the project avoids asset files, generate the pattern in code (CSS gradients or an inline SVG) to match the exported pixels.
  5. Flag every texture as a placeholder: name the asset so it is obviously a stand-in (e.g. `element-3-placeholder.png`) and add a short comment like `TODO: replace placeholder texture with real art`. The user will swap in real artwork later.

## Step 4: verify against the annotations

1. Render or run the UI.
2. Confirm the style: Material Design 3 unless the spec names another style — spacing on the grid, tonal surfaces, elevation, and the design tokens applied.
3. Compare the result with `annotated.png` for each screen, element by element. Check positions, grid alignment, and textures.
4. Confirm the surfaces carry texture maps: every element with a spec texture is baked into the code and matches the annotation (same pattern or image, color, opacity, and tint), and each element you texture-mapped on your own reads as a deliberate material while staying readable. Report any element whose texture is missing, still a flat color, or baked with the wrong settings, with its element number.
5. Report mismatches and every placeholder texture to the user. Do not silently diverge from the spec. If the spec seems wrong, say which element and why.

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
- `uispec element texture N --export PATH` writes the element's finished texture to PATH (image with tint and opacity applied, or the rendered pattern tile) so it can be baked into the app as a placeholder
- `uispec element delete N`

**Arrows, notes, and rendering**
- `uispec arrow add --from N --to M --label "..."` (or `--to-point x,y`)
- `uispec label add "note" --x 10 --y 10`
- `uispec render --screen S --out /path.png` renders the annotated view so you can check your work

**Export and history**
- `uispec export` writes a new timestamped bundle and updates `current/`
- `uispec undo` / `uispec redo`

**Handoff.** After exporting, the app's **Copy prompt** button copies an instruction that points you at
`current/spec.md` and names this skill; the user pastes it to you to start a task. Seeing that prompt
means the spec is ready — read it and build.

Do not edit `project.json` directly while the app is open. Use the commands above.
