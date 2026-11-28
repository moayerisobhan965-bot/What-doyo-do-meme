extends Control
## Spiel - Runden mit Caption, Meme-Auswahl, Voting und Ergebnissen

var _round_label: Label
var _caption_label: Label
var _score_label: Label
var _scoreboard: VBoxContainer
var _scoreboard_flow: FlowContainer
var _body: Control          # aktueller Body (wird ersetzt)
var _status: Label
var _back_panel: Control    # bei Verbindungsverlust

var _built_signature := ""
var _selected_meme_id := -1
var _meme_buttons: Dictionary = {}   # meme_id -> Button

func _ready() -> void:
	_build_ui()
	Global.ws_message.connect(_on_ws_message)
	Global.ws_open.connect(_on_ws_open)
	Global.ws_closed.connect(_on_ws_closed)
	Global.ws_error.connect(_on_ws_error)
	_render()

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

	# Obere Leiste: Runde | Meine Punkte
	var top := PanelContainer.new()
	var top_sb := StyleBoxFlat.new()
	top_sb.bg_color = UI.PANEL
	top.add_theme_stylebox_override("panel", top_sb)
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.custom_minimum_size = Vector2(0, 60)
	add_child(top)

	var top_row := HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 18)
	top.add_child(top_row)

	_round_label = UI.label("Runde 1", 24, UI.GOLD, HORIZONTAL_ALIGNMENT_LEFT)
	_round_label.custom_minimum_size = Vector2(220, 0)
	top_row.add_child(_round_label)

	_score_label = UI.label("Punkte: 0", 24, UI.GREEN, HORIZONTAL_ALIGNMENT_RIGHT)
	_score_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_row.add_child(_score_label)

	# Caption-Zeile
	var caption_panel := PanelContainer.new()
	var cap_sb := StyleBoxFlat.new()
	cap_sb.bg_color = Color("16213e")
	cap_sb.content_margin_left = 14.0
	cap_sb.content_margin_right = 14.0
	cap_sb.content_margin_top = 6.0
	cap_sb.content_margin_bottom = 6.0
	caption_panel.add_theme_stylebox_override("panel", cap_sb)
	caption_panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	caption_panel.offset_top = 64
	caption_panel.offset_bottom = 64 + 78
	add_child(caption_panel)
	_caption_label = UI.label("", 22, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER)
	_caption_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_caption_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_caption_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	caption_panel.add_child(_caption_label)

	# Scoreboard (Streifen unter der Caption, immer sichtbar)
	var sb_panel := PanelContainer.new()
	var sb_style := StyleBoxFlat.new()
	sb_style.bg_color = Color("0d1b2a")
	sb_style.set_corner_radius_all(10)
	sb_style.content_margin_left = 12.0
	sb_style.content_margin_right = 12.0
	sb_style.content_margin_top = 8.0
	sb_style.content_margin_bottom = 8.0
	sb_panel.add_theme_stylebox_override("panel", sb_style)
	sb_panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	sb_panel.offset_top = 146
	sb_panel.offset_bottom = 250
	add_child(sb_panel)
	_scoreboard = VBoxContainer.new()
	_scoreboard.add_theme_constant_override("separation", 2)
	sb_panel.add_child(_scoreboard)
	var sb_flow := FlowContainer.new()
	sb_flow.add_theme_constant_override("h_separation", 12)
	sb_flow.add_theme_constant_override("v_separation", 2)
	sb_flow.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scoreboard.add_child(sb_flow)
	_scoreboard_flow = sb_flow

	# Body-Bereich
	var body_area := MarginContainer.new()
	body_area.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	body_area.add_theme_constant_override("margin_top", 258)
	body_area.add_theme_constant_override("margin_bottom", 84)
	body_area.add_theme_constant_override("margin_left", 10)
	body_area.add_theme_constant_override("margin_right", 10)
	add_child(body_area)
	_body = Control.new()
	_body.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	body_area.add_child(_body)

	# Statuszeile unten
	_status = UI.label("", 20, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_status.offset_top = -72
	_status.offset_bottom = -8
	_status.custom_minimum_size = Vector2(0, 64)
	add_child(_status)

	# Verbindungsverlust-Panel (versteckt)
	_back_panel = UI.panel()
	_back_panel.set_anchors_preset(Control.PRESET_CENTER)
	_back_panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_back_panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	_back_panel.visible = false
	add_child(_back_panel)
	var back_box := VBoxContainer.new()
	back_box.add_theme_constant_override("separation", 14)
	_back_panel.add_child(back_box)
	back_box.add_child(UI.label("❌ Verbindung verloren", 30, UI.RED, HORIZONTAL_ALIGNMENT_CENTER))
	var back_btn := UI.button("Zurück zur Startseite", 26)
	back_btn.pressed.connect(_on_back_home_pressed)
	back_box.add_child(back_btn)

# ───────────────────────── Events ─────────────────────────
func _on_ws_open() -> void:
	Global.send_ws({"event": "join_room"})

func _on_ws_message(msg: Dictionary) -> void:
	if msg.has("room") and msg["room"] is Dictionary:
		Global.room = msg["room"]
	var event := str(msg.get("event", ""))
	match event:
		"game_over":
			get_tree().change_scene_to_file("res://scenes/game_over.tscn")
			return
		"error":
			_toast(str(msg.get("message", "Fehler")), UI.RED)
	_render()

func _on_ws_closed() -> void:
	_back_panel.visible = true

func _on_ws_error(message: String) -> void:
	_toast(message, UI.RED)

func _on_back_home_pressed() -> void:
	Global.close_ws()
	get_tree().change_scene_to_file("res://scenes/home.tscn")

# ───────────────────────── Rendering ─────────────────────────
func _render() -> void:
	var room := Global.room
	if room.is_empty():
		return
	var state := str(room.get("state", "lobby"))
	if state == "game_over":
		get_tree().change_scene_to_file("res://scenes/game_over.tscn")
		return
	if state == "lobby":
		get_tree().change_scene_to_file("res://scenes/lobby.tscn")
		return

	var round := int(room.get("current_round", 0))
	var rounds_limit := int(room.get("rounds_limit", 0))
	if rounds_limit > 0:
		_round_label.text = "Runde %d/%d" % [round, rounds_limit]
	else:
		_round_label.text = "Runde %d" % round
	_caption_label.text = "🃏 %s" % str(room.get("drawn_caption", ""))

	var my_score := 0
	var scores: Dictionary = room.get("scores", {})
	if scores.has(Global.player_id):
		my_score = int(scores[Global.player_id])
	_score_label.text = "Punkte: %d" % my_score
	_update_scoreboard(room, scores)

	var signature := "%s_%d_%s" % [state, round, str(room.get("submissions", {}).size())]
	if signature == _built_signature:
		return
	_built_signature = signature

	_clear_body()
	match state:
		"playing":
			_show_playing(room)
		"voting":
			_show_voting(room)
		"result":
			_show_result(room)

func _clear_body() -> void:
	for child in _body.get_children():
		child.queue_free()
	_selected_meme_id = -1
	_meme_buttons.clear()

func _update_scoreboard(room: Dictionary, scores: Dictionary) -> void:
	for child in _scoreboard_flow.get_children():
		child.queue_free()
	for p in room.get("players", []):
		var pid := str(p.get("id", ""))
		var s := int(scores.get(pid, 0))
		var nm := str(p.get("name", "?"))
		if pid == Global.player_id:
			nm += " (Du)"
		var lbl := UI.label("%s: %d" % [nm, s], 20, UI.TEXT, HORIZONTAL_ALIGNMENT_LEFT)
		if pid == Global.player_id:
			lbl.add_theme_color_override("font_color", UI.GREEN)
		_scoreboard_flow.add_child(lbl)

func _player_name(pid: String) -> String:
	for p in Global.room.get("players", []):
		if str(p.get("id", "")) == pid:
			return str(p.get("name", "?"))
	return "?"

# ───────────────────────── PLAYING ─────────────────────────
func _show_playing(room: Dictionary) -> void:
	var judge_index := int(room.get("judge_index", 0))
	var players: Array = room.get("players", [])
	var judge: Dictionary = players[judge_index] if judge_index < players.size() else {}
	var am_judge := str(judge.get("id", "")) == Global.player_id

	var submitters: Array = room.get("round_submitters", [])
	var submissions: Dictionary = room.get("submissions", {})
	var total := submitters.size()
	var done := submissions.size()

	if am_judge:
		var v := VBoxContainer.new()
		v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		v.alignment = BoxContainer.ALIGNMENT_CENTER
		v.add_theme_constant_override("separation", 14)
		_body.add_child(v)
		v.add_child(UI.label("👨‍⚖️ Du bist der Richter!", 38, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER))
		v.add_child(UI.label("Warte auf die Einsendungen der anderen Spieler...", 26, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		v.add_child(UI.label("%d / %d abgegeben" % [done, total], 24, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER))
		return

	if not Global.player_id in submitters:
		var v := VBoxContainer.new()
		v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		v.alignment = BoxContainer.ALIGNMENT_CENTER
		v.add_theme_constant_override("separation", 14)
		_body.add_child(v)
		v.add_child(UI.label("👀 Du bist Zuschauer diese Runde", 32, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		v.add_child(UI.label("Nächste Runde bist du dabei!", 24, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		return

	if submissions.has(Global.player_id):
		var v := VBoxContainer.new()
		v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		v.alignment = BoxContainer.ALIGNMENT_CENTER
		v.add_theme_constant_override("separation", 14)
		_body.add_child(v)
		v.add_child(UI.label("✅ Einsendung gesendet!", 34, UI.GREEN, HORIZONTAL_ALIGNMENT_CENTER))
		v.add_child(UI.label("Warte auf die anderen Spieler...", 26, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		v.add_child(UI.label("%d / %d abgegeben" % [done, total], 24, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER))
		return

	# Meme-Auswahl
	var v := VBoxContainer.new()
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.add_theme_constant_override("separation", 10)
	_body.add_child(v)

	v.add_child(UI.label("Wähle das beste Meme zur Caption!", 28, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER))

	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(grid)

	var memes: Array = room.get("round_memes", [])
	for meme in memes:
		var mid := int(meme.get("id", 0))
		var url := str(meme.get("url", ""))
		var mname := str(meme.get("name", ""))
		var cell := UI.button("")
		cell.custom_minimum_size = Vector2(330, 230)
		cell.pressed.connect(_on_meme_selected.bind(mid))
		_meme_buttons[mid] = cell
		grid.add_child(cell)
		var inner := VBoxContainer.new()
		inner.add_theme_constant_override("separation", 2)
		inner.alignment = BoxContainer.ALIGNMENT_CENTER
		cell.add_child(inner)
		var rect := TextureRect.new()
		rect.custom_minimum_size = Vector2(0, 170)
		rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		inner.add_child(rect)
		Global.fetch_texture(url, _set_rect_texture.bind(rect))
		if mname != "":
			inner.add_child(UI.label(mname, 18, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))

	var submit := UI.button("📤 Einreichen", 28)
	submit.disabled = true
	submit.pressed.connect(_on_submit_pressed)
	v.add_child(submit)
	_submit_button = submit

var _submit_button: Button

func _on_meme_selected(meme_id: int) -> void:
	_selected_meme_id = meme_id
	for mid in _meme_buttons:
		var btn: Button = _meme_buttons[mid]
		var sb: StyleBoxFlat = UI._sb(UI.GREEN if mid == meme_id else UI.PANEL)
		if mid == meme_id:
			sb.border_color = UI.GOLD
			sb.set_border_width_all(4)
		btn.add_theme_stylebox_override("normal", sb)
	_submit_button.disabled = false

func _on_submit_pressed() -> void:
	if _selected_meme_id <= 0:
		return
	Global.send_ws({"event": "submit_meme", "meme_id": _selected_meme_id})
	_toast("Einsendung gesendet...")
	_submit_button.disabled = true

# ───────────────────────── VOTING ─────────────────────────
func _show_voting(room: Dictionary) -> void:
	var submissions: Dictionary = room.get("submissions", {})
	var v := VBoxContainer.new()
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.add_theme_constant_override("separation", 10)
	_body.add_child(v)

	v.add_child(UI.label("🗳️ Stimme für das beste Meme!", 30, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER))

	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(grid)

	var ids: Array = submissions.keys()
	ids.sort()
	var votable := 0
	for pid in ids:
		if str(pid) != Global.player_id:
			votable += 1
	if votable == 0:
		# z.B. 2-Spieler-Runde: nur die eigene Einsendung vorhanden →
		# nichts zum Wählen, einfach warten
		var w := VBoxContainer.new()
		w.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		w.alignment = BoxContainer.ALIGNMENT_CENTER
		w.add_theme_constant_override("separation", 14)
		_body.add_child(w)
		w.add_child(UI.label("🗳️ Abstimmung läuft...", 30, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER))
		w.add_child(UI.label("Nur deine Einsendung liegt vor - der Richter entscheidet!", 24, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		return

	for pid in ids:
		var pid_str := str(pid)
		var meme: Dictionary = submissions[pid]
		var url := str(meme.get("url", ""))
		var own := pid_str == Global.player_id

		var cell := UI.button("", 24, UI.PANEL if own else UI.PANEL_LIGHT)
		cell.custom_minimum_size = Vector2(330, 230)
		cell.disabled = own
		if not own:
			cell.pressed.connect(_on_vote_pressed.bind(pid_str))
		grid.add_child(cell)

		var inner := VBoxContainer.new()
		inner.add_theme_constant_override("separation", 2)
		inner.alignment = BoxContainer.ALIGNMENT_CENTER
		cell.add_child(inner)

		var rect := TextureRect.new()
		rect.custom_minimum_size = Vector2(0, 170)
		rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		inner.add_child(rect)
		Global.fetch_texture(url, _set_rect_texture.bind(rect))

		var name_text := _player_name(pid_str)
		if own:
			name_text += " (Du)"
		inner.add_child(UI.label(name_text, 22, UI.MUTED if not own else UI.GREEN, HORIZONTAL_ALIGNMENT_CENTER))

func _on_vote_pressed(target: String) -> void:
	Global.send_ws({"event": "vote", "target_player_id": target})
	_toast("Stimme abgegeben!")
	_built_signature = "voted"  # verhindert Doppel-Klick-Rebuild

# ───────────────────────── RESULT ─────────────────────────
func _show_result(room: Dictionary) -> void:
	var last: Dictionary = room.get("last_result", {})
	if last.is_empty():
		return
	var winner_name := str(last.get("winner_name", "?"))
	var meme_url := str(last.get("meme_url", ""))
	var votes: Dictionary = last.get("votes", {})
	var scores: Dictionary = last.get("scores", {})
	var winner_id := str(last.get("winner_id", ""))
	var winner_votes := int(votes.get(winner_id, 0))

	var win_limit := 5
	var is_final := false
	for s in scores.values():
		if int(s) >= win_limit:
			is_final = true

	var v := VBoxContainer.new()
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 10)
	_body.add_child(v)

	v.add_child(UI.label("🎉 %s gewinnt die Runde!" % winner_name, 36, UI.GOLD, HORIZONTAL_ALIGNMENT_CENTER))

	var rect := TextureRect.new()
	rect.custom_minimum_size = Vector2(0, 220)
	rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	v.add_child(rect)
	Global.fetch_texture(meme_url, _set_rect_texture.bind(rect))

	v.add_child(UI.label("🏆 %d Stimmen" % winner_votes, 24, UI.TEXT, HORIZONTAL_ALIGNMENT_CENTER))

	# Punktestand
	var score_line := ""
	var names := []
	var players: Array = room.get("players", [])
	for p in players:
		var pid := str(p.get("id", ""))
		var s := int(scores.get(pid, 0))
		var nm := str(p.get("name", "?"))
		var mark := " ⭐" if pid == winner_id else ""
		names.append("%s: %d%s" % [nm, s, mark])
	v.add_child(UI.label(",  ".join(names), 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))

	if is_final:
		v.add_child(UI.label("🏁 Finale! Der Sieger wird gekürt...", 28, UI.GREEN, HORIZONTAL_ALIGNMENT_CENTER))
	else:
		v.add_child(UI.label("Nächste Runde startet gleich...", 24, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))

# ───────────────────────── Helfer ─────────────────────────
func _set_rect_texture(rect: TextureRect, tex: ImageTexture) -> void:
	if rect != null and is_instance_valid(rect) and tex != null:
		rect.texture = tex

func _toast(text: String, color: Color = UI.TEXT) -> void:
	_status.text = text
	_status.add_theme_color_override("font_color", color)
	var t := get_tree().create_timer(3.0)
	t.timeout.connect(func() -> void:
		if is_inside_tree():
			_status.text = ""
	)

# Android-Zurück-Button → Raum verlassen
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		Global.send_ws({"event": "leave_room"})
		Global.close_ws()
		get_tree().change_scene_to_file("res://scenes/home.tscn")
