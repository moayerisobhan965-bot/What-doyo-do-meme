extends Control

# API Configuration
const API_URL = "http://localhost:8000/api"
const WS_URL = "ws://localhost:8000/ws"

# API Client
var http_client: HTTPRequest
var socket_client: WebSocketClient

# State
var room_code: String = ""
var player_id: String = ""
var is_host: bool = false
var players: Array = []

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
	$StartButton.pressed.connect(_on_start_pressed)
	$LeaveButton.pressed.connect(_on_leave_pressed)

	# Create room
	_create_room()

func _create_room():
	var request_body = {
		"max_players": 10
	}

	var error = http_client.request(
		API_URL + "/rooms",
		JSON.stringify(request_body),
		["Content-Type: application/json", "Authorization: Bearer " + Global.token],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Erstellen des Raumes!")

func _on_start_pressed():
	var request_body = {}

	var error = http_client.request(
		API_URL + "/rooms/" + room_code + "/start",
		JSON.stringify(request_body),
		["Content-Type: application/json", "Authorization: Bearer " + Global.token],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Starten des Spiels!")

func _on_leave_pressed():
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")

func _on_http_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
	if response_code == 200:
		var response = JSON.new()
		response.parse(body.get_string_from_utf8())

		if response.error == OK:
			var data = response.data
			room_code = data["code"]
			is_host = data["host_id"] == Global.user_id
			player_id = Global.user_id

			$RoomCodeLabel.text = "Raum: " + room_code
			$PlayerList.clear()

			if is_host:
				$StartButton.visible = true

			# Connect WebSocket
			connect_websocket()
	else:
		var error_text = body.get_string_from_utf8()
		show_error("Fehler: " + str(response_code) + " - " + error_text)

func _on_data_received(data):
	var message = JSON.new()
	message.parse(data)

	if message.error == OK:
		var event = message.data.get("event")
		var room = message.data.get("room")

		match event:
			"room_joined":
				players = room["players"]
				update_player_list()
			"player_left":
				var player_id = message.data.get("player_id")
				players = [p for p in players if p["id"] != player_id]
				update_player_list()

func update_player_list():
	$PlayerList.clear()
	for player in players:
		var player_name = player["name"]
		var is_host_str = " (Host)" if player["is_host"] else ""
		$PlayerList.add_item(player_name + is_host_str)

func connect_websocket():
	var query = PackedStringArray()
	query.append("player_id=" + player_id)
	if Global.token:
		query.append("token=" + Global.token)

	socket_client.connect_to_url(WS_URL + "/" + room_code + "/" + player_id, query)

func show_error(text: String):
	$ErrorLabel.text = text
	$ErrorLabel.add_theme_font_override("font_size", 20)
	$ErrorLabel.modulate = Color.RED

func _input(event):
	if event.is_action_pressed("ui_cancel"):
		get_tree().quit()
