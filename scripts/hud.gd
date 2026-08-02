extends CanvasLayer

@export var help_display_seconds: float = 2.5
@export var help_fade_seconds: float = 0.6

func _ready() -> void:
	var touch: bool = DisplayServer.is_touchscreen_available()
	$TouchControls.visible = touch
	if touch:
		$HelpOverlay/CaptionLabel.text = "Drag the stick to drive"
		$HelpOverlay/KeysContainer.visible = false
	$HelpOverlay.modulate.a = 1.0
	await get_tree().create_timer(help_display_seconds).timeout
	var tween := create_tween()
	tween.tween_property($HelpOverlay, "modulate:a", 0.0, help_fade_seconds)
	await tween.finished
	$HelpOverlay.visible = false

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

func _on_restart_button_pressed() -> void:
	get_tree().reload_current_scene()
