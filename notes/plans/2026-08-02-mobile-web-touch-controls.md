# Mobile Web Touch Controls (Auto-Switch)

**Goal:** Make the web build usable on phones/tablets by showing an on-screen virtual joystick when the player has a touchscreen, and hiding it (falling back to WASD/arrow keys) on desktop. One build, runtime detection — no separate mobile URL.

**Non-goals:** Native iOS/Android exports, gyro/tilt steering, redesigning the game for portrait, multi-touch camera gestures, PWA install/offline. HUD layout on very small screens is best-effort only.

## Design decisions

### 1. Auto-switch: runtime detection, one build

Godot 4.7 gives us two viable web-side signals:

- **`DisplayServer.is_touchscreen_available()`** — runtime; true on any device with a touchscreen (iOS, Android, Windows tablets, some Chromebooks). This is the primary signal.
- **`OS.has_feature("web_android")` / `OS.has_feature("web_ios")`** — set by the exporter's JS shim based on user-agent. Useful as a secondary hint, but a Surface tablet or 2-in-1 in desktop-Chrome UA will read as `web_linuxbsd`/`web_windows` while still having touch.

**Rule:** Show touch controls iff `DisplayServer.is_touchscreen_available()` is true at scene ready. Do NOT hide keyboard input in that case — a Bluetooth keyboard on an iPad should still drive the truck. Both input paths stay live simultaneously; whichever the player uses wins for that frame.

Rejected alternative: two builds + UA sniffing at `docs/index.html`. More moving parts, worse for hybrid devices, and the desktop build would still need touch handling for anyone who lands on the wrong URL.

Also rejected: forcing a manual toggle button. Adds a UI decision to the first 5 seconds of play; auto-detect is right ~100% of the time.

### 2. Control shape: single left-thumb joystick

One analog stick on the left, mapped so:

- **Up (y < 0)** → `throttle_forward`
- **Down (y > 0)** → `throttle_reverse`
- **Left/right (x)** → `steer_left` / `steer_right`

Matches WASD's mental model 1:1, keeps the right thumb free for possible future actions (horn, camera), and is one thing to build. Rejected alternatives:

- Left-stick steer + right-side gas/brake pedals: two controls to build, and reverse becomes a third button. Not worth it for a game with no distinct brake.
- On-screen D-pad buttons: no analog steering feel; the truck currently uses `Input.get_axis()` which is already analog-friendly.

### 3. How the joystick feeds the existing controller

`truck_controller.gd` reads four named actions via `Input.get_axis()`. Two choices for wiring the joystick:

- **A.** Have the joystick call `Input.action_press("throttle_forward", strength)` etc. every frame. Zero changes to `truck_controller.gd`. `Input.get_axis` respects action strength, so partial-tilt already produces partial throttle.
- **B.** Publish the joystick vector on an autoload/singleton and read it directly in `truck_controller.gd`.

Go with **A**. Keeps the controller ignorant of input source, and desktop keyboard input keeps working with no branching. The one subtlety: `Input.action_press` with strength below the action's `deadzone` (0.5 in [project.godot](project.godot)) reads as 0 from `get_axis`. Lower each action's deadzone to `0.1` so partial tilt registers — keyboard still reports 1.0, so nothing regresses.

### 4. Where the joystick lives

A new `TouchControls` `Control` node added to [HUD.tscn](scenes/HUD.tscn), anchored bottom-left, with:

- A `Control` script (`scripts/virtual_joystick.gd`) that handles `_gui_input` (`InputEventScreenTouch` + `InputEventScreenDrag`).
- Two `TextureRect`s (base ring + knob) or `ColorRect`s drawn from code; art is a stretch goal, plain circles are fine for v1.
- Radius ~140 px, dead-zone ~15 px inside the ring, knob clamped to radius. Vector normalized by radius → magnitude 0..1 per axis.

`hud.gd._ready` calls `$TouchControls.visible = DisplayServer.is_touchscreen_available()` and swaps the WASD help overlay (`$HelpOverlay/CaptionLabel.text` and the `KeysContainer` visuals) for a "Drag the stick to drive" caption when touch is on. `KeysContainer` gets hidden in touch mode.

### 5. Web export / viewport tweaks

- `export_presets.cfg`: set `html/canvas_resize_policy=2` (already the value — "Adaptive"), and confirm `html/focus_canvas_on_start=true` (already true).
- Add a viewport meta and touch-action CSS to whatever HTML shell we ship. Godot's default shell already includes `viewport` with `user-scalable=no`, so no shell override is needed **unless** we see pinch-zoom or double-tap-zoom eating touches during testing. If we do, set `html/custom_html_shell=""` → a small custom shell that adds `touch-action: none` on the canvas.
- Project setting `input_devices/pointing/emulate_mouse_from_touch` should stay **off** for the game canvas so we get real `InputEventScreenTouch` events on the joystick. `emulate_touch_from_mouse` stays off too. (Current `project.godot` has neither set → both default false, which is what we want. No change needed, but the plan verifies.)

