extends Node3D

@export var truck_path: NodePath
@export var hud_path: NodePath
@export var goal_area_path: NodePath
@export var start_point_path: NodePath

var total_damage: int = 0
var _game_over: bool = false

func _ready() -> void:
	add_to_group("game_state")
	var truck: Node3D = get_node(truck_path)
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
	var truck_body: RigidBody3D = get_node(truck_path).get_node("TruckBody")
	truck_body.freeze = true
	truck_body.set_active(false)
	get_node(hud_path).show_end_screen(total_damage)
