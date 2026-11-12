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
var current_caption: String = ""
var current_meme: String = ""
var memes: Array = []
var selected_meme: int = -1
var current_round: int = 1
var player_score: int = 0
var player_name: String = ""
var is_my_turn: bool = false

func _ready():
	# Create HTTP Client
	http_client = HTTPRequest.new()
	add_child(http_client)
	http_client.request_completed.connect(_on_http_request_completed)

	# Create WebSocket Client
	socket_client = WebSocketClient.new()
	add_child(socket_client)
	socket_client.data_received.connect(_on_data_received)

	# Load memes
	load_memes()

	# Connect UI signals
	for i in range(1, 6):
		var btn = get_node("GameArea/MemesGrid/Meme" + str(i))
		if btn:
			btn.pressed.connect(_on_meme_selected.bind(i))

	$GameArea/SubmitButton.pressed.connect(_on_submit_pressed)

	# Get room code from Global
	room_code = Global.room_code
	player_id = Global.user_id
	player_name = Global.username

	# Connect WebSocket
	connect_websocket()

	# Update UI
	$TopBar/PlayerNameLabel.text = "Spieler: " + player_name
	$TopBar/ScoreLabel.text = "Punkte: " + str(player_score)
	$TopBar/RoundLabel.text = "Runde: " + str(current_round)

func load_memes():
	var error = http_client.request(
		API_URL + "/memes",
		PackedByteArray(),
		["Content-Type: application/json", "Authorization: Bearer " + Global.token],
		HTTPRequest.Method.GET
	)

	if error != OK:
		show_error("Fehler beim Laden der Memes!")

func _on_http_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
	if response_code == 200:
		var response = JSON.new()
		response.parse(body.get_string_from_utf8())

		if response.error == OK:
			memes = response.data
			for i in range(min(memes.size(), 5)):
				var meme = memes[i]
				$GameArea/MemesGrid/Meme%+str(i+1)/TextureRect.texture = load(meme["url"])
	else:
		var error_text = body.get_string_from_utf8()
		show_error("Fehler beim Laden der Memes!")

func connect_websocket():
	var query = PackedStringArray()
	query.append("player_id=" + player_id)
	if Global.token:
		query.append("token=" + Global.token)

	socket_client.connect_to_url(WS_URL + "/" + room_code + "/" + player_id, query)

func _on_data_received(data):
	var message = JSON.new()
	message.parse(data)

	if message.error == OK:
		var event = message.data.get("event")
		var room = message.data.get("room")

		match event:
			"meme_submitted":
				current_caption = room["drawn_caption"]
				$GameArea/CaptionLabel.text = "Computer: '" + current_caption + "'"
				show_message("Computer hat Textkarte gezogen!")
				is_my_turn = true
				$GameArea/SubmitButton.disabled = false
			"turn_changed":
				is_my_turn = message.data.get("current_player")["id"] == player_id
				$GameArea/SubmitButton.disabled = not is_my_turn
				show_message("Deine Runde!")
			"round_result":
				var winner_id = message.data.get("winner_id")
				var winner_name = message.data.get("winner_name")
				var meme_url = message.data.get("meme_url")
				var votes = message.data.get("votes")
				var total_votes = message.data.get("total_votes")

				current_meme = meme_url
				$GameArea/MemeImage.texture = load(current_meme)
				$GameArea/MemePlaceholder.visible = false
				$GameArea/MemeImage.visible = true

				$Title.text = "Runde beendet!"
				$WinnerLabel.text = "Gewinner: " + winner_name
				$VotesLabel.text = "Stimmen: " + str(total_votes)

				# Update scores
				for player in room["players"]:
					if player["id"] == player_id:
						player_score = player["score"]
						$TopBar/ScoreLabel.text = "Punkte: " + str(player_score)

				get_tree().change_scene_to_file("res://scenes/result.tscn")
			"game_over":
				show_message("Spiel vorbei!")
				get_tree().change_scene_to_file("res://scenes/game_over.tscn")

func _on_meme_selected(meme_id: int):
	selected_meme = meme_id

func _on_submit_pressed():
	if selected_meme == -1:
		show_error("Bitte erst ein Meme auswählen!")
		return

	var request_body = {
		"meme_id": selected_meme
	}

	var error = http_client.request(
		API_URL + "/rooms/" + room_code + "/submit",
		JSON.stringify(request_body),
		["Content-Type: application/json", "Authorization: Bearer " + Global.token],
		HTTPRequest.Method.POST
	)

	if error != OK:
		show_error("Fehler beim Einreichen!")

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
