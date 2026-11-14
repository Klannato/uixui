"""Tooltip and hint text for the editor. HTML is allowed in tooltips."""

TIPS = {
    # project actions
    "new_project": "<b>New project</b><br>Create a project folder under ~/ui-specs.",
    "open_project": "<b>Open project</b><br>Open an existing project folder.",
    "export": "<b>Export spec</b><br>Write a timestamped bundle and point <code>current/</code> at it. "
              "Agents read <code>current/spec.md</code>.",
    "copy_prompt": "<b>Copy agent prompt</b><br>Copy a ready-made instruction that points a coding agent "
                   "at the latest spec.",
    # screens
    "paste": "<b>Paste screenshot</b> (Ctrl+V)<br>Add the image on your clipboard as a new screen.",
    "add_image": "<b>Add image</b><br>Add a screenshot file (PNG, JPG, WebP…) as a new screen.",
    "capture": "<b>Capture region</b><br>Pick a part of your screen. Your desktop shows the selector, "
               "and the capture becomes a new screen.",
    "screens_list": "<b>Screens</b><br>The screens in flow order. Drag a screen to reorder it.",
    "leads_to": "Where this screen goes next, e.g. <i>Dashboard after login</i>. Included in the spec.",
    # tools
    "tool_select": "<b>Select</b> (V)<br>Click an element to select it. Drag it to move it. "
                   "Press Delete to remove it.",
    "tool_rect": "<b>Rectangle</b> (R)<br>Draw a box around an element. It gets a numbered pin.",
    "tool_ellipse": "<b>Ellipse</b> (E)<br>Draw an oval around an element. It gets a numbered pin.",
    "tool_freehand": "<b>Freehand</b> (F)<br>Draw a loose outline around an irregular element.",
    "tool_arrow": "<b>Arrow</b> (A)<br>Drag from a numbered pin to another element, or to an empty "
                  "spot, to show a flow.",
    "tool_text": "<b>Text note</b> (T)<br>Click to add a note that applies to the whole screen.",
    "undo": "<b>Undo</b> (Ctrl+Z)<br>Undo your last change, including changes made by an agent.",
    "redo": "<b>Redo</b> (Ctrl+Shift+Z)<br>Redo the change you just undid.",
    "theme": "<b>Theme</b><br>Switch between dark and light.",
    # element panel
    "element_list": "<b>Elements</b><br>The numbered elements on this screen. Click one to select it "
                    "on the canvas.",
    "name": "<b>Name</b> (required)<br>A short label the agent will use, e.g. <i>Submit button</i>.",
    "purpose": "<b>Purpose</b> (required)<br>Why this element exists, e.g. <i>Logs the user in</i>.",
    "behavior": "What happens on click, hover, typing, or other interaction.",
    "states": "The visual states this element needs. Tick the ones that apply, or add your own below.",
    "state_default": "Normal resting appearance.",
    "state_hover": "The pointer is over the element.",
    "state_pressed": "The element is being pressed or clicked.",
    "state_focused": "The element has keyboard focus.",
    "state_disabled": "The element can't be used right now.",
    "state_error": "The element shows a problem, such as invalid input.",
    "state_empty": "There is no data yet.",
    "state_loading": "The element is waiting for data.",
    "custom_states": "Other states, separated by commas.",
    "content": "Exact text, labels, or copy the user sees.",
    "constraints": "Limits and must-do rules: sizes, accessibility, performance, things to avoid.",
    "notes": "Anything else the agent should know.",
    "reference": "A link or file path to a design or example to follow.",
    "save_element": "Save changes to this element.",
    "delete_element": "Remove this element. Later elements are renumbered.",
    # project panel
    "brief_purpose": "What the app is for, in one or two sentences.",
    "brief_audience": "Who uses it, e.g. <i>warehouse staff on tablets</i>.",
    "brief_tone": "The feel of the UI, e.g. <i>calm, plain, professional</i>.",
    "tokens_colors": "Named colors with values, e.g. <i>primary #0a6cff, surface #fff</i>.",
    "tokens_fonts": "Font families and sizes the design uses.",
    "tokens_spacing": "Spacing scale, e.g. <i>4, 8, 12, 16, 24</i>.",
    "tokens_radii": "Corner radii, e.g. <i>4 for inputs, 12 for cards</i>.",
    "save_brief": "Save the project brief and design tokens.",
}

HINTS = {
    "elements": "Draw a shape on the canvas to add an element. Select one to describe it.",
    "element_form": "Select an element to edit its description.",
    "no_screen": "Paste or add a screenshot to start a screen.",
    "project": "The brief and tokens apply to every screen. Agents read them first.",
    "canvas_empty": "Paste a screenshot (Ctrl+V), drop an image file here, or capture a region.",
}
