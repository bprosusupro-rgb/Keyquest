extends Control

const INK := Color("#0d1a16")
const TEXT := Color("#edf6fb")
const MUTED := Color("#abc0d2")
const ACCENT := Color("#c4ff6a")
const SURFACE := Color("#172438")
const CONTROL := Color("#24364b")
const OUTLINE := Color("#39506a")

var bridge: Object
var target := OptionButton.new()
var package_field := LineEdit.new()
var steps := TextEdit.new()
var repeat_count := SpinBox.new()
var status: Label
var readiness: Label
var packages := PackedStringArray()
var text_payload := LineEdit.new()
var actions: Array[Button] = []


func _ready() -> void:
	theme = _make_theme()
	var inset := MarginContainer.new()
	add_child(inset)
	inset.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		inset.add_theme_constant_override("margin_" + side, 28)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	inset.add_child(scroll)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 16)
	scroll.add_child(column)

	var title_row := HBoxContainer.new()
	column.add_child(title_row)
	var heading := _label(title_row, "Keyquest", 42, TEXT)
	heading.size_flags_horizontal = SIZE_EXPAND_FILL
	readiness = _label(title_row, "Android service unavailable", 16, MUTED)
	readiness.vertical_alignment = VERTICAL_ALIGNMENT_CENTER

	var launch := _card(column)
	_label(launch, "Game keyboard", 26, TEXT)
	_label(launch, "Choose a 2D game, open the keyboard, then focus the game’s text prompt.", 16, MUTED)
	var target_row := HBoxContainer.new()
	target_row.add_theme_constant_override("separation", 8)
	launch.add_child(target_row)
	target.size_flags_horizontal = SIZE_EXPAND_FILL
	target.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	target.custom_minimum_size.y = 46
	target_row.add_child(target)
	target.item_selected.connect(_choose_target)
	package_field.placeholder_text = "Android package if the game is missing"
	package_field.custom_minimum_size.y = 46
	package_field.size_flags_horizontal = SIZE_EXPAND_FILL
	target_row.add_child(package_field)
	var start := HBoxContainer.new()
	start.add_theme_constant_override("separation", 8)
	launch.add_child(start)
	_button(start, "Open in-game keyboard", _keyboard, true)
	_button(start, "Enable accessibility service", _settings)

	var macro := _card(column)
	_label(macro, "Tap macros", 26, TEXT)
	_label(macro, "One step per line. Enter x%, y%, and the delay after the tap in ms.", 16, MUTED)
	steps.custom_minimum_size.y = 74
	steps.text = "50, 50, 500"
	macro.add_child(steps)
	var fields := HBoxContainer.new()
	fields.add_theme_constant_override("separation", 10)
	macro.add_child(fields)
	var repeats := _label(fields, "Repeats", 16, MUTED)
	repeats.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	repeat_count.min_value = 1
	repeat_count.max_value = 100
	repeat_count.value = 1
	repeat_count.custom_minimum_size = Vector2(112, 44)
	fields.add_child(repeat_count)
	text_payload.placeholder_text = "Optional text to send after the taps"
	text_payload.size_flags_horizontal = SIZE_EXPAND_FILL
	fields.add_child(text_payload)
	var controls := HBoxContainer.new()
	controls.add_theme_constant_override("separation", 8)
	macro.add_child(controls)
	_button(controls, "Find tap point", _pick)
	_button(controls, "Run macro", _run, true)
	_button(controls, "Stop", _stop)
	status = _label(column, "", 16, MUTED)
	status.custom_minimum_size.y = 30
	if not Engine.has_singleton("QuestMacros"):
		status.text = "Run on Android to connect to the accessibility service."
		target.add_item("Choose an installed game")
		for action in actions:
			action.disabled = true
		return
	bridge = Engine.get_singleton("QuestMacros")
	_reload_targets()
	_load_macro()
	var timer := Timer.new()
	timer.wait_time = 0.4
	timer.timeout.connect(_refresh_status)
	add_child(timer)
	timer.start()
	_refresh_status()


