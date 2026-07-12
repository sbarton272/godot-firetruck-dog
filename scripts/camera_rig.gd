extends Node3D

@export var target_path: NodePath
@export var offset: Vector3 = Vector3(0, 9, 9)
@export var follow_smoothing: float = 4.0

var _target: Node3D

func _ready() -> void:
	_target = get_node(target_path)
	global_position = _target.global_position + offset

func _process(delta: float) -> void:
	if _target == null:
		return
	var target_position := _target.global_position + offset
	global_position = global_position.lerp(target_position, 1.0 - exp(-follow_smoothing * delta))
