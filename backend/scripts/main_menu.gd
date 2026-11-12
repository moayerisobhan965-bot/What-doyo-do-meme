extends Control

# API Configuration
const API_URL = "http://localhost:8000/api"
const WS_URL = "ws://localhost:8000/ws"

# API Client
var http_client: HTTPRequest
var socket_client: WebSocketClient

# State
var current_token: String = ""
var current_username: String = ""
var is_registered: bool = false

func _ready():
	# Create HTTP Client
	http_client = HTTPRequest.new()
	add_child(http_client)
	http_client.request_completed.connect(_on_http_request_completed)

	# Create WebSocket Client
	socket_client = WebSocketClient.new()
	add_child(socket_client)
	socket_client.data_received.connect(_on_data_received)

	# Connect UI signals
	$LoginForm/RegisterButton.pressed.connect(_on_register_pressed)
	$LoginForm/LoginButton.pressed.connect(_on_login_pressed)
	$LoginForm/VerifyButton.pressed.connect(_on_verify_pressed)
	$LoginForm/ForgotPasswordButton.pressed.connect(_on_forgot_password_pressed)

func _on_register_pressed():
	var email = $LoginForm/EmailInput.text
	var username = $LoginForm/UsernameInput.text
	var password = $LoginForm/PasswordInput.text

	if email.is_empty() or username.is_empty() or password.is_empty():
		show_error("Bitte alle Felder ausfüllen!")
		return

	var request_body = {
		"email": email,
		"username": username,
		"password": password
	}

	var error = http_client.request(
		API_URL + "/auth/register",
		JSON.stringify(request_body),
		["Content-Type: application/json"],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Senden der Anfrage!")

func _on_login_pressed():
	var email = $LoginForm/EmailInput.text
	var password = $LoginForm/PasswordInput.text

	if email.is_empty() or password.is_empty():
		show_error("Bitte E-Mail und Passwort eingeben!")
		return

	var request_body = {
		"email": email,
		"password": password
	}

	var error = http_client.request(
		API_URL + "/auth/login",
		JSON.stringify(request_body),
		["Content-Type: application/json"],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Senden der Anfrage!")

func _on_verify_pressed():
	var token = $LoginForm/VerifyCodeInput.text

	if token.is_empty():
		show_error("Bitte Code eingeben!")
		return

	var request_body = {
		"token": token
	}

	var error = http_client.request(
		API_URL + "/auth/verify-email",
		JSON.stringify(request_body),
		["Content-Type: application/json"],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Senden der Anfrage!")

func _on_forgot_password_pressed():
	var email = $LoginForm/EmailInput.text

	if email.is_empty():
		show_error("Bitte E-Mail eingeben!")
		return

	var request_body = {
		"email": email
	}

	var error = http_client.request(
		API_URL + "/auth/forgot-password",
		JSON.stringify(request_body),
		["Content-Type: application/json"],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Senden der Anfrage!")

func _on_http_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
	if response_code == 200:
		var response = JSON.new()
		response.parse(body.get_string_from_utf8())

		if response.error == OK:
			var data = response.data

			if "access_token" in data:
				current_token = data["access_token"]
				current_username = data["user"]["username"]

				if data["user"]["is_verified"]:
					# Login erfolgreich
					show_message("Login erfolgreich!")
					# ToDo: Lobby Scene laden
				else:
					# E-Mail verifizieren
					$LoginForm/VerifyCodeInput.visible = true
					$LoginForm/VerifyButton.visible = true
					show_message("E-Mail verifizieren! Bitte Code eingeben.")
			elif "message" in data:
				show_message(data["message"])
	else:
		var error_text = body.get_string_from_utf8()
		show_error("Fehler: " + str(response_code) + " - " + error_text)

func _on_data_received(data):
	var message = JSON.new()
	message.parse(data)

	if message.error == OK:
		var event = message.data.get("event")

		match event:
			"room_created":
				show_message("Raum erstellt!")
			"room_joined":
				show_message("Raum beigetreten!")
			"game_started":
				show_message("Spiel gestartet!")
				get_tree().change_scene_to_file("res://scenes/game.tscn")

func show_message(text: String):
	$LoginForm/ErrorLabel.text = text
	$LoginForm/ErrorLabel.add_theme_font_override("font_size", 24)
	$LoginForm/ErrorLabel.modulate = Color.GREEN

func show_error(text: String):
	$LoginForm/ErrorLabel.text = text
	$LoginForm/ErrorLabel.add_theme_font_override("font_size", 20)
	$LoginForm/ErrorLabel.modulate = Color.RED

func _input(event):
	if event.is_action_pressed("ui_cancel"):
		get_tree().quit()
