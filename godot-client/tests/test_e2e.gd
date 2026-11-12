extends SceneTree
## E2E-Test: 3 Spieler, kompletter Spielfluss gegen ein echtes Backend
## Ausführen:
##   WM_API_BASE=http://localhost:8001 godot --headless -s res://tests/test_e2e.gd

const TIMEOUT_MS := 20000

var g: Node
var ts := str(int(Time.get_unix_time_from_system()))
var emails := ["e2e1%s@test.de" % ts, "e2e2%s@test.de" % ts, "e2e3%s@test.de" % ts]
var names := ["e2ep1%s" % ts, "e2ep2%s" % ts, "e2ep3%s" % ts]
var password := "password123"

var tokens := {}        # name -> token
var ids := {}           # name -> user id (int)
var dev_codes := {}     # name -> verifizierungs-code
var room_code := ""

var ws := {}            # "p2"/"p3" -> WebSocketPeer
var _mail: Dictionary = {"p1": [], "p2": [], "p3": []}

var phase := 0
var _cond: Callable = Callable()
var _next_phase := 0
var _deadline := 0.0
var _http_done := false
var _http_code := 0
var _http_text := ""
var _expect_round := 0
var fails := 0
var passes := 0
var _closed_printed: Dictionary = {}

func _initialize() -> void:
	g = load("res://scripts/global.gd").new()
	root.add_child(g)
	g.ws_message.connect(func(m): _mail["p1"].append(m))
	print("=== WHAT MEME E2E-TEST (3 Spieler) ===")
	print("API: ", g.API_BASE)
	phase = 1

func _wait(cond: Callable, next_p: int) -> void:
	_cond = cond
	_next_phase = next_p
	_deadline = Time.get_ticks_msec() + TIMEOUT_MS
	phase = -1

func _process(_delta: float) -> bool:
	for p in ["p2", "p3"]:
		if ws.has(p):
			var peer: WebSocketPeer = ws[p]
			peer.poll()
			match peer.get_ready_state():
				WebSocketPeer.STATE_OPEN:
					while peer.get_available_packet_count() > 0:
						var msg = JSON.parse_string(peer.get_packet().get_string_from_utf8())
						if msg is Dictionary:
							_mail[p].append(msg)
				WebSocketPeer.STATE_CLOSED:
					if not _closed_printed.has(p):
						_closed_printed[p] = true
						print("  ⚠️ %s WS CLOSED code=%d reason=%s" % [p, peer.get_close_code(), peer.get_close_reason()])

	if phase == -1:
		if _cond.is_valid() and _cond.call():
			phase = _next_phase
			_cond = Callable()
		elif Time.get_ticks_msec() > _deadline:
			_fail("Timeout in Phase %d" % _next_phase)
			return true
	else:
		match phase:
			1: _send_register(0, 2)
			2: _check_register(0) ; _send_verify(0, 3)
			3: _check_verify(0) ; _send_login(0, 4)
			4: _check_login(0) ; _send_register(1, 5)
			5: _check_register(1) ; _send_verify(1, 6)
			6: _check_verify(1) ; _send_login(1, 7)
			7: _check_login(1) ; _send_register(2, 8)
			8: _check_register(2) ; _send_verify(2, 9)
			9: _check_verify(2) ; _send_login(2, 10)
			10: _check_login(2) ; _create_room()
			11: _open_ws()
			12: _join_room()
			13: _start_game()
			14: _submit_memes()
			15: _vote()
			16: _after_round()
			17: _final_checks()
			18: _done()
	return false

# ─────────────── HTTP-Helfer ───────────────
func _http(method: int, path: String, body: Variant) -> void:
	_http_done = false
	g.http(method, path, body, func(_r, c, t):
		_http_code = c
		_http_text = t
		_http_done = true
	)

func _check_http(expected: int, what: String) -> bool:
	if not _http_done or _http_code != expected:
		_fail("%s: HTTP %d erwartet, bekam %d (%s)" % [what, expected, _http_code, _http_text.left(150)])
		return false
	passes += 1
	print("  ✅ %s" % what)
	return true

# ─────────────── Auth ───────────────
func _send_register(idx: int, next_p: int) -> void:
	print("Registriere %s..." % names[idx])
	_http(HTTPClient.METHOD_POST, "/api/auth/register",
		{"email": emails[idx], "username": names[idx], "password": password})
	_wait(func(): return _http_done, next_p)

func _check_register(idx: int) -> void:
	if not _check_http(200, "%s registriert" % names[idx]):
		return
	var data = JSON.parse_string(_http_text)
	if data is Dictionary and data.has("dev_code"):
		dev_codes[names[idx]] = str(data["dev_code"])
	else:
		_fail("Kein dev_code - Backend mit DEV_CODE_RETURN=1 starten")
		return

