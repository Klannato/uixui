# uispec

Annotate UI screenshots and hand the spec to a coding agent.

- Paste, drop, or capture a screenshot, then draw numbered elements over it.
- Describe each element in a side panel (purpose, behavior, states, copy, constraints, notes, reference).
- Export a bundle to `~/ui-specs/<project>/current/` containing `spec.md`, annotated PNGs, and per-element JSON.
- Agents drive the running app through the `uispec` CLI, and the `ui-spec` skill tells them how to use the spec.

## Setup

    python3 -m venv venv && ./venv/bin/pip install -e '.[test]'
    ln -sfn "$PWD/venv/bin/uispec" ~/.local/bin/uispec
    uispec skill install

## Usage

    uispec project new --name myapp      # creates ~/ui-specs/myapp and opens it
    uispec screen add login.png --name Login
    uispec element add --box 40,40,200,60
    uispec element edit 1 --set name=Submit --set purpose="Logs the user in" --set states="default,hover"
    uispec export

Run `uispec --help` for the full command list. Add `--json` for machine-readable output.

## Tests

    ./venv/bin/pytest
