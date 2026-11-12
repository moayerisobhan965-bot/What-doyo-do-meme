extends SceneTree
## Smoke-Test: Alle Szenen instanziieren und auf Laufzeitfehler prüfen
## Ausführen: godot --headless -s res://tests/test_scenes.gd

var fails := 0
var passes := 0

func _initialize() -> void:
	print("=== SZENEN-SMOKE-TEST ===")

	# Login-Seite
	await _check_scene("res://scenes/main_menu.tscn", "Login")
	# Home-Seite (mit Fake-Login)
	var g: Node = root.get_node_or_null("Global")
	if g:
		g.set_auth("fake_token", {"id": 1, "username": "TestUser", "email": "t@t.de", "is_verified": true})
	await _check_scene("res://scenes/home.tscn", "Home")
	# Lobby (mit Fake-Raum)
	if g:
		g.room = {
			"code": "1234", "state": "lobby", "host_id": "1",
			"rounds_limit": 5, "max_players": 10,
			"players": [
				{"id": "1", "name": "TestUser", "is_host": true, "is_ready": true, "score": 0},
				{"id": "2", "name": "Freund", "is_host": false, "is_ready": true, "score": 0},
			],
			"scores": {"1": 0, "2": 0},
		}
		g.room_code = "1234"
	await _check_scene("res://scenes/lobby.tscn", "Lobby")

	# Spiel (Runde läuft - ich bin nicht Richter)
	if g:
		g.player_id = "1"
		g.room = {
			"code": "1234", "state": "playing", "host_id": "1",
			"rounds_limit": 10, "max_players": 10,
			"players": [
				{"id": "1", "name": "TestUser", "is_host": true, "score": 0},
				{"id": "2", "name": "Freund", "is_host": false, "score": 0},
				{"id": "3", "name": "Dritte", "is_host": false, "score": 0},
			],
			"scores": {"1": 0, "2": 0, "3": 0},
			"current_round": 1, "judge_index": 1, "drawn_caption": "Test-Caption",
			"round_memes": [
				{"id": 1, "url": "/meme-images/1.png", "name": "BIG BABA BUM"},
				{"id": 2, "url": "/meme-images/2.png", "name": "DRAKE"},
				{"id": 3, "url": "/meme-images/3.png", "name": "DOGE"},
				{"id": 4, "url": "/meme-images/4.png", "name": "STONKS"},
				{"id": 5, "url": "/meme-images/5.png", "name": "PEPE"},
				{"id": 6, "url": "/meme-images/6.png", "name": "SHREK"},
			],
			"submissions": {}, "votes": {},
			"round_submitters": ["1", "3"], "round_voters": ["1", "2", "3"],
			"last_result": null,
		}
	await _check_scene("res://scenes/game.tscn", "Spiel (playing)")

	# Voting-Ansicht
	if g:
		g.room["state"] = "voting"
		g.room["submissions"] = {
			"1": {"id": 2, "url": "/meme-images/2.png"},
			"3": {"id": 5, "url": "/meme-images/5.png"},
		}
	await _check_scene("res://scenes/game.tscn", "Spiel (voting)")

	# Ergebnis-Ansicht
	if g:
		g.room["state"] = "result"
		g.room["last_result"] = {
			"winner_id": "1", "winner_name": "TestUser",
			"meme_url": "/meme-images/2.png", "votes": {"1": 2},
			"scores": {"1": 1, "2": 0, "3": 0},
		}
	await _check_scene("res://scenes/game.tscn", "Spiel (result)")

	# Spielende
	if g:
		g.room["state"] = "game_over"
		g.room["winner_id"] = "1"
		g.room["scores"] = {"1": 2, "2": 1, "3": 0}
	await _check_scene("res://scenes/game_over.tscn", "Spielende")

	print("")
	print("=== ERGEBNIS: %d bestanden, %d fehlgeschlagen ===" % [passes, fails])
	if fails > 0:
		print("❌ TEST FEHLGESCHLAGEN")
		quit(1)
	else:
		print("🎉 ALLE SZENEN OK")
		quit(0)

func _check_scene(path: String, name: String) -> void:
	var packed: PackedScene = load(path)
	if packed == null:
		fails += 1
		print("❌ %s: Szene konnte nicht geladen werden" % name)
		return
	var inst := packed.instantiate()
	if inst == null:
		fails += 1
		print("❌ %s: Instanziierung fehlgeschlagen" % name)
		return
	root.add_child(inst)
	await process_frame
	await process_frame
	# Prüfen ob die Szene noch lebt (kein sofortiger Crash)
	if is_instance_valid(inst):
		passes += 1
		print("  ✅ %s" % name)
	else:
		fails += 1
		print("❌ %s: Szene nach _ready ungültig" % name)
	inst.queue_free()
	await process_frame
