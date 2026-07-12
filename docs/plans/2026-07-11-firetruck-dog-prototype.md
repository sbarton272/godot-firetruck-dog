# Chief Waffles, Firehouse Dog — Prototype Implementation Plan

## Context

The user wants a prototype game built in this Godot project: a dalmatian firehouse dog drives a firetruck across a small town to reach a fire, but drives badly (loose, drifty, hard-to-control physics). Hitting things adds to a running dollar-damage counter; the goal is to reach the fire while minimizing damage. Drives should take about 1 minute. Visual style: cute, muted-color low-poly 3D primitives (no textures), viewed from a fixed isometric-style camera — evoking Untitled Goose Game. The prototype must also be exportable to web (HTML5/WebGL) so it can be shared/played in a browser.

This plan was developed through a brainstorming session. Key decisions (do not deviate):
- **3D with fixed isometric-style camera**, not true 2D isometric — primitive meshes with flat `StandardMaterial3D` colors, no textures/imported models.
- **Custom RigidBody3D arcade controller** for the truck (not `VehicleBody3D`) — hand-tuned thrust/torque/low-grip physics for a drifty, oversteer-prone feel, with a subtle idle lean tied to steering shown on a small visible dog bust in the driver's seat.
- **Camera**: fixed elevation/angle, smoothly follows truck position, never rotates with truck heading.
- **Scene structure**: `Main.tscn` is the composition root and directly contains the town layout (roads/buildings/obstacles/start/goal) as organizational sub-nodes — **no separate `Town.tscn` file** (this was tried and then reverted back to merged, per user feedback). `Truck.tscn` stays a separate, independently-testable scene (truck + camera + dog). `HUD.tscn` stays separate (damage counter + end screen).
- **Damage system**: fixed per-obstacle-type dollar costs — mailbox $50, trash can $30, parked car $500, lamp post $150, fence $100, **and now buildings too** (e.g. $300 for a standard building, tunable per instance for bigger ones) — obstacles are `RigidBody3D`/`StaticBody3D` in a `"damageable"` group and react to truck impact. The one exception is the goal building (the burning building) — it is not damageable, it's the win trigger.
- **Win condition**: reaching a `GoalArea` near a burning building freezes the truck and shows an end screen with damage total + threshold-based flavor-text rating + restart button.
- **Web export**: get local Web (HTML5/WebGL) export working and verified in-browser; no hosting/deployment automation.
- **Engine version**: upgrade from the previously-installed Godot 4.2.1 to the latest stable **Godot 4.7** (via the Homebrew cask `godot`), and fully target 4.7 going forward — `project.godot` and this repo's `CLAUDE.md` engine-version references updated to 4.7.
- **Plans folder**: rename the repo's top-level `plans/` folder to `docs/plans/` (matching the brainstorming skill's default convention), and update CLAUDE.md's reference from `plans/` to `docs/plans/`.

## Assumptions / conventions

