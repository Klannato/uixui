# Contributing

Thanks for taking an interest in uispec. Bug reports, ideas, and pull requests are welcome.

## Before you start

- For anything bigger than a small fix, open an issue first so we can agree on the approach.
- Keep changes focused. One concern per pull request makes review faster.

## Development setup

```bash
python3 -m venv venv
./venv/bin/pip install -e '.[test]'
./venv/bin/pytest
```

The tests run headless (`QT_QPA_PLATFORM=offscreen`) and use temporary state directories, so they
never touch your real projects.

## Guidelines

- Every change to project data goes through `Controller.mutate` or a command in `commands.py`.
  That keeps undo, autosave, the CLI, and the API in step.
- New fields need a tooltip in `gui/help.py`, and a line in the export in `exporter.py` if the agent
  should see them.
- Keep the agent-facing behavior in `skill/ui-spec/SKILL.md` in sync with the CLI.
- Add a test for behavior you change. Command-level tests are usually the most useful.

## Pull requests

- Describe what changed and why.
- Include a screenshot for UI changes.
- Make sure `pytest` passes.
