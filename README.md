# UI X UI

**Annotate UI screenshots and hand the spec to your coding agent.**

UI X UI is a desktop editor for describing how a user interface should look and behave. Draw numbered
elements over a screenshot of any app, describe each one in depth, and export a spec bundle that
an agent can read and implement. (The command-line tool and Python package are named `uispec`.)

![UI X UI in dark mode](docs/screenshot-dark.png)

## Features

- **Screenshots in any way you like:** paste from the clipboard, drop image files, add files, or capture a region of your screen (Wayland-safe, via the desktop portal).
- **Numbered elements:** draw rectangles, ellipses, or freehand outlines. Each one gets a pin that the description refers to.
- **Delete screens:** remove a screen and its elements from the panel button, the list's right-click menu, or the Delete key. Undo with Ctrl+Z.
- **Auto-save:** element descriptions and the project brief save as soon as you click away, switch screens, or export. The Save buttons remain if you prefer to save immediately.
- **Layout grid:** a per-project grid (default 8px) that drawing, moving, and resizing snap to. Toggle the overlay with G and snapping with S. The grid is written to the spec so agents space elements the same way.
- **Align and distribute:** Shift-click or drag a box to select several elements, then align edges or centers, or space three or more evenly.
- **Textures:** fill an element with an image (tiled or stretched, with opacity and tint) or a built-in seamless pattern (noise, grain, stripes, dots, hatch). Textures are clipped to the shape and appear in the annotated PNG. Export a finished texture with `uispec element texture N --export out.png`, so an agent can bake it into the element as a placeholder.
- **Resize and move:** drag the handles on a selected element to resize it, drag its pin to resize from the top-left, or drag the body to move it. Agents can resize with `uispec element resize`.
- **Structured descriptions:** name, purpose, behavior, states (checklist plus custom), content, constraints, notes, and a reference link.
- **Flows:** order screens by drag and drop, add a "leads to" note, and draw arrows between elements.
- **Project brief and design tokens:** purpose, audience, tone, colors, fonts, spacing, and radii apply to every screen.
- **Spec bundles:** each export writes `spec.md`, annotated and original PNGs, and per-element JSON to a timestamped folder. `current/` always points at the latest.
- **Agent control:** a `uispec` command drives the running app over a token-guarded localhost API, so an agent can add, edit, align, texture, and export elements while you watch.
- **Undo and redo** for every change, including the ones made by agents.
- **Material Design UI:** dark and light themes, icon toolbars, and a tooltip on every control.
- **Application launcher:** `uispec app install` adds "UI X UI" to your desktop's app launcher with an icon, so you can start it like any other app. `uispec app uninstall` removes it.

## Install

Requires Python 3.10+ and a desktop session (Linux tested; Qt should run on macOS and Windows, but only Linux is verified).

```bash
git clone https://github.com/Klannato/uixui.git
cd uixui
python3 -m venv venv
./venv/bin/pip install -e '.[test]'
ln -sfn "$PWD/venv/bin/uispec" ~/.local/bin/uispec
uispec skill install          # installs the ui-spec agent skill
uispec app install            # adds "UI X UI" to your application launcher
```

## Quick start

```bash
uispec project new --name myapp            # creates ~/ui-specs/myapp and opens the app
uispec screen add login.png --name Login
uispec element add --box 40,40,200,60      # x,y,w,h in image pixels
uispec element edit 1 --set name=Submit --set purpose="Logs the user in" --set states="default,hover,disabled"
uispec arrow add --from 1 --to 2 --label "on success"
uispec export                              # writes ~/ui-specs/myapp/current/spec.md
```

Run `uispec --help` for every command. Add `--json` for machine-readable output.

## How agents use it

The bundled `ui-spec` skill tells a coding agent to read `current/spec.md` and the annotated images
before building a UI, implement each numbered element against its fields, render the result, and
report any mismatch rather than silently diverging. Copy the prompt from the app's toolbar to hand
off a task.

## Project layout

```
src/uispec/
  model.py       data model: projects, screens, elements, arrows, labels
  controller.py  owns the open project; undo/redo; autosave
  commands.py    command handlers shared by the GUI, CLI, and API
  api.py         localhost JSON API with a per-run token
  cli.py         the `uispec` command
  exporter.py    spec.md, annotated PNGs, element JSON
  render.py      drawing for the canvas and exports
  capture.py     screenshot portal for region capture
  desktop.py     application-launcher entry and icon
  gui/           Qt (PySide6) window, canvas, panels, Material theme
  skill/         the ui-spec agent skill
tests/           unit and command-level tests
```

## Development

```bash
./venv/bin/pip install -e '.[test]'
./venv/bin/pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
