extends RigidBody3D

@export var thrust_force: float = 4000.0
@export var reverse_thrust_force: float = 2000.0
@export var turn_torque: float = 1800.0
@export var turn_torque_falloff_speed: float = 8.0
@export var min_turn_torque_scale: float = 0.35
@export var lateral_grip: float = 0.15

var is_active: bool = true

func _ready() -> void:
	add_to_group("player_truck")
	contact_monitor = true
	max_contacts_reported = 8
	body_entered.connect(_on_body_entered)

func set_active(active: bool) -> void:
	is_active = active

func _on_body_entered(body: Node) -> void:
	if not body.is_in_group("damageable") or not body.has_method("register_hit"):
		return
	var cost: int = body.register_hit()
	if cost > 0:
		get_tree().call_group("game_state", "add_damage", cost)

func _physics_process(_delta: float) -> void:
	if not is_active:
		return

	var throttle_input := Input.get_axis("throttle_reverse", "throttle_forward")
	var steer_input := Input.get_axis("steer_right", "steer_left")

	if throttle_input > 0.0:
		apply_central_force(-global_transform.basis.z * throttle_input * thrust_force)
	elif throttle_input < 0.0:
		apply_central_force(-global_transform.basis.z * throttle_input * reverse_thrust_force)

	var speed := linear_velocity.length()
	var torque_scale: float = clamp(1.0 - speed / turn_torque_falloff_speed, min_turn_torque_scale, 1.0)
	apply_torque(Vector3.UP * steer_input * turn_torque * torque_scale)

	var right := global_transform.basis.x
	var lateral_speed := linear_velocity.dot(right)
	apply_central_force(-right * lateral_speed * lateral_grip * mass)
