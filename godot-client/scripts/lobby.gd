extends Control
## Lobby - Wartezimmer: Spielerliste, Raumcode, Spielstart (nur Host)

var _code_label: Label
var _setting_label: Label
var _players_box: VBoxContainer
var _status: Label
var _start_button: Button
var _leave_button: Button

func _ready() -> void:
	_build_ui()
	Global.ws_message.connect(_on_ws_message)
	Global.ws_open.connect(_on_ws_open)
	Global.ws_closed.connect(_on_ws_closed)
	Global.ws_error.connect(_on_ws_error)

	if Global.room.is_empty() and not Global.room_code.is_empty():
		_set_status("Verbinde mit Raum %s..." % Global.room_code)
	else:
		_render_room()

	if not Global.is_ws_open():
		Global.connect_ws(Global.room_code)

func _exit_tree() -> void:
	if Global.ws_message.is_connected(_on_ws_message):
		Global.ws_message.disconnect(_on_ws_message)
	if Global.ws_open.is_connected(_on_ws_open):
		Global.ws_open.disconnect(_on_ws_open)
	if Global.ws_closed.is_connected(_on_ws_closed):
		Global.ws_closed.disconnect(_on_ws_closed)
	if Global.ws_error.is_connected(_on_ws_error):
		Global.ws_error.disconnect(_on_ws_error)

func _build_ui() -> void:
	add_child(UI.background())

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", 18)
	outer.custom_minimum_size = Vector2(680, 0)
	center.add_child(outer)

	outer.add_child(UI.title("🏠 Lobby", 52))

	_code_label = UI.label("Raum: ----", 40, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(_code_label)

	var hint := UI.label("Teile den Code mit deinen Freunden!", 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(hint)

	_setting_label = UI.label("", 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(_setting_label)

	var panel := UI.panel()
	panel.custom_minimum_size = Vector2(680, 340)
	outer.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)

	var players_label := UI.label("Spieler:", 26, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER)
	box.add_child(players_label)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size = Vector2(0, 220)
	box.add_child(scroll)
	_players_box = VBoxContainer.new()
	_players_box.add_theme_constant_override("separation", 8)
	_players_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_players_box)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	outer.add_child(row)
	_start_button = UI.button("🚀 Spiel starten", 28)
	_start_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_start_button.pressed.connect(_on_start_pressed)
	row.add_child(_start_button)
	_leave_button = UI.button_danger("Raum verlassen", 28)
	_leave_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_leave_button.pressed.connect(_on_leave_pressed)
	row.add_child(_leave_button)

	_status = UI.label("", 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.custom_minimum_size = Vector2(0, 54)
	outer.add_child(_status)

func _on_ws_open() -> void:
	# In der Lobby immer anmelden (idempotent auf dem Server)
	Global.send_ws({"event": "join_room"})

func _on_ws_message(msg: Dictionary) -> void:
	var event := str(msg.get("event", ""))
	if msg.has("room") and msg["room"] is Dictionary:
		Global.room = msg["room"]

	match event:
		"room_joined", "room_state", "player_left", "game_started":
			_render_room()
		"round_started", "voting_started", "round_result":
			# Spiel läuft - zur Spielszene wechseln
			get_tree().change_scene_to_file("res://scenes/game.tscn")
		"game_over":
			get_tree().change_scene_to_file("res://scenes/game_over.tscn")
		"error":
			_set_status("❌ " + str(msg.get("message", "Fehler")), UI.RED)

	# Wenn der Raum schon läuft (Rejoin): direkt ins Spiel
	if not Global.room.is_empty():
		var state := str(Global.room.get("state", "lobby"))
		if state in ["playing", "voting", "result"]:
			get_tree().change_scene_to_file("res://scenes/game.tscn")
		elif state == "game_over":
			get_tree().change_scene_to_file("res://scenes/game_over.tscn")

func _render_room() -> void:
	if Global.room.is_empty():
		return
	var code := str(Global.room.get("code", ""))
	_code_label.text = "Raum: %s" % code
	Global.room_code = code

	# Spiel-Einstellungen anzeigen
	var rounds_limit := int(Global.room.get("rounds_limit", 0))
	var max_players := int(Global.room.get("max_players", 10))
	var rounds_text := "Unbegrenzt" if rounds_limit == 0 else str(rounds_limit)
	_setting_label.text = "👥 bis zu %d Spieler  |  🔄 %s Runden" % [max_players, rounds_text]

	# Spielerliste neu aufbauen
	for child in _players_box.get_children():
		child.queue_free()

	var players: Array = Global.room.get("players", [])
	var host_id := str(Global.room.get("host_id", ""))
	var is_host := host_id == Global.player_id

	_start_button.visible = is_host
	_start_button.disabled = players.size() < 2
	if is_host:
		if players.size() < 2:
			_set_status("Warte auf Spieler... (mind. 2 nötig)")
		else:
			_set_status("Du bist der Host - starte das Spiel!")

	for p in players:
		var pid := str(p.get("id", ""))
		var pname := str(p.get("name", "?"))
		var p_host := bool(p.get("is_host", false))
		var p_guest := bool(p.get("is_guest", false))
		var p_score := int(p.get("score", 0))

		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		_players_box.add_child(row)

		var name_label := UI.label(pname, 26)
		if p_host:
			name_label.text = "👑 " + pname
			name_label.add_theme_color_override("font_color", UI.GOLD)
		if p_guest:
			name_label.text += " 🎮 Gast"
		if pid == Global.player_id:
			name_label.text += " (Du)"
			name_label.add_theme_color_override("font_color", UI.GREEN)
		name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(name_label)

		var score_label := UI.label("Punkte: %d" % p_score, 22, UI.MUTED, HORIZONTAL_ALIGNMENT_RIGHT)
		row.add_child(score_label)

func _on_start_pressed() -> void:
	Global.send_ws({"event": "start_game"})
	_set_status("Spiel wird gestartet...")

func _on_leave_pressed() -> void:
	Global.send_ws({"event": "leave_room"})
	Global.close_ws()
	get_tree().change_scene_to_file("res://scenes/home.tscn")

func _on_ws_closed() -> void:
	_set_status("❌ Verbindung zum Server verloren.", UI.RED)
	Global.close_ws()
	get_tree().change_scene_to_file("res://scenes/home.tscn")

func _on_ws_error(message: String) -> void:
	_set_status("❌ " + message, UI.RED)

func _set_status(text: String, color: Color = UI.MUTED) -> void:
	_status.text = text
	_status.add_theme_color_override("font_color", color)

# Android-Zurück-Button → Raum verlassen
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		_on_leave_pressed()
