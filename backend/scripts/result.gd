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
var winner_name: String = ""
var meme_url: String = ""
var votes: Dictionary = {}
var total_votes: int = 0
var player_score: int = 0

func _ready():
	# Create HTTP Client
	http_client = HTTPRequest.new()
	add_child(http_client)
	http_client.request_completed.connect(_on_http_request_completed)

	# Get data from Global
	room_code = Global.room_code
	player_id = Global.user_id
	winner_id = Global.winner_id
	winner_name = Global.winner_name
	meme_url = Global.meme_url
	votes = Global.votes
	total_votes = Global.total_votes
	player_score = Global.player_score

	# Update UI
	$WinnerLabel.text = "Gewinner: " + winner_name
	$MemeImage.texture = load(meme_url)

	var votes_text = ""
	for player_id in votes:
		votes_text += str(player_id) + ": " + str(votes[player_id]) + "\n"

	$VotesLabel.text = "Stimmen:\n" + votes_text

	# Connect UI signals
	$NextButton.pressed.connect(_on_next_pressed)
	$LeaveButton.pressed.connect(_on_leave_pressed)

	# Connect WebSocket
	connect_websocket()

func _on_next_pressed():
	# ToDo: Nächste Runde starten
	show_message("Nächste Runde wird gestartet...")

func _on_leave_pressed():
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")

func connect_websocket():
	var query = PackedStringArray()
	query.append("player_id=" + player_id)
	if Global.token:
		query.append("token=" + Global.token)

	socket_client.connect_to_url(WS_URL + "/" + room_code + "/" + player_id, query)

func show_message(text: String):
	$ErrorLabel.text = text
	$ErrorLabel.add_theme_font_override("font_size", 24)
	$ErrorLabel.modulate = Color.GREEN

func show_error(text: String):
	$ErrorLabel.text = text
	$ErrorLabel.add_theme_font_override("font_size", 20)
	$ErrorLabel.modulate = Color.RED

func _input(event):
	if event.is_action_pressed("ui_cancel"):
		get_tree().quit()
