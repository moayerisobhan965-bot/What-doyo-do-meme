extends Control
## Login / Registrierung - die erste Seite der App

var _mode := "login"        # "login" | "register"
var _code_mode := ""        # "" | "verify" | "reset"

var _email: LineEdit
var _username: LineEdit
var _password: LineEdit
var _code: LineEdit
var _new_password: LineEdit
var _status: Label
var _login_tab: Button
var _register_tab: Button
var _action_button: Button
var _username_row: Control
var _code_box: VBoxContainer
var _confirm_code_button: Button
var _forgot_button: Button

var _pending_email := ""
var _pending_password := ""
var _pending_username := ""

var _google: GoogleLogin

func _ready() -> void:
	_build_ui()
	Global.ws_message.connect(_on_ws_message)

func _process(_delta: float) -> void:
	if _google != null:
		_google._poll()

func _exit_tree() -> void:
	if Global.ws_message.is_connected(_on_ws_message):
		Global.ws_message.disconnect(_on_ws_message)

# ───────────────────────── UI-Aufbau ─────────────────────────
func _build_ui() -> void:
	add_child(UI.background())

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", 24)
	outer.custom_minimum_size = Vector2(600, 0)
	center.add_child(outer)

	outer.add_child(UI.title("🎮 What Meme", 64))
	var subtitle := UI.label("Das Multiplayer-Meme-Spiel", 24, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	outer.add_child(subtitle)
	outer.add_child(UI.label("Version " + Global.VERSION, 16, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))

	var panel := UI.panel()
	panel.custom_minimum_size = Vector2(600, 0)
	outer.add_child(panel)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	panel.add_child(box)

	# Tabs Login / Registrieren
	var tabs := HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 12)
	box.add_child(tabs)
	_login_tab = UI.button("Login", 26)
	_login_tab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_login_tab.pressed.connect(_on_login_tab)
	tabs.add_child(_login_tab)
	_register_tab = UI.button_secondary("Registrieren", 26)
	_register_tab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_register_tab.pressed.connect(_on_register_tab)
	tabs.add_child(_register_tab)

	# Eingabefelder
	_email = UI.line_edit("E-Mail", false)
	_email.virtual_keyboard_type = LineEdit.KEYBOARD_TYPE_EMAIL_ADDRESS
	box.add_child(_email)

	_username_row = UI.line_edit("Username", false)
	_username_row.visible = false
	box.add_child(_username_row)
	_username = _username_row

	_password = UI.line_edit("Passwort (min. 8 Zeichen)", true)
	box.add_child(_password)

	# Hauptaktion
	_action_button = UI.button("Einloggen", 30)
	_action_button.pressed.connect(_on_action_pressed)
	box.add_child(_action_button)

	# Google-Login
	var google_sep := HBoxContainer.new()
	google_sep.add_theme_constant_override("separation", 10)
	box.add_child(google_sep)
	var line1 := HSeparator.new()
	line1.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	google_sep.add_child(line1)
	google_sep.add_child(UI.label("oder", 20, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
	var line2 := HSeparator.new()
	line2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	google_sep.add_child(line2)

	var google_button := UI.button("🔵 Mit Google anmelden", 26, Color("4285F4"))
	google_button.pressed.connect(_on_google_pressed)
	box.add_child(google_button)

	# Gast-Modus: ohne Eingaben direkt spielen
	var guest_button := UI.button("🎮 Als Gast spielen (ohne Anmeldung)", 26, UI.PANEL)
	guest_button.pressed.connect(_on_guest_pressed)
	box.add_child(guest_button)

	# Status
	_status = UI.label("", 22, UI.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.custom_minimum_size = Vector2(0, 60)
	box.add_child(_status)

	# Sekundär-Aktionen
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	box.add_child(row)
	_forgot_button = UI.button_secondary("Passwort vergessen", 22)
	_forgot_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_forgot_button.pressed.connect(_on_forgot_pressed)
	row.add_child(_forgot_button)

	# Code-Bereich (versteckt)
	_code_box = VBoxContainer.new()
	_code_box.add_theme_constant_override("separation", 12)
	_code_box.visible = false
	box.add_child(_code_box)
	_code = UI.line_edit("6-stelliger Code aus der E-Mail", false)
	_code.virtual_keyboard_type = LineEdit.KEYBOARD_TYPE_PHONE
	_code_box.add_child(_code)
	_new_password = UI.line_edit("Neues Passwort", true)
	_new_password.visible = false
	_code_box.add_child(_new_password)
	_confirm_code_button = UI.button("Code bestätigen", 26)
	_confirm_code_button.pressed.connect(_on_confirm_code_pressed)
	_code_box.add_child(_confirm_code_button)

	_set_tab("login")

func _set_tab(mode: String) -> void:
	_mode = mode
	var login_style := UI.GREEN if mode == "login" else UI.PANEL
	var register_style := UI.GREEN if mode == "register" else UI.PANEL
	_login_tab.add_theme_stylebox_override("normal", UI._sb(login_style))
	_register_tab.add_theme_stylebox_override("normal", UI._sb(register_style))
	_username_row.visible = mode == "register"
	_password.placeholder_text = "Passwort (min. 8 Zeichen)" if mode == "register" else "Passwort"
	_action_button.text = "Konto erstellen" if mode == "register" else "Einloggen"
	_hide_code_area()
	_set_status("")

func _show_code_area(reset_mode: bool) -> void:
	_code_mode = "reset" if reset_mode else "verify"
	_new_password.visible = reset_mode
	_code_box.visible = true
	_code.text = ""
	_new_password.text = ""

func _hide_code_area() -> void:
	_code_mode = ""
	_code_box.visible = false
	_code.text = ""
	_new_password.text = ""

func _set_status(text: String, color: Color = UI.MUTED) -> void:
	_status.text = text
	_status.add_theme_color_override("font_color", color)

# ───────────────────────── Aktionen ─────────────────────────
func _on_login_tab() -> void:
	_set_tab("login")

func _on_register_tab() -> void:
	_set_tab("register")

func _on_action_pressed() -> void:
	var email := _email.text.strip_edges()
	var password := _password.text
	if email == "" or password == "":
		_set_status("Bitte E-Mail und Passwort ausfüllen.", UI.RED)
		return

	_pending_email = email
	_pending_password = password

	if _mode == "register":
		_pending_username = _username.text.strip_edges()
		if _pending_username == "" or _pending_username.length() < 3:
			_set_status("Username muss mind. 3 Zeichen haben.", UI.RED)
			return
		if password.length() < 8:
			_set_status("Passwort muss mind. 8 Zeichen haben.", UI.RED)
			return
		_set_status("Konto wird erstellt...")
		_action_button.disabled = true
		Global.http(HTTPClient.METHOD_POST, "/api/auth/register",
			{"email": email, "username": _pending_username, "password": password},
			_on_register_result)
	else:
		_set_status("Login läuft...")
		_action_button.disabled = true
		Global.http(HTTPClient.METHOD_POST, "/api/auth/login",
			{"email": email, "password": password},
			_on_login_result)

func _on_google_pressed() -> void:
	_set_status("Öffne Google-Login im Browser...")
	_google = GoogleLogin.new()
	_google.completed.connect(_on_google_completed)
	_google.got_tokens.connect(_on_google_tokens)
	_google.start()

func _on_guest_pressed() -> void:
	_set_status("Gast-Konto wird erstellt...")
	_action_button.disabled = true
	Global.http(HTTPClient.METHOD_POST, "/api/auth/guest", {}, _on_guest_result)

func _on_guest_result(_result: int, code: int, text: String) -> void:
	_action_button.disabled = false
	if code == 200:
		var data = JSON.parse_string(text)
		if data is Dictionary and data.has("access_token"):
			Global.set_auth(str(data["access_token"]), data.get("user", {}))
			_set_status("✅ Willkommen! Du spielst als Gast.", UI.GREEN)
			_go_home()
		else:
			_set_status("Unerwartete Server-Antwort.", UI.RED)
	else:
		_set_status(_error_text(code, text), UI.RED)

func _on_google_completed(success: bool, message: String) -> void:
	if not success:
		_set_status("❌ " + message, UI.RED)
	else:
		_set_status(message, UI.GREEN)

func _on_google_tokens(data: Dictionary) -> void:
	Global.set_auth(str(data.get("access_token", "")), data.get("user", {}))
	_set_status("✅ Erfolgreich eingeloggt!", UI.GREEN)
	_go_home()

func _on_forgot_pressed() -> void:
	var email := _email.text.strip_edges()
	if email == "":
		_set_status("Bitte zuerst deine E-Mail eintippen.", UI.RED)
		return
	_pending_email = email
	_set_status("Reset-Code wird gesendet...")
	Global.http(HTTPClient.METHOD_POST, "/api/auth/forgot-password",
		{"email": email}, _on_forgot_result)

func _on_confirm_code_pressed() -> void:
	var code := _code.text.strip_edges()
	if code.length() < 6:
		_set_status("Bitte den 6-stelligen Code eingeben.", UI.RED)
		return
	if _code_mode == "reset":
		var npw := _new_password.text
		if npw.length() < 8:
			_set_status("Neues Passwort muss mind. 8 Zeichen haben.", UI.RED)
			return
		_set_status("Passwort wird geändert...")
		_confirm_code_button.disabled = true
		Global.http(HTTPClient.METHOD_POST, "/api/auth/reset-password",
			{"token": code, "new_password": npw}, _on_reset_result)
	else:
		_set_status("Code wird geprüft...")
		_confirm_code_button.disabled = true
		Global.http(HTTPClient.METHOD_POST, "/api/auth/verify-email",
			{"token": code}, _on_verify_result)

# ───────────────────────── HTTP-Ergebnisse ─────────────────────────
func _on_register_result(_result: int, code: int, text: String) -> void:
	_action_button.disabled = false
	if code == 200:
		var data = JSON.parse_string(text)
		if data is Dictionary:
			if data.has("dev_code"):
				# Dev-Modus (kein E-Mail-Key): Code direkt anzeigen + vorausfüllen
				_set_status("✅ Konto erstellt! Dev-Code: %s (bereits eingetragen) → Code bestätigen." % str(data["dev_code"]), UI.GREEN)
				_show_code_area(false)
				_code.text = str(data["dev_code"])
			else:
				_set_status("✅ Konto erstellt! Wir haben dir einen Code per E-Mail geschickt. Bitte Code eingeben.", UI.GREEN)
				_show_code_area(false)
		else:
			_set_status("Unerwartete Server-Antwort.", UI.RED)
	else:
		_set_status(_error_text(code, text), UI.RED)

func _on_login_result(_result: int, code: int, text: String) -> void:
	_action_button.disabled = false
	if code == 200:
		var data = JSON.parse_string(text)
		if data is Dictionary and data.has("access_token"):
			Global.set_auth(str(data["access_token"]), data.get("user", {}))
			_set_status("✅ Erfolgreich eingeloggt!", UI.GREEN)
			_go_home()
		else:
			_set_status("Unerwartete Server-Antwort.", UI.RED)
	else:
		var detail := _detail_from(text)
		if code == 400 and "verifiziere" in detail.to_lower():
			_set_status("Deine E-Mail ist noch nicht verifiziert. Bitte Code aus der E-Mail eingeben.", UI.GOLD)
			_show_code_area(false)
		else:
			_set_status(_error_text(code, text), UI.RED)

func _on_verify_result(_result: int, code: int, text: String) -> void:
	_confirm_code_button.disabled = false
	if code == 200:
		_set_status("✅ E-Mail verifiziert! Du wirst eingeloggt...", UI.GREEN)
		_action_button.disabled = true
		Global.http(HTTPClient.METHOD_POST, "/api/auth/login",
			{"email": _pending_email, "password": _pending_password},
			_on_login_result)
	else:
		_set_status(_error_text(code, text), UI.RED)

func _on_forgot_result(_result: int, code: int, text: String) -> void:
	if code == 200:
		var data = JSON.parse_string(text)
		if data is Dictionary and data.has("dev_code"):
			_set_status("📧 Dev-Reset-Code: %s (bereits eingetragen)" % str(data["dev_code"]), UI.GREEN)
			_show_code_area(true)
			_code.text = str(data["dev_code"])
		else:
			_set_status("📧 Reset-Code gesendet! Bitte Code + neues Passwort eingeben.", UI.GREEN)
			_show_code_area(true)
	else:
		_set_status(_error_text(code, text), UI.RED)

func _on_reset_result(_result: int, code: int, text: String) -> void:
	_confirm_code_button.disabled = false
	if code == 200:
		_set_status("✅ Passwort geändert! Du kannst dich jetzt einloggen.", UI.GREEN)
		_hide_code_area()
		_password.text = ""
		_set_tab("login")
	else:
		_set_status(_error_text(code, text), UI.RED)

# ───────────────────────── Helfer ─────────────────────────
func _detail_from(text: String) -> String:
	var data = JSON.parse_string(text)
	if data is Dictionary and data.has("detail"):
		if data["detail"] is String:
			return str(data["detail"])
	return ""

func _error_text(code: int, text: String) -> String:
	var detail := _detail_from(text)
	if detail != "":
		return "❌ " + detail
	match code:
		401:
			return "❌ Falsche E-Mail oder Passwort."
		409:
			return "❌ E-Mail oder Username bereits vergeben."
		0:
			return "❌ Keine Verbindung zum Server. Läuft das Backend?"
		_:
			return "❌ Fehler " + str(code)

func _on_ws_message(_msg: Dictionary) -> void:
	pass  # Login-Seite braucht kein WebSocket

func _go_home() -> void:
	get_tree().change_scene_to_file("res://scenes/home.tscn")

# Android-Zurück-Button → App beenden
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		get_tree().quit()
