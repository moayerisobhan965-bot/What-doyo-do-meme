extends Control
## Spielende - Sieger und Endstand

func _ready() -> void:
	_build_ui()

func _build_ui() -> void:
	add_child(UI.background())

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", 18)
	outer.custom_minimum_size = Vector2(700, 0)
	center.add_child(outer)

	outer.add_child(UI.title("🏁 Spiel vorbei!", 58))

	var room := Global.room
	var winner_id := str(room.get("winner_id", ""))
	var winner_name := "Unbekannt"
	for p in room.get("players", []):
		if str(p.get("id", "")) == winner_id:
			winner_name = str(p.get("name", "?"))
	if winner_name == "Unbekannt" and not winner_id.is_empty():
		winner_name = winner_id

	var i_won := winner_id == Global.player_id
	var win_label := UI.label(
		"🎉 %s hat gewonnen!" % winner_name if not i_won else "🎉 DU HAST GEWONNEN!",
		40, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(win_label)

	var panel := UI.panel()
	panel.custom_minimum_size = Vector2(700, 0)
	outer.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)

	box.add_child(UI.label("Endstand:", 28, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER))

	var scores: Dictionary = room.get("scores", {})
	var rows: Array = []
	var players: Array = room.get("players", [])
	for p in players:
		var pid := str(p.get("id", ""))
		var s := int(scores.get(pid, 0))
		rows.append({"name": str(p.get("name", "?")), "score": s, "winner": pid == winner_id})

	rows.sort_custom(func(a, b): return a["score"] > b["score"])

	var rows_box := VBoxContainer.new()
	rows_box.add_theme_constant_override("separation", 8)
	box.add_child(rows_box)

	for r in rows:
		var row := HBoxContainer.new()
		rows_box.add_child(row)
		var nm := UI.label(str(r["name"]), 26)
		if r["winner"]:
			nm.text = "👑 " + str(r["name"])
			nm.add_theme_color_override("font_color", UI.GOLD)
		nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(nm)
		row.add_child(UI.label("%d Punkte" % int(r["score"]), 26, UI.TEXT, HORIZONTAL_ALIGNMENT_RIGHT))

	var play_again := UI.button("🏠 Zurück zur Startseite", 28)
	play_again.pressed.connect(_on_home_pressed)
	outer.add_child(play_again)

func _on_home_pressed() -> void:
	Global.send_ws({"event": "leave_room"})
	Global.close_ws()
	get_tree().change_scene_to_file("res://scenes/home.tscn")

# Android-Zurück-Button → Startseite
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		_on_home_pressed()
