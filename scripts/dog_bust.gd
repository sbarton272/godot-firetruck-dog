extends Node3D

@export var lean_amount_degrees: float = 12.0
@export var lean_smoothing: float = 6.0

func _process(delta: float) -> void:
	var steer_input := Input.get_axis("steer_right", "steer_left")
	var target_lean := deg_to_rad(lean_amount_degrees) * steer_input
	rotation.z = lerp_angle(rotation.z, target_lean, 1.0 - exp(-lean_smoothing * delta))