### 6. HUD scaling on small screens

Not solving fully in v1. Two cheap wins:

- The joystick anchors to bottom-left with a margin proportional to viewport height (`size.y * 0.05`), so it stays reachable in landscape phones.
- The `DamageLabel` font is already 32 px on a 2304×1296 viewport, which downscales fine.

Portrait phones will look bad — that's fine for v1, we tell the player to rotate via a one-time overlay if `size.x < size.y`.

## Tech stack

- Godot 4.7, GL Compatibility renderer (unchanged).
- GDScript only. No new dependencies, no JS interop.
- Web export via existing `Web` preset in [export_presets.cfg](export_presets.cfg).

## Global constraints

- Verify any API against https://docs.godotengine.org/en/4.7/ (esp. `DisplayServer.is_touchscreen_available`, `Input.action_press`, `InputEventScreenTouch/Drag`).
- Do NOT export into `docs/v1/` during dev — that's the published build. Export throwaway to `/tmp/mobile-test/` and open it via a local server for touch testing (Safari on iPhone → local IP, or Chrome DevTools device mode).
- Keep [truck_controller.gd](scripts/truck_controller.gd) untouched except possibly for a one-line comment. All input-source logic lives in HUD / joystick script.
- Don't break existing keyboard play — desktop must behave identically after the change.

---

## Implementation tasks

### Task 1: Lower action deadzones so partial joystick tilt registers

**Files:** [project.godot](project.godot)

Change all four input actions' `"deadzone": 0.5` to `"deadzone": 0.1`. Keyboard events still fire strength 1.0 so nothing regresses; joystick partial-tilt now feeds the controller.

**Verify:** Open the project in Godot, Project Settings → Input Map, confirm all four actions show deadzone 0.1.

---

### Task 2: Add virtual joystick script

**Files (new):** `scripts/virtual_joystick.gd`, `scripts/virtual_joystick.gd.uid`

A `Control` script that:

- Exports `radius: float = 140.0`, `dead_zone_px: float = 15.0`.
- Tracks an active touch index (`_active_touch := -1`) so a second finger elsewhere doesn't hijack.
- On `InputEventScreenTouch` inside `get_global_rect()`: capture index, recenter the knob to the touch position (touch-anywhere-to-grab feel).
- On `InputEventScreenDrag` with matching index: update knob position clamped to `radius`.
- On touch release: reset knob to center, clear index.
- Each frame with an active touch, compute `v = (knob_offset / radius)` clamped to length 1, apply dead-zone: if `abs(v.x) < dead_zone_px/radius` → 0, same for y.
- Call `Input.action_press("throttle_forward", -v.y)` when `v.y < 0`, else release; symmetric for reverse/steer axes. Release all four on touch end.

Draws with `_draw()` (two circles) — no textures needed.

---

### Task 3: Wire joystick into HUD, gate on touchscreen detection

**Files:** [scenes/HUD.tscn](scenes/HUD.tscn), [scripts/hud.gd](scripts/hud.gd)

- Add a `Control` node `TouchControls` at bottom-left of `HUD.tscn`, script = `virtual_joystick.gd`, anchored bottom-left with a margin, visible = false by default.
- In `hud.gd._ready()`, before the existing help-fade coroutine:
  - `var touch := DisplayServer.is_touchscreen_available()`
  - `$TouchControls.visible = touch`
  - If touch: `$HelpOverlay/KeysContainer.visible = false` and set `$HelpOverlay/CaptionLabel.text = "Drag the stick to drive"`.

**Verify:** Run in editor (touch off → joystick hidden, WASD works). Then use Godot's `--debug-touchscreen` flag or DevTools touch emulation on the web export to confirm the joystick appears and drives the truck.

---

### Task 4: Local mobile smoke test via web export

**Files:** none (workflow only)

- Export web build to `/tmp/mobile-test/` using the existing `Web` preset.
- Serve with `python3 -m http.server 8000 --directory /tmp/mobile-test` (or the repo's existing tool if one exists — check `tools/`).
- Open on a phone browser at `http://<laptop-ip>:8000` (same Wi-Fi). Confirm:
  - Joystick visible bottom-left on phone; hidden on desktop.
  - Dragging within the ring steers/throttles the truck smoothly.
  - Multi-touch doesn't glitch (e.g., second finger tapping the HUD area).
  - Pinch-zoom doesn't zoom the page canvas. If it does → follow up with the custom HTML shell mentioned in design §5.

If any of the above fails, iterate before Task 5.

---

### Task 5: Publish

Only after Task 4 passes. Follow the existing publish flow (whatever `notes/plans/2026-07-12-github-pages-publish.md` prescribes) — export to `docs/v1/` (or a new `docs/v2/` per that plan's versioning rules), update `docs/index.html`, commit.

---

## Resolved decisions

1. **Publish target:** override `docs/v1/` in place — no new version dir, no `docs/index.html` change.
2. **Portrait rotate overlay:** skipped for this iteration. Landscape-first; portrait will look bad and that's accepted.
