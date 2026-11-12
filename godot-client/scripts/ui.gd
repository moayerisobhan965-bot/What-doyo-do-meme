extends Node
## UI-Helfer (Autoload) - konsistentes Styling für alle Szenen

const BG := Color("1a1a2e")
const BG2 := Color("16213e")
const PANEL := Color("0f3460")
const PANEL_LIGHT := Color("194a7a")
const GREEN := Color("4CAF50")
const RED := Color("FF5722")
const GOLD := Color("FFC107")
const TEXT := Color("eaeaea")
const MUTED := Color("aab3c5")

func background() -> ColorRect:
	var r := ColorRect.new()
	r.color = BG
	r.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return r

func label(text: String, size: int = 28, color: Color = TEXT, align: int = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.horizontal_alignment = align
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return l

func title(text: String, size: int = 52) -> Label:
	return label(text, size, TEXT, HORIZONTAL_ALIGNMENT_CENTER)

func button(text: String, size: int = 28, base: Color = GREEN) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", Color("ffffff"))
	b.add_theme_color_override("font_disabled_color", Color("8892a8"))
	b.custom_minimum_size = Vector2(0, 76)
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_stylebox_override("normal", _sb(base))
	b.add_theme_stylebox_override("hover", _sb(base.lightened(0.12)))
	b.add_theme_stylebox_override("pressed", _sb(base.darkened(0.15)))
	b.add_theme_stylebox_override("focus", _sb(base))
	b.add_theme_stylebox_override("disabled", _sb(Color("33415c")))
	return b

func button_secondary(text: String, size: int = 28) -> Button:
	return button(text, size, PANEL)

func button_danger(text: String, size: int = 28) -> Button:
	return button(text, size, RED)

func line_edit(placeholder: String, secret: bool = false, size: int = 26) -> LineEdit:
	var e := LineEdit.new()
	e.placeholder_text = placeholder
	e.secret = secret
	e.add_theme_font_size_override("font_size", size)
	e.add_theme_color_override("font_color", TEXT)
	e.add_theme_color_override("font_placeholder_color", MUTED)
	e.custom_minimum_size = Vector2(0, 64)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("0d1b2a")
	sb.border_color = Color("415a77")
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(10)
	sb.content_margin_left = 16.0
	sb.content_margin_right = 16.0
	sb.content_margin_top = 8.0
	sb.content_margin_bottom = 8.0
	e.add_theme_stylebox_override("normal", sb)
	e.add_theme_stylebox_override("focus", sb)
	return e

func panel() -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = BG2
	sb.border_color = Color("31456b")
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(16)
	sb.content_margin_left = 28.0
	sb.content_margin_right = 28.0
	sb.content_margin_top = 22.0
	sb.content_margin_bottom = 22.0
	p.add_theme_stylebox_override("panel", sb)
	return p

func highlighted_panel() -> PanelContainer:
	var p := panel()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("0d3b1e")
	sb.border_color = GOLD
	sb.set_border_width_all(4)
	sb.set_corner_radius_all(16)
	sb.content_margin_left = 8.0
	sb.content_margin_right = 8.0
	sb.content_margin_top = 8.0
	sb.content_margin_bottom = 8.0
	p.add_theme_stylebox_override("panel", sb)
	return p

func _sb(color: Color) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(12)
	sb.content_margin_left = 20.0
	sb.content_margin_right = 20.0
	sb.content_margin_top = 10.0
	sb.content_margin_bottom = 10.0
	return sb
