extends Node
## What Meme - Globaler Zustand, HTTP-Helfer, WebSocket und Bild-Cache (Autoload)

signal ws_message(msg: Dictionary)
signal ws_open
signal ws_closed
signal ws_error(message: String)

# ═══════════════════════════════════════════════════════════════
# SERVER-KONFIGURATION
# - Android Emulator (PC-Server):    http://10.0.2.2:8000
# - Echte Geräte im gleichen WLAN:   http://<LAN-IP-des-PCs>:8000
# - Produktion mit Domain:           https://whatmeme.de
# Kann auch per Umgebungsvariable WM_API_BASE überschrieben werden.
# ═══════════════════════════════════════════════════════════════
const DEFAULT_API_BASE := "http://10.0.2.2:8000"

var API_BASE: String
var WS_BASE: String

# Auth
var token := ""
var user: Dictionary = {}
var stats: Dictionary = {}

# Raum / Spiel
var room: Dictionary = {}
var player_id := ""
var room_code := ""
var last_error := ""

# WebSocket
var _ws: WebSocketPeer
var _ws_connecting := false

# HTTP-Warteschlange (HTTPRequest kann nur 1 Anfrage gleichzeitig)
var _http: HTTPRequest
var _queue: Array[Dictionary] = []
var _current: Dictionary = {}
var _busy := false

# Bild-Warteschlange
var _img_http: HTTPRequest
var _img_queue: Array[Dictionary] = []
var _img_current: Dictionary = {}
var _img_busy := false
var texture_cache: Dictionary = {}   # url -> ImageTexture
var texture_failed: Dictionary = {}  # url -> true

func _ready() -> void:
	var env := OS.get_environment("WM_API_BASE")
	API_BASE = env if env != "" else DEFAULT_API_BASE
	WS_BASE = API_BASE.replace("https://", "wss://").replace("http://", "ws://")

	_http = HTTPRequest.new()
	add_child(_http)
	_http.request_completed.connect(_on_http_done)

	_img_http = HTTPRequest.new()
	add_child(_img_http)
	_img_http.request_completed.connect(_on_img_done)

func is_logged_in() -> bool:
	return not token.is_empty()

func set_auth(tok: String, u: Dictionary) -> void:
	token = tok
	user = u
	player_id = str(int(u.get("id", 0)))

func logout() -> void:
	close_ws()
	token = ""
	user = {}
	stats = {}
	room = {}
	room_code = ""
	last_error = ""

# ─────────────────────────── HTTP ───────────────────────────
func http(method: int, path: String, body: Variant = null, cb: Callable = Callable()) -> void:
	_queue.append({"method": method, "path": path, "body": body, "cb": cb})
	_drain_queue()

func _drain_queue() -> void:
	if _busy or _queue.is_empty():
		return
	_busy = true
	_current = _queue.pop_front()
	var headers := PackedStringArray(["Content-Type: application/json"])
	if not token.is_empty():
		headers.append("Authorization: Bearer " + token)
	var body_str := ""
	if _current["body"] != null:
		body_str = JSON.stringify(_current["body"])
	var err := _http.request(API_BASE + _current["path"], headers, _current["method"], body_str)
	if err != OK:
		_finish_http(err, 0, PackedStringArray(), PackedByteArray())

func _on_http_done(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_finish_http(result, code, _headers, body)

func _finish_http(result: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	_busy = false
	var req: Dictionary = _current
	_current = {}
	var text := body.get_string_from_utf8()
	var cb: Callable = req.get("cb", Callable())
	if cb.is_valid():
		cb.call(result, code, text)
	_drain_queue()

# ─────────────────────────── Bilder ───────────────────────────
func fetch_texture(url: String, cb: Callable = Callable()) -> void:
	if url.begins_with("/"):
		url = API_BASE + url
	if texture_cache.has(url):
		if cb.is_valid():
			cb.call(texture_cache[url])
		return
	if texture_failed.has(url):
		if cb.is_valid():
			cb.call(null)
		return
	_img_queue.append({"url": url, "cb": cb})
	_drain_img_queue()

func _drain_img_queue() -> void:
	if _img_busy or _img_queue.is_empty():
		return
	_img_busy = true
	_img_current = _img_queue.pop_front()
	var err := _img_http.request(_img_current["url"], PackedStringArray(), HTTPClient.METHOD_GET)
	if err != OK:
		_finish_img(0, PackedByteArray())

func _on_img_done(_r: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	_finish_img(code, body)

func _finish_img(code: int, body: PackedByteArray) -> void:
	_img_busy = false
	var req: Dictionary = _img_current
	_img_current = {}
	var url: String = req.get("url", "")
	var cb: Callable = req.get("cb", Callable())
	var tex: ImageTexture = null
	if code == 200 and body.size() > 0:
		var img := Image.new()
		if img.load_png_from_buffer(body) == OK:
			tex = ImageTexture.create_from_image(img)
	if tex != null:
		texture_cache[url] = tex
	else:
		texture_failed[url] = true
	if cb.is_valid():
		cb.call(tex)
	_drain_img_queue()

# ─────────────────────────── WebSocket ───────────────────────────
func connect_ws(code: String) -> void:
	close_ws()
	room_code = code
	_ws = WebSocketPeer.new()
	var url := "%s/ws/%s/%s" % [WS_BASE, code, player_id]
	if not token.is_empty():
		url += "?token=" + token.uri_encode()
	_ws_connecting = true
	var err := _ws.connect_to_url(url)
	if err != OK:
		_ws = null
		_ws_connecting = false
		ws_error.emit("WebSocket-Verbindung fehlgeschlagen")

func send_ws(ev: Dictionary) -> void:
	if _ws != null and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		_ws.send_text(JSON.stringify(ev))

func is_ws_open() -> bool:
	return _ws != null and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN

func close_ws() -> void:
	if _ws != null:
		_ws.close()
		_ws = null
	_ws_connecting = false

func _process(_delta: float) -> void:
	if _ws == null:
		return
	_ws.poll()
	var state := _ws.get_ready_state()
	match state:
		WebSocketPeer.STATE_OPEN:
			if _ws_connecting:
				_ws_connecting = false
				ws_open.emit()
			while _ws.get_available_packet_count() > 0:
				var pkt := _ws.get_packet()
				var text := pkt.get_string_from_utf8()
				var msg = JSON.parse_string(text)
				if msg is Dictionary:
					ws_message.emit(msg)
		WebSocketPeer.STATE_CLOSING:
			pass
		WebSocketPeer.STATE_CLOSED:
			var was_connecting := _ws_connecting
			_ws = null
			_ws_connecting = false
			if was_connecting:
				ws_error.emit("Verbindung zum Server fehlgeschlagen")
			else:
				ws_closed.emit()