func _make_theme() -> Theme:
	var ui := Theme.new()
	ui.default_font_size = 18
	ui.set_color("font_color", "Label", TEXT)
	for kind in ["Button", "OptionButton"]:
		ui.set_stylebox("normal", kind, _style(CONTROL))
		ui.set_stylebox("hover", kind, _style(Color("#33506a"), ACCENT))
		ui.set_stylebox("pressed", kind, _style(Color("#395a71"), ACCENT))
		ui.set_stylebox("disabled", kind, _style(Color("#202e40")))
		ui.set_stylebox("focus", kind, _focus())
		ui.set_color("font_color", kind, TEXT)
	for kind in ["LineEdit", "TextEdit"]:
		ui.set_stylebox("normal", kind, _style(Color("#0f1928"), OUTLINE))
		ui.set_stylebox("focus", kind, _focus())
		ui.set_color("font_color", kind, TEXT)
		ui.set_color("font_placeholder_color", kind, MUTED)
	return ui


func _style(color: Color, border: Color = Color.TRANSPARENT) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = color
	box.set_corner_radius_all(12)
	box.set_border_width_all(1)
	box.border_color = border
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 7
	box.content_margin_bottom = 7
	return box


func _focus() -> StyleBoxFlat:
	var outline := _style(Color.TRANSPARENT, ACCENT)
	outline.set_border_width_all(2)
	return outline


func _card(parent: Container) -> VBoxContainer:
	var panel := PanelContainer.new()
	var surface := _style(SURFACE, OUTLINE)
	surface.content_margin_left = 18
	surface.content_margin_right = 18
	surface.content_margin_top = 14
	surface.content_margin_bottom = 14
	panel.add_theme_stylebox_override("panel", surface)
	parent.add_child(panel)
	var contents := VBoxContainer.new()
	contents.add_theme_constant_override("separation", 8)
	panel.add_child(contents)
	return contents


func _button(parent: Container, caption: String, action: Callable, primary := false) -> void:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size.y = 46
	button.size_flags_horizontal = SIZE_EXPAND_FILL
	if primary:
		button.add_theme_stylebox_override("normal", _style(ACCENT))
		button.add_theme_stylebox_override("hover", _style(Color("#dcffb0"), ACCENT))
		button.add_theme_stylebox_override("pressed", _style(Color("#99dd4a")))
		for state in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
			button.add_theme_color_override(state, INK)
	button.pressed.connect(action)
	parent.add_child(button)
	actions.append(button)


func _label(parent: Container, caption: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = caption
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	return label


func _settings() -> void:
	bridge.openSettings()


func _reload_targets() -> void:
	var items = JSON.parse_string(bridge.listApps())
	packages.clear()
	target.clear()
	target.add_item("Choose an installed game")
	for app in items:
		packages.append(app.package)
		target.add_item(app.label)


func _choose_target(index: int) -> void:
	if index > 0:
		package_field.text = packages[index - 1]


func _load_macro() -> void:
	var saved = JSON.parse_string(bridge.loadMacro())
	if saved is Dictionary and not saved.is_empty():
		package_field.text = saved.package
		steps.text = saved.steps
		repeat_count.value = saved.repeats


func _keyboard() -> void:
	bridge.openKeyboard(package_field.text.strip_edges())
	_refresh_status()


func _run() -> void:
	bridge.arm(package_field.text.strip_edges(), steps.text, int(repeat_count.value), text_payload.text, false)
	_refresh_status()


func _pick() -> void:
	bridge.arm(package_field.text.strip_edges(), steps.text, int(repeat_count.value), "", true)
	_refresh_status()


func _stop() -> void:
	bridge.stop()
	_refresh_status()


func _refresh_status() -> void:
	var ready: bool = bridge.isServiceReady()
	readiness.text = "Service connected" if ready else "Service disabled"
	readiness.add_theme_color_override("font_color", ACCENT if ready else MUTED)
	status.text = bridge.getStatus()
	var point: String = bridge.takePoint()
	if not point.is_empty():
		var existing := steps.text.strip_edges()
		steps.text = point if existing == "50, 50, 500" or existing.is_empty() else existing + "\n" + point
