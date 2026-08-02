extends Control

@export var radius: float = 140.0
@export var dead_zone_ratio: float = 0.12
@export var base_color: Color = Color(0.08, 0.08, 0.08, 0.45)
@export var ring_color: Color = Color(1, 1, 1, 0.85)
@export var knob_color: Color = Color(1, 1, 1, 0.95)
@export var ring_width: float = 3.0
@export var knob_radius_ratio: float = 0.36

const _ACTIONS := ["throttle_forward", "throttle_reverse", "steer_left", "steer_right"]

var _active_touch: int = -1
var _touch_center: Vector2 = Vector2.ZERO
var _knob_offset: Vector2 = Vector2.ZERO
var _vector: Vector2 = Vector2.ZERO

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	custom_minimum_size = Vector2(radius * 2.0, radius * 2.0)
	visibility_changed.connect(_on_visibility_changed)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and _active_touch == -1:
			_begin(event.index, event.position)
		elif not event.pressed and event.index == _active_touch:
			_release()
			accept_event()
	elif event is InputEventScreenDrag and event.index == _active_touch:
		_update_drag(event.position)
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed and _active_touch == -1:
			_begin(-2, event.position)
		elif not event.pressed and _active_touch == -2:
			_release()
			accept_event()
	elif event is InputEventMouseMotion and _active_touch == -2:
		_update_drag(event.position)

func _begin(index: int, pos: Vector2) -> void:
	_active_touch = index
	_touch_center = pos
	_knob_offset = Vector2.ZERO
	_vector = Vector2.ZERO
	queue_redraw()
	accept_event()

func _update_drag(pos: Vector2) -> void:
	var delta: Vector2 = pos - _touch_center
	if delta.length() > radius:
		delta = delta.normalized() * radius
	_knob_offset = delta
	_vector = delta / radius
	queue_redraw()
	accept_event()

func _process(_delta: float) -> void:
	if _active_touch == -1:
		return
	var vx: float = _vector.x
	var vy: float = _vector.y
	if absf(vx) < dead_zone_ratio:
		vx = 0.0
	if absf(vy) < dead_zone_ratio:
		vy = 0.0
	_set_axis("throttle_forward", -vy if vy < 0.0 else 0.0)
	_set_axis("throttle_reverse", vy if vy > 0.0 else 0.0)
	_set_axis("steer_left", -vx if vx < 0.0 else 0.0)
	_set_axis("steer_right", vx if vx > 0.0 else 0.0)

func _set_axis(action: String, strength: float) -> void:
	if strength > 0.0:
		Input.action_press(action, strength)
	else:
		Input.action_release(action)

func _release() -> void:
	_active_touch = -1
	_touch_center = Vector2.ZERO
	_knob_offset = Vector2.ZERO
	_vector = Vector2.ZERO
	for a in _ACTIONS:
		Input.action_release(a)
	queue_redraw()

func _on_visibility_changed() -> void:
	if not visible and _active_touch != -1:
		_release()

func _draw() -> void:
	var center: Vector2 = _touch_center if _active_touch != -1 else size * 0.5
	draw_circle(center, radius, base_color)
	draw_arc(center, radius, 0.0, TAU, 48, ring_color, ring_width, true)
	var knob_center: Vector2 = center + _knob_offset
	var knob_r: float = radius * knob_radius_ratio
	draw_circle(knob_center, knob_r, knob_color)
	draw_arc(knob_center, knob_r, 0.0, TAU, 32, Color(0, 0, 0, 0.55), 2.0, true)
