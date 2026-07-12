extends RigidBody3D

@export var damage_cost: int = 50
## Alpha 0 means "no override, use the mesh's authored material as-is".
@export var color_override: Color = Color(0, 0, 0, 0)

var _already_hit: bool = false

func _ready() -> void:
	add_to_group("damageable")
	if color_override.a > 0.0:
		_apply_color_override(self)

func _apply_color_override(node: Node) -> void:
	if node is MeshInstance3D:
		var material := StandardMaterial3D.new()
		material.albedo_color = color_override
		material.roughness = 0.9
		node.set_surface_override_material(0, material)
	for child in node.get_children():
		_apply_color_override(child)

## Called by the truck when it collides with this obstacle. Returns the damage
## cost on first hit, or 0 if it was already hit (prevents double-counting).
## Detection lives on the truck rather than here because a frozen RigidBody3D
## (used for buildings so they don't get knocked around) does not reliably
## emit its own body_entered/contact_monitor signals in Godot 4.7.
func register_hit() -> int:
	if _already_hit:
		return 0
	_already_hit = true
	remove_from_group("damageable")
	return damage_cost