func _send_verify(idx: int, next_p: int) -> void:
	_http(HTTPClient.METHOD_POST, "/api/auth/verify-email", {"token": dev_codes[names[idx]]})
	_wait(func(): return _http_done, next_p)

func _check_verify(idx: int) -> void:
	_check_http(200, "%s E-Mail verifiziert" % names[idx])

func _send_login(idx: int, next_p: int) -> void:
	_http(HTTPClient.METHOD_POST, "/api/auth/login",
		{"email": emails[idx], "password": password})
	_wait(func(): return _http_done, next_p)

func _check_login(idx: int) -> void:
	if not _check_http(200, "%s eingeloggt" % names[idx]):
		return
	var data = JSON.parse_string(_http_text)
	if data is Dictionary and data.has("access_token"):
		tokens[names[idx]] = str(data["access_token"])
		ids[names[idx]] = int(data["user"]["id"])
	else:
		_fail("Login-Antwort ohne access_token")
		return

# ─────────────── Spiel ───────────────
func _create_room() -> void:
	print("Raum erstellen (Host: %s, 2 Runden-Limit)..." % names[0])
	g.set_auth(str(tokens[names[0]]), {"id": ids[names[0]]})
	_http(HTTPClient.METHOD_POST, "/api/rooms", {"max_players": 3, "rounds_limit": 2})
	_wait(func(): return _http_done, 11)

func _open_ws() -> void:
	if not _check_http(200, "Raum erstellt"):
		return
	var data = JSON.parse_string(_http_text)
	if not (data is Dictionary) or not data.has("code"):
		_fail("Raum-Antwort ohne Code")
		return
	room_code = str(data["code"])
	print("  Raumcode: %s" % room_code)

	g.connect_ws(room_code)
	var peer2 := WebSocketPeer.new()
	ws["p2"] = peer2
	peer2.connect_to_url("%s/ws/%s/%s?token=%s" % [g.WS_BASE, room_code, str(ids[names[1]]), tokens[names[1]].uri_encode()])
	var peer3 := WebSocketPeer.new()
	ws["p3"] = peer3
	peer3.connect_to_url("%s/ws/%s/%s?token=%s" % [g.WS_BASE, room_code, str(ids[names[2]]), tokens[names[2]].uri_encode()])
	_wait(_all_ws_open, 12)

func _join_room() -> void:
	passes += 1
	print("  ✅ Alle 3 verbunden - Raum beitreten")
	g.send_ws({"event": "join_room"})
	for p in ["p2", "p3"]:
		ws[p].send_text(JSON.stringify({"event": "join_room"}))
	_wait(_all_have_room, 13)

func _start_game() -> void:
	passes += 1
	print("  ✅ Alle im Raum - Spiel starten")
	g.send_ws({"event": "start_game"})
	_expect_round = 1
	_wait(_all_have_round_started, 14)

func _submit_memes() -> void:
	passes += 1
	print("  ✅ Runde %d gestartet - Memes einsenden" % _expect_round)
	for n in names:
		var rm := _msg_by_name(n, "round_started", _expect_round)
		if rm.is_empty():
			_fail("Kein round_started für %s" % n)
			return
		if str(rm.get("judge_id", "")) == str(ids[n]):
			continue
		var memes: Array = rm.get("memes", [])
		if memes.is_empty():
			_fail("Keine Memes in round_started")
			return
		var mid := int(memes[0].get("id", 0))
		if n == names[0]:
			g.send_ws({"event": "submit_meme", "meme_id": mid})
		else:
			ws[_key(n)].send_text(JSON.stringify({"event": "submit_meme", "meme_id": mid}))
	_wait(_all_have_voting_started, 15)

func _vote() -> void:
	passes += 1
	print("  ✅ Alle haben eingesendet - Abstimmen")
	for n in names:
		var vm := _msg_by_name(n, "voting_started", _expect_round)
		if vm.is_empty():
			_fail("Kein voting_started für %s" % n)
			return
		var subs: Array = vm.get("submissions", [])
		var my_id := str(ids[n])
		var i_am_submitter := false
		for s in subs:
			if str(s.get("player_id", "")) == my_id:
				i_am_submitter = true
		var target := ""
		if i_am_submitter:
			for s in subs:
				if str(s.get("player_id", "")) != my_id:
					target = str(s.get("player_id", ""))
					break
		elif subs.size() > 0:
			target = str(subs[0].get("player_id", ""))
		if target == "":
			_fail("Kein gültiges Abstimmungsziel für %s. vm=%s subs=%s my_id=%s" % [n, str(vm), str(subs), my_id])
			return
		if n == names[0]:
			g.send_ws({"event": "vote", "target_player_id": target})
		else:
			ws[_key(n)].send_text(JSON.stringify({"event": "vote", "target_player_id": target}))
	_wait(_all_have_round_result, 16)

