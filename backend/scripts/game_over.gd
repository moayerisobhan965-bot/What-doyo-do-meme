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
var winner_id: String = ""
var scores: Dictionary = {}

func _ready():
	# Create HTTP Client
	http_client = HTTPRequest.new()
	add_child(http_client)
	http_client.request_completed.connect(_on_http_request_completed)

	# Get data from Global
	room_code = Global.room_code
	player_id = Global.user_id
	winner_id = Global.winner_id
	scores = Global.scores

	# Update UI
	$WinnerLabel.text = "Gewinner: " + Global.winner_name

	# Create scores list
	$ScoresList.clear()
	for player_id in scores:
		var player_name = Global.players[player_id]["name"]
		var score = scores[player_id]
		$ScoresList.add_item(player_name + ": " + str(score))

	# Connect UI signals
	$LeaveButton.pressed.connect(_on_leave_pressed)

	# Connect WebSocket
	connect_websocket()

func _on_leave_pressed():
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")

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