- New scripts under `res://scripts/` (obstacle scripts under `res://scripts/obstacles/`); scenes under `res://scenes/` (obstacle scenes under `res://scenes/obstacles/`).
- Godot 4.7, GL Compatibility renderer (still the right choice for web export) — GDScript only. One `DirectionalLight3D` + `WorldEnvironment` (soft muted sky) packaged as a reusable `res://scenes/env/GameEnvironment.tscn`, instanced into both `Truck.tscn` (for isolated testing) and `Main.tscn`.
- Input actions (Project Settings → Input Map, or edit `project.godot`'s `[input]` section): `throttle_forward` (W/Up), `throttle_reverse` (S/Down), `steer_left` (A/Left), `steer_right` (D/Right).
- Groups: `"player_truck"` (truck `RigidBody3D`), `"damageable"` (obstacle + building roots), `"game_state"` (Main.tscn root script — obstacles report damage via `get_tree().call_group("game_state", "add_damage", cost)` rather than holding a direct reference).
- Verify exact Godot 4.7 API names/behavior against https://docs.godotengine.org/en/4.7/classes/ while implementing — some property/class names may differ from the 4.2 docs referenced during earlier design discussion (e.g. double check `RigidBody3D.apply_central_force`/`apply_torque`, `contact_monitor`/`max_contacts_reported`, `body_entered`, `Area3D.body_entered`, `Node.top_level`, `RigidBody3D.freeze`, `get_tree().reload_current_scene()` are still current in 4.7).

---

## Phase 0 — Upgrade Godot + project scaffolding

1. Upgrade the installed Godot app: `brew upgrade --cask godot`. Confirm with `godot --version` afterward.
2. Open the project in the upgraded editor, let it re-save/migrate `project.godot` to 4.7 conventions. Update `config/features` in `project.godot` accordingly.
3. Update this repo's `CLAUDE.md` "Engine version" line from `Godot 4.2` to `Godot 4.7`, and update the docs-order note to point at the 4.7 docs branch instead of 4.2.
4. Rename the repo's top-level `plans/` folder to `docs/plans/` (`git mv plans docs/plans`), update the `CLAUDE.md` project-layout line referencing `plans/` to `docs/plans/`, and save this implementation plan into the repo at `docs/plans/2026-07-11-firetruck-dog-prototype.md`.
5. Create folders: `res://scenes/`, `res://scenes/obstacles/`, `res://scenes/env/`, `res://scripts/`, `res://scripts/obstacles/`.
6. Add the four input actions listed above in the Input Map.
7. Create `res://scenes/env/GameEnvironment.tscn`: a `Node3D` with a `WorldEnvironment` (soft muted-sky `Environment` resource) + a `DirectionalLight3D` angled ~-45°.

**Verify:** `godot --version` reports 4.7.x; project opens in the 4.7 editor with no Output panel errors; Input Map shows the four new actions; `CLAUDE.md` reflects 4.7 and `docs/plans/`; `docs/plans/2026-07-11-firetruck-dog-prototype.md` exists in the repo.

---

## Phase 1 — Truck controller in isolation

**Files:** `res://scripts/truck_controller.gd`, `res://scenes/Truck.tscn` (physics-only for now).

**Truck.tscn (partial):**
```
Truck (Node3D)
└── TruckBody (RigidBody3D)     [group: "player_truck", script: truck_controller.gd]
    ├── CollisionShape3D (BoxShape3D ~2m x 1.2m x 4m)
    └── ChassisMesh (MeshInstance3D, BoxMesh, muted red material)
└── GameEnvironment (instance of env/GameEnvironment.tscn)
```

**`truck_controller.gd` exported tunables:**
```gdscript
@export var thrust_force: float = 4000.0
@export var reverse_thrust_force: float = 2000.0
@export var turn_torque: float = 1800.0
@export var turn_torque_falloff_speed: float = 8.0
@export var min_turn_torque_scale: float = 0.35
@export var lateral_grip: float = 0.15   # 0 = pure ice, 1 = no slide
var is_active: bool = true
```
Also tune native `RigidBody3D` properties in the Inspector: `linear_damp`/`angular_damp` kept low (e.g. 0.2–0.5) so the truck coasts/slides; `mass` ~800.

**Physics logic (`_physics_process(delta)`; skip entirely if `is_active == false`):**
- Read `Input.get_axis("throttle_reverse", "throttle_forward")` and `Input.get_axis("steer_right", "steer_left")`.
- Forward force along `-global_transform.basis.z`, scaled by `thrust_force` or `reverse_thrust_force` depending on sign.
- Speed-scaled steering torque: `torque_scale = clamp(1.0 - linear_velocity.length() / turn_torque_falloff_speed, min_turn_torque_scale, 1.0)`; apply `Vector3.UP * steer_input * turn_torque * torque_scale` via `apply_torque`.
- Low-grip lateral friction (the source of the drift): `right = global_transform.basis.x`, `lateral_speed = linear_velocity.dot(right)`, apply `-right * lateral_speed * lateral_grip * mass` via `apply_central_force`.
- Don't manually zero angular velocity — let low `angular_damp` be the only settling force, so the truck keeps spinning slightly after hard turns.
- Add a public `set_active(active: bool)` method that flips `is_active` (used later by `game_state.gd` to stop the truck at the win condition without fighting `freeze`).

**Verify:** open `Truck.tscn`, run it standalone (F6). Confirm forward/reverse work, steering has visible torque, and the truck noticeably slides/oversteers at speed rather than tracking cleanly. Confirm it coasts to a stop rather than snapping. Iterate on the exported tunables live in the Inspector until it feels "loose and drifty but learnable within about a minute."

---

## Phase 2 — Camera rig

**Files:** `res://scripts/camera_rig.gd`, update `res://scenes/Truck.tscn`.

**Truck.tscn addition:**
```
Truck (Node3D)
├── TruckBody (RigidBody3D) ...
├── CameraRig (Node3D)   [top_level = true, script: camera_rig.gd]
│   └── Camera3D          [current = true, fixed rotation_degrees ≈ (-35, 45, 0)]
```
`Node.top_level = true` on `CameraRig` makes its transform world-space, ignoring the parent — so the script fully owns its position (lerped toward the truck) while `Camera3D`'s local rotation stays fixed regardless of truck heading.

**`camera_rig.gd`:**
```gdscript
@export var target_path: NodePath        # -> TruckBody
@export var offset: Vector3 = Vector3(0, 9, 9)
@export var follow_smoothing: float = 4.0
```
In `_process(delta)`: `global_position = global_position.lerp(target.global_position + offset, 1.0 - exp(-follow_smoothing * delta))`. Camera rotation is set once and never touched.

**Verify:** run `Truck.tscn`. Camera should smoothly trail truck position with no jitter/snapping, while its viewing angle stays constant even as the truck spins.

---

## Phase 3 — Town layout + obstacles (built directly inside Main.tscn)

**Files:**
- `res://scenes/Main.tscn` (town layout built here directly — no separate Town.tscn)
- `res://scripts/obstacles/obstacle_base.gd`
- `res://scenes/obstacles/{Mailbox,TrashCan,ParkedCar,LampPost,FenceSegment,Building}.tscn`

**Main.tscn town-layout portion (Truck + HUD instances added in Phase 5):**
```
Main (Node3D)   [group: "game_state", script: game_state.gd — added in Phase 5]
├── Roads (Node3D)          — road/sidewalk meshes + StaticBody3D collision, a few connected blocks
├── Buildings (Node3D)      — instances of Building.tscn (now damageable, see below) framing the route
├── GoalBuilding (Node3D)   — the distinct "burning building" (orange/red accent), NOT damageable — it's the win trigger, not an obstacle
├── Obstacles (Node3D)      — instances of Mailbox/TrashCan/ParkedCar/LampPost/FenceSegment along the main route and a side street or two (route choice)
├── StartPoint (Marker3D)
└── GoalArea (Area3D)       — near GoalBuilding
```

**Obstacle pattern** (each obstacle scene root is a `RigidBody3D` in group `"damageable"` with a `CollisionShape3D` + primitive `MeshInstance3D`; `Building.tscn` uses the same script/pattern but as a heavier `RigidBody3D` or `StaticBody3D` — see note below):
```gdscript
# obstacle_base.gd
@export var damage_cost: int = 50
var _already_hit := false

func _ready() -> void:
    contact_monitor = true
    max_contacts_reported = 4
    body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node) -> void:
    if _already_hit or not body.is_in_group("player_truck"):
        return
    _already_hit = true
    get_tree().call_group("game_state", "add_damage", damage_cost)
    remove_from_group("damageable")
```
Default costs: Mailbox $50, TrashCan $30, ParkedCar $500, LampPost $150, FenceSegment $100, **Building $300** (tune up per instance for larger buildings via the exported `damage_cost`).

**Building note:** unlike the small obstacles, buildings should stay structurally fixed (not go flying) when hit — implement `Building.tscn` as a `StaticBody3D` root instead of `RigidBody3D` so it doesn't get knocked around, but still detect the truck hitting it. Since `StaticBody3D` has no `body_entered` contact signal by default, either (a) wrap the building's collision in a child `Area3D` that listens for the truck entering and reuses the same damage-report call, or (b) give the building a lightweight `RigidBody3D` with `freeze = true`/`freeze_mode = STATIC` so it still gets `body_entered` contact monitoring like the other obstacles but doesn't physically move. Prefer (b) for consistency with `obstacle_base.gd`'s existing contact-monitor logic — just add `freeze = true` and `freeze_mode = FREEZE_MODE_STATIC` in `Building.tscn`'s inspector so `obstacle_base.gd` can be reused unmodified.

**Verify:** open `Main.tscn` (town portion only, Truck/HUD not yet wired) — layout reads as a few connected blocks, `GoalBuilding` is visually distinct and NOT in the damageable group, regular buildings + obstacles line the route with at least one alternate path, and static-frozen buildings don't get knocked around when hit but still register a hit exactly once.

---

## Phase 4 — Damage system + HUD

**Files:** `res://scenes/HUD.tscn`, `res://scripts/hud.gd`.

**HUD.tscn:**
```
HUD (CanvasLayer)
├── DamageLabel (Label)        — corner "$0" counter
└── EndScreen (Control)        — hidden until win
    ├── DimBackground (ColorRect)
    ├── ResultLabel (Label)
    ├── RatingLabel (Label)
    └── RestartButton (Button)
```

**`hud.gd`:**
```gdscript
func update_damage(total: int) -> void:
    $DamageLabel.text = "$%d" % total

func show_end_screen(total: int) -> void:
    $EndScreen.visible = true
    $EndScreen/ResultLabel.text = "Total damage: $%d" % total
    $EndScreen/RatingLabel.text = _rating_for(total)

func _rating_for(total: int) -> String:
    if total < 200:
        return "Hero of the day!"
    elif total < 600:
        return "Could've been worse."
    else:
        return "The town is suing you."
```
`RestartButton.pressed` connects to `get_tree().reload_current_scene()`.

**Verify:** run `HUD.tscn` standalone to check label placement/legibility; toggle `EndScreen.visible` manually via the Remote scene tree to sanity-check the overlay.

---

## Phase 5 — Win condition + final Main.tscn composition

**Files:** update `res://scenes/Main.tscn`, `res://scripts/game_state.gd`.

**Main.tscn additions:**
```
Main (Node3D)   [group: "game_state", script: game_state.gd]
├── Roads / Buildings / GoalBuilding / Obstacles / StartPoint / GoalArea   (from Phase 3)
├── Truck (instance of Truck.tscn)
└── HUD (instance of HUD.tscn)
```

**`game_state.gd`:**
```gdscript
@export var truck_path: NodePath
@export var hud_path: NodePath
@export var goal_area_path: NodePath
@export var start_point_path: NodePath

var total_damage: int = 0
var _game_over: bool = false

func _ready() -> void:
    var truck := get_node(truck_path)
    truck.global_position = get_node(start_point_path).global_position
    get_node(goal_area_path).body_entered.connect(_on_goal_entered)

func add_damage(amount: int) -> void:
    if _game_over:
        return
    total_damage += amount
    get_node(hud_path).update_damage(total_damage)

func _on_goal_entered(body: Node) -> void:
    if _game_over or not body.is_in_group("player_truck"):
        return
    _game_over = true
    var truck_body := get_node(truck_path).get_node("TruckBody")
    truck_body.freeze = true
    truck_body.set_active(false)
    get_node(hud_path).show_end_screen(total_damage)
```
`freeze = true` stops physics response; `set_active(false)` (from Phase 1) stops the controller from still applying forces to a frozen body. (Note: paths changed from `town_path` to direct `goal_area_path`/`start_point_path` since the town nodes now live directly under `Main` rather than under a separate `Town` instance.)

**Verify:** run `Main.tscn`. Truck spawns at `StartPoint`; HUD starts at `$0` and updates live and correctly as obstacles/buildings are hit (no double-counting); driving to `GoalArea` freezes the truck and shows the end screen with correct total + rating; Restart reloads to a clean state. Specifically test re-colliding with an already-hit, still-nearby obstacle/building to confirm no double-charge, and confirm buildings don't get knocked out of place when hit.

---

## Phase 6 — Web export verification

1. In the Godot 4.7 editor, install Web export templates matching 4.7 if missing (Editor → Manage Export Templates).
2. Project → Export → Add… → Web. Export path e.g. `web-build/index.html`; add `web-build/` to `.gitignore`.
3. Confirm the preset doesn't override the project's existing `gl_compatibility` rendering method.
4. Export the project (produces `.html`/`.js`/`.wasm`/`.pck`).
5. Serve locally over HTTP (Web export requires HTTP, not `file://`) — e.g. `python3 -m http.server 8060` from `web-build/`, then open `http://localhost:8060/index.html`.
6. In-browser, confirm: game boots with no console errors, truck drives with the same drifty feel, obstacles and buildings register damage and update the HUD live, reaching the goal shows the end screen with working restart.

**Constraints already respected by earlier phases:** GDScript only (no GDExtension), no threading, no imported textures/models (primitive meshes + flat materials only), no file I/O/save system.

---

## Critical files
- `scripts/truck_controller.gd`
- `scripts/camera_rig.gd`
- `scripts/obstacles/obstacle_base.gd`
- `scripts/game_state.gd`
- `scripts/hud.gd`
- `scenes/Main.tscn` (contains town layout directly), `scenes/Truck.tscn`, `scenes/HUD.tscn`
- `scenes/obstacles/*.tscn` (including `Building.tscn`)
- `project.godot` (4.7 conversion + input actions), `CLAUDE.md` (engine version bump to 4.7)
- `export_presets.cfg` (created via editor Export dialog in Phase 6)