func _after_round() -> void:
	passes += 1
	var rr := _msg_by_name(names[0], "round_result", _expect_round)
	print("  ✅ Runde %d beendet - Gewinner: %s" % [_expect_round, str(rr.get("winner_name", "?"))])

	var scores: Dictionary = rr.get("scores", {})
	var room: Dictionary = rr.get("room", {})
	var rounds_limit := int(room.get("rounds_limit", 0))
	var round_no := int(room.get("current_round", 0))
	var over := false
	if rounds_limit > 0 and round_no >= rounds_limit:
		over = true  # Runden-Limit erreicht
	elif rounds_limit == 0:
		for s in scores.values():
			if int(s) >= 2:
				over = true
	if over:
		_wait(_all_have_game_over, 17)
	else:
		g.send_ws({"event": "next_round"})
		_expect_round += 1
		_wait(_all_have_round_started, 14)

func _final_checks() -> void:
	passes += 1
	var go := _msg_by_name(names[0], "game_over", 0)
	var winner_id := str(go.get("winner_id", ""))
	var scores: Dictionary = go.get("scores", {})
	var room: Dictionary = go.get("room", {})
	print("  ✅ Spiel vorbei! Gewinner: %s" % str(go.get("winner_name", "?")))
	if winner_id.is_empty() or not scores.has(winner_id):
		_fail("game_over ohne gültigen Gewinner")
		return
	# Gewinner muss die höchste Punktzahl haben
	var max_score := 0
	for s in scores.values():
		max_score = maxi(max_score, int(s))
	if int(scores[winner_id]) != max_score:
		_fail("Gewinner hat nicht die höchste Punktzahl: %s" % str(scores))
		return
	passes += 1
	print("  ✅ Gewinner hat die höchste Punktzahl (%d)" % int(scores[winner_id]))
	if int(room.get("current_round", 0)) != 2:
		_fail("Spiel endete nicht nach 2 Runden: %s" % str(room.get("current_round", 0)))
		return
	passes += 1
	print("  ✅ Runden-Limit (2) korrekt eingehalten")

	var url := "/meme-images/1.png"
	g.fetch_texture(url, func(tex):
		if tex != null:
			passes += 1
			print("  ✅ Meme-Bild vom Server geladen")
		else:
			fails += 1
			print("❌ Meme-Bild konnte nicht geladen werden")
	)
	_wait(func(): return g.texture_cache.has(g.API_BASE + url) or g.texture_failed.has(g.API_BASE + url), 18)

func _done() -> void:
	g.send_ws({"event": "leave_room"})
	g.close_ws()
	for p in ["p2", "p3"]:
		if ws.has(p):
			ws[p].close()
	print("")
	print("=== ERGEBNIS: %d bestanden, %d fehlgeschlagen ===" % [passes, fails])
	if fails > 0:
		print("❌ TEST FEHLGESCHLAGEN")
		quit(1)
	else:
		print("🎉 ALLE TESTS BESTANDEN")
		quit(0)

func _fail(message: String) -> void:
	fails += 1
	print("❌ FEHLER: " + message)
	_done()

# ─────────────── Bedingungen ───────────────
func _key(player_name: String) -> String:
	return "p1" if player_name == names[0] else ("p2" if player_name == names[1] else "p3")

func _msg_by_name(player_name: String, event: String, round: int) -> Dictionary:
	return _msg(_key(player_name), event, round)

func _msg(p: String, event: String, round: int) -> Dictionary:
	for m in _mail[p]:
		if str(m.get("event", "")) != event:
			continue
		if round > 0:
			var r := int(m.get("round", 0))
			if r == 0:
				var room: Dictionary = m.get("room", {})
				r = int(room.get("current_round", 0))
			if r != round:
				continue
		return m
	return {}

func _all_have(event: String, round: int) -> bool:
	for p in ["p1", "p2", "p3"]:
		if _msg(p, event, round).is_empty():
			return false
	return true

func _all_ws_open() -> bool:
	if not g.is_ws_open():
		return false
	for p in ["p2", "p3"]:
		if not ws.has(p) or ws[p].get_ready_state() != WebSocketPeer.STATE_OPEN:
			return false
	return true

func _all_have_room() -> bool:
	for p in ["p1", "p2", "p3"]:
		var found := false
		for m in _mail[p]:
			if m.has("room"):
				found = true
		if not found:
			return false
	return true

func _all_have_round_started() -> bool:
	return _all_have("round_started", _expect_round)

func _all_have_voting_started() -> bool:
	return _all_have("voting_started", _expect_round)

func _all_have_round_result() -> bool:
	return _all_have("round_result", _expect_round)

func _all_have_game_over() -> bool:
	return _all_have("game_over", 0)
