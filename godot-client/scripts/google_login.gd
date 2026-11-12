class_name GoogleLogin
extends RefCounted
## Google-Login: lokaler Server fängt den Browser-Redirect ab
## Ablauf:
## 1. start()            → URL + State vom Backend holen
## 2. Browser öffnet     → Google-Login
## 3. Redirect           → Browser ruft http://127.0.0.1:{port}/?code=...&state=... auf
## 4. Lokaler Server     → fängt Code ab, zeigt Erfolgsseite
## 5. Callback           → Code ans Backend, JWT-Tokens zurück → completed(true)

signal completed(success: bool, message: String)
signal got_tokens(data: Dictionary)

const DEFAULT_PORT := 8123

var _server: TCPServer
var _peer: StreamPeerTCP
var _pending_data := ""
var _state := ""
var _port := DEFAULT_PORT
var _open_browser := true
var _finished := false

## Startet den Google-Login. open_browser=false für Tests.
func start(port: int = DEFAULT_PORT, open_browser: bool = true) -> void:
	_port = port
	_open_browser = open_browser
	_finished = false
	_global().http(HTTPClient.METHOD_GET, "/api/auth/google/url?port=%d" % port, null, _on_url)

## Autoload "Global" zur Laufzeit holen (vermeidet Compile-Order-Probleme)
func _global() -> Node:
	var main: SceneTree = Engine.get_main_loop()
	if main and main.root:
		return main.root.get_node_or_null("Global")
	return null

func is_finished() -> bool:
	return _finished

func _on_url(result: int, code: int, text: String) -> void:
	if code != 200:
		_finished = true
		completed.emit(false, "Google-Login konnte nicht gestartet werden")
		return
	var data = JSON.parse_string(text)
	if not (data is Dictionary) or not data.has("url"):
		_finished = true
		completed.emit(false, "Ungültige Server-Antwort")
		return

	_state = str(data.get("state", ""))
	_port = int(data.get("port", DEFAULT_PORT))

	_server = TCPServer.new()
	var err := _server.listen(_port, "127.0.0.1")
	if err != OK:
		_finished = true
		completed.emit(false, "Lokaler Server konnte nicht gestartet werden")
		return

	if _open_browser:
		OS.shell_open(str(data["url"]))

## Jeden Frame vom Aufrufer aufrufen!
func _poll() -> void:
	if _finished:
		return
	if _server == null or not _server.is_listening():
		return
	if _peer == null and _server.is_connection_available():
		_peer = _server.take_connection()
		_pending_data = ""
	if _peer == null:
		return
	_peer.poll()
	while _peer.get_available_bytes() > 0:
		_pending_data += _peer.get_utf8_string(_peer.get_available_bytes())
		if _pending_data.length() > 16384:
			_pending_data = ""
			break
	if _pending_data.contains("\r\n\r\n") or _pending_data.contains("\n\n"):
		_handle_request(_pending_data)
		_pending_data = ""
		_peer = null
		_server.stop()
		_server = null

func _handle_request(raw: String) -> void:
	var first_line: String = str(raw.split("\n")[0].strip_edges())
	# Format: GET /?code=XXX&state=YYY HTTP/1.1
	var parts := first_line.split(" ")
	var path := ""
	if parts.size() >= 2:
		path = parts[1]

	var query := ""
	var qpos := path.find("?")
	if qpos >= 0:
		query = path.substr(qpos + 1)
		path = path.substr(0, qpos)

	var params := {}
	for pair in query.split("&"):
		var eq := pair.find("=")
		if eq > 0:
			params[pair.substr(0, eq)] = pair.substr(eq + 1).uri_decode()

	if params.has("error"):
		_respond_html(false, "Login abgebrochen")
		_finished = true
		completed.emit(false, "Google-Login abgebrochen")
		return

	if params.get("state", "") != _state:
		_respond_html(false, "Ungültiger Login-Versuch")
		_finished = true
		completed.emit(false, "Ungültiger Login-Versuch")
		return

	var code: String = str(params.get("code", ""))
	if code == "":
		_respond_html(false, "Kein Code erhalten")
		_finished = true
		completed.emit(false, "Kein Code erhalten")
		return

	_respond_html(true, "Erfolgreich! Du kannst zur App zurückkehren.")
	var g := _global()
	if g:
		g.http(HTTPClient.METHOD_POST, "/api/auth/google/callback",
			{"code": code, "state": _state, "port": _port}, _on_callback)
	else:
		_finished = true
		completed.emit(false, "Interner Fehler (Global nicht gefunden)")

func _on_callback(result: int, code: int, text: String) -> void:
	_finished = true
	if code != 200:
		var detail := ""
		var data = JSON.parse_string(text)
		if data is Dictionary and data.has("detail"):
			detail = str(data["detail"])
		completed.emit(false, detail if detail != "" else "Google-Login fehlgeschlagen")
		return
	var data = JSON.parse_string(text)
	if data is Dictionary and data.has("access_token"):
		got_tokens.emit(data)
		completed.emit(true, "Erfolgreich eingeloggt!")
	else:
		completed.emit(false, "Ungültige Server-Antwort")

func _respond_html(success: bool, message: String) -> void:
	if _peer == null:
		return
	var color := "#4CAF50" if success else "#FF5722"
	var html := """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>What Meme Login</title></head>
<body style="font-family:sans-serif;background:#1a1a2e;color:#eee;text-align:center;padding-top:80px">
<h1 style="color:%s">%s</h1><p style="font-size:18px">Du kannst dieses Fenster jetzt schließen.</p>
</body></html>""" % [color, message]
	var response := "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s" % [html.to_utf8_buffer().size(), html]
	_peer.put_data(response.to_utf8_buffer())
