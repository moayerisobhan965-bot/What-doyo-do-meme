extends Control
## Home - nach dem Login: Raum erstellen oder beitreten, Statistiken

var _greeting: Label
var _stats: Label
var _status: Label
var _code_input: LineEdit
var _join_button: Button
var _create_button: Button
var _players_value: Label
var _rounds_option: OptionButton
var _joining := false
var _player_count := 4
var _rounds_limit := 0   # 0 = unbegrenzt

func _ready() -> void:
	_build_ui()
	Global.ws_message.connect(_on_ws_message)
	Global.ws_open.connect(_on_ws_open)
	Global.ws_closed.connect(_on_ws_closed)
	Global.ws_error.connect(_on_ws_error)
	_load_stats()

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
	outer.add_theme_constant_override("separation", 22)
	outer.custom_minimum_size = Vector2(640, 0)
	center.add_child(outer)

	outer.add_child(UI.title("🎮 What Meme", 56))

	_greeting = UI.label("", 30, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(_greeting)
	_greeting.text = "Hallo, %s!" % str(Global.user.get("username", "Spieler"))

	_stats = UI.label("Spiele: - | Siege: -", 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(_stats)

	var panel := UI.panel()
	panel.custom_minimum_size = Vector2(640, 0)
	outer.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 16)
	panel.add_child(box)

	var create_label := UI.label("Neues Spiel erstellen:", 26, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER)
	box.add_child(create_label)

	# Spieler-Anzahl (2-10)
	var players_row := HBoxContainer.new()
	players_row.add_theme_constant_override("separation", 12)
	box.add_child(players_row)
	var players_title := UI.label("Spieler:", 26, UI.TEXT)
	players_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	players_row.add_child(players_title)
	var minus_btn := UI.button_secondary("−", 30)
	minus_btn.custom_minimum_size = Vector2(76, 76)
	minus_btn.pressed.connect(_on_players_minus)
	players_row.add_child(minus_btn)
	_players_value = UI.label(str(_player_count), 32, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	_players_value.custom_minimum_size = Vector2(90, 0)
	players_row.add_child(_players_value)
	var plus_btn := UI.button_secondary("+", 30)
	plus_btn.custom_minimum_size = Vector2(76, 76)
	plus_btn.pressed.connect(_on_players_plus)
	players_row.add_child(plus_btn)

	# Runden-Auswahl
	var rounds_row := HBoxContainer.new()
	rounds_row.add_theme_constant_override("separation", 12)
	box.add_child(rounds_row)
	var rounds_title := UI.label("Runden:", 26, UI.TEXT)
	rounds_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rounds_row.add_child(rounds_title)
	_rounds_option = OptionButton.new()
	_rounds_option.add_theme_font_size_override("font_size", 26)
	_rounds_option.custom_minimum_size = Vector2(320, 70)
	_rounds_option.focus_mode = Control.FOCUS_NONE
	_rounds_option.add_item("5 Runden", 0)
	_rounds_option.add_item("10 Runden", 1)
	_rounds_option.add_item("20 Runden", 2)
	_rounds_option.add_item("Unbegrenzt (bis 5 Punkte)", 3)
	_rounds_option.select(3)
	rounds_row.add_child(_rounds_option)

	_create_button = UI.button("🆕 Raum erstellen", 30)
	_create_button.pressed.connect(_on_create_pressed)
	box.add_child(_create_button)

	var sep := HSeparator.new()
	box.add_child(sep)

	var join_label := UI.label("Oder Raum beitreten:", 24, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	box.add_child(join_label)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	box.add_child(row)
	_code_input = UI.line_edit("4-stelliger Code", false, 26)
	_code_input.virtual_keyboard_type = LineEdit.KEYBOARD_TYPE_PHONE
	_code_input.max_length = 4
	_code_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_code_input)
	_join_button = UI.button_secondary("Beitreten", 26)
	_join_button.custom_minimum_size = Vector2(200, 76)
	_join_button.pressed.connect(_on_join_pressed)
	row.add_child(_join_button)

	_status = UI.label("", 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.custom_minimum_size = Vector2(0, 56)
	box.add_child(_status)

	var logout := UI.button_danger("Abmelden", 22)
	logout.pressed.connect(_on_logout_pressed)
	outer.add_child(logout)

func _load_stats() -> void:
	Global.http(HTTPClient.METHOD_GET, "/api/users/me/stats", null, _on_stats_result)

func _on_stats_result(_result: int, code: int, text: String) -> void:
	if code == 200:
		var data = JSON.parse_string(text)
		if data is Dictionary:
			Global.stats = data
			_stats.text = "Spiele: %d  |  Siege: %d  |  Siegquote: %s%%" % [
				int(data.get("total_games", 0)),
				int(data.get("total_wins", 0)),
				str(data.get("win_rate", 0)),
			]

func _on_players_minus() -> void:
	_player_count = maxi(2, _player_count - 1)
	_players_value.text = str(_player_count)

func _on_players_plus() -> void:
	_player_count = mini(10, _player_count + 1)
	_players_value.text = str(_player_count)

func _on_create_pressed() -> void:
	_rounds_limit = [5, 10, 20, 0][_rounds_option.selected]
	_set_status("Raum wird erstellt...")
	_create_button.disabled = true
	Global.http(HTTPClient.METHOD_POST, "/api/rooms",
		{"max_players": _player_count, "rounds_limit": _rounds_limit},
		_on_create_result)

func _on_create_result(_result: int, code: int, text: String) -> void:
	_create_button.disabled = false
	if code == 200:
		var data = JSON.parse_string(text)
		if data is Dictionary and data.has("code"):
			Global.room = data
			_enter_room(str(data["code"]))
		else:
			_set_status("Unerwartete Server-Antwort.", UI.RED)
	else:
		_set_status(_error_text(code, text), UI.RED)

func _on_join_pressed() -> void:
	var code := _code_input.text.strip_edges()
	if code.length() != 4:
		_set_status("Bitte den 4-stelligen Code eingeben.", UI.RED)
		return
	_set_status("Verbinde mit Raum %s..." % code)
	_join_button.disabled = true
	_joining = true
	Global.connect_ws(code)

func _enter_room(code: String) -> void:
	Global.room_code = code
	Global.connect_ws(code)

func _on_ws_open() -> void:
	if _joining:
		# Beitritt zu einem fremden Raum
		Global.send_ws({"event": "join_room"})
		return
	if not Global.room.is_empty():
		# Host: nach dem Erstellen des Raums erneut anmelden (idempotent)
		Global.send_ws({"event": "join_room"})

func _on_ws_message(msg: Dictionary) -> void:
	var event := str(msg.get("event", ""))
	if event == "room_joined" or event == "room_state":
		if msg.has("room") and msg["room"] is Dictionary:
			Global.room = msg["room"]
			_joining = false
			get_tree().change_scene_to_file("res://scenes/lobby.tscn")
	elif event == "error":
		_joining = false
		_join_button.disabled = false
		Global.close_ws()
		_set_status("❌ " + str(msg.get("message", "Fehler")), UI.RED)

func _on_ws_closed() -> void:
	if _joining:
		_joining = false
		_join_button.disabled = false
		_set_status("❌ Verbindung geschlossen. Raum nicht gefunden?", UI.RED)

func _on_ws_error(message: String) -> void:
	_joining = false
	_join_button.disabled = false
	_set_status("❌ " + message, UI.RED)

func _on_logout_pressed() -> void:
	Global.logout()
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")

func _set_status(text: String, color: Color = UI.MUTED) -> void:
	_status.text = text
	_status.add_theme_color_override("font_color", color)

func _error_text(code: int, text: String) -> String:
	var data = JSON.parse_string(text)
	if data is Dictionary and data.has("detail"):
		return "❌ " + str(data["detail"])
	return "❌ Fehler " + str(code)

# Android-Zurück-Button → abmelden
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		Global.logout()
		get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
