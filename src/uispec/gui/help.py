"""Tooltip and hint text for the editor. HTML is allowed in tooltips."""

TIPS = {
    # project actions
    "new_project": "<b>New project</b><br>Create a project folder under ~/ui-specs.",
    "open_project": "<b>Open project</b><br>Open an existing project folder.",
    "recent": "<b>Recent projects</b><br>Open a project you used lately. The list is kept per user.",
    "export": "<b>Export spec</b><br>Write a timestamped bundle and point <code>current/</code> at it. "
              "Agents read <code>current/spec.md</code>.",
    "copy_prompt": "<b>Copy agent prompt</b><br>Copy a ready-made instruction that points a coding agent "
                   "at the latest spec.",
    # screens
    "paste": "<b>Paste screenshot</b> (Ctrl+V)<br>Add the image on your clipboard as a new screen.",
    "add_image": "<b>Add image</b><br>Add a screenshot file (PNG, JPG, WebP…) as a new screen.",
    "capture": "<b>Capture region</b><br>Pick a part of your screen. Your desktop shows the selector, "
               "and the capture becomes a new screen.",
    "blank_canvas": "<b>Blank canvas</b><br>Add an empty screen to design from scratch — pick a name "
                    "and size, then draw textured elements on it. No screenshot needed. The page starts "
                    "as a dark neutral surface so light elements stay visible; change it with "
                    "<code>uispec screen add --blank --color #rrggbb</code>.",
    "screens_list": "<b>Screens</b><br>The screens in flow order. Drag a screen to reorder it.",
    "delete_screen": "<b>Delete screen</b><br>Remove the selected screen and its elements. "
                     "Press Delete while the list has focus. You can undo with Ctrl+Z.",
    "autosave": "Edits save as soon as you click away, so nothing is lost. The Save button is there "
                "if you prefer to save right away.",
    "leads_to": "Where this screen goes next, e.g. <i>Dashboard after login</i>. Included in the spec.",
    # tools
    "tool_select": "<b>Select</b> (V)<br>Click an element to select it and drag it to move it. "
                   "Drag a white handle to resize it, or drag its numbered pin to resize from the "
                   "top-left. Press Delete to remove it.",
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
    "grid_size": "Spacing of the layout grid in image pixels. Saved with the project and written to the spec.",
    "grid_snap": "When on, drawing, moving, and resizing snap to the grid. Hold nothing; the arrow keys "
                 "nudge by one grid step.",
    "save_grid": "Save the grid size and snapping setting.",
    "grid_toggle": "<b>Show grid</b> (G)<br>Overlay the layout grid on the screenshot. Overlay only; "
                   "it is not exported.",
    "snap_toggle": "<b>Snap to grid</b> (S)<br>Snap drawing, moving, and resizing to the grid. Saved with "
                   "the project.",
    "align_left": "Align left edges to the leftmost selected element.",
    "align_hcenter": "Align horizontal centers to the middle of the selection.",
    "align_right": "Align right edges to the rightmost selected element.",
    "align_dist_h": "Space three or more elements evenly from left to right.",
    "align_top": "Align top edges to the highest selected element.",
    "align_vcenter": "Align vertical centers to the middle of the selection.",
    "align_bottom": "Align bottom edges to the lowest selected element.",
    "align_dist_v": "Space three or more elements evenly from top to bottom.",
    "texture_source": "None removes the texture. Image fills the element with a picture. Pattern uses a "
                      "built-in seamless pattern.",
    "texture_pick": "Choose a PNG or JPEG. It is copied into the project's textures folder.",
    "texture_pattern": "noise, grain, stripes, dots, or hatch.",
    "texture_color": "Pattern color, as #rrggbb.",
    "texture_mode": "tile repeats the image at its scale. stretch fills the element once.",
    "texture_scale": "Size of each repeat (tile) or of the pattern cells. 1 is the original size.",
    "texture_opacity": "How strongly the texture shows. Lower values keep outlines and text readable.",
    "texture_tint": "Optional color that washes over the image or pattern, e.g. #3366ff.",
    "texture_apply": "Apply these texture settings to the selected element.",
    "texture_clear": "Remove the texture from the selected element.",
}

HINTS = {
    "elements": "Draw a shape on the canvas to add an element. Select one to describe it.",
    "element_form": "Select an element to edit its description.",
    "no_screen": "Add a screenshot to design over it, or a blank canvas to design from scratch.",
    "project": "The brief and tokens apply to every screen. Agents read them first.",
    "canvas_empty": "Add a screenshot (Ctrl+V, a file, or a region capture) to change an existing UI, "
                    "or add a blank canvas to draw a new one.",
    "multi_select": "Shift-click or drag a box to select several. Use the buttons below to line them up.",
    "texture": "Fills the selected element. Agents can set the same thing with uispec element texture.",
    "grid": "The layout grid is part of the spec. Agents use it to space elements consistently.",
}
