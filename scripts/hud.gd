extends CanvasLayer

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
