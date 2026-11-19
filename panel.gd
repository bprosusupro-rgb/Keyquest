extends Control

const INK := Color("#0d1a16")
const TEXT := Color("#edf6fb")
const MUTED := Color("#abc0d2")
const ACCENT := Color("#92f3d2")
const SURFACE := Color("#15212f")
const CONTROL := Color("#223248")
const OUTLINE := Color("#34475e")

const KEY_ROWS := ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
const SYMBOL_ROWS := ["1234567890", "@#%&?!:;_", "()[]+-=/"]

var draft: LineEdit
var keyboard_status: Label
var key_rows: VBoxContainer
var bridge_message := ""
var shifted := false
var symbols := false

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
var service_button: Button
var manual_button: Button
var tabs: TabContainer
var inset: MarginContainer


func _ready() -> void:
	theme = _make_theme()
	inset = MarginContainer.new()
	add_child(inset)
	inset.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	resized.connect(_fit_panel)
	_fit_panel()
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	inset.add_child(scroll)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 14)
	scroll.add_child(column)

	var brand := HBoxContainer.new()
	brand.add_theme_constant_override("separation", 12)
	column.add_child(brand)
	var logo := TextureRect.new()
	logo.texture = preload("res://icon.png")
	logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	logo.custom_minimum_size = Vector2(48, 48)
	brand.add_child(logo)
	var title := _label(brand, "Keyquest", 36, TEXT)
	title.autowrap_mode = TextServer.AUTOWRAP_OFF
	title.size_flags_horizontal = SIZE_EXPAND_FILL
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER

	var setup := _card(column)
	readiness = _label(setup, "Accessibility service unavailable", 16, MUTED)
	service_button = _button(setup, "Accessibility settings", _settings)
	_label(setup, "Target game", 19, TEXT)
	target.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	target.clip_text = true
	target.custom_minimum_size.y = 52
	setup.add_child(target)
	target.item_selected.connect(_choose_target)
	manual_button = Button.new()
	manual_button.text = "Enter package name"
	manual_button.toggle_mode = true
	manual_button.custom_minimum_size.y = 48
	setup.add_child(manual_button)
	package_field.placeholder_text = "com.example.game"
	package_field.custom_minimum_size.y = 52
	package_field.hide()
	setup.add_child(package_field)
	manual_button.toggled.connect(func(visible_field: bool) -> void:
		package_field.visible = visible_field
		if visible_field:
			package_field.grab_focus()
	)

	tabs = TabContainer.new()
	tabs.clip_tabs = true
	tabs.add_theme_stylebox_override("panel", _style(SURFACE, OUTLINE))
	column.add_child(tabs)

	var keyboard := _page("Keyboard")
	_label(keyboard, "Type in Keyquest", 26, TEXT)
	draft = LineEdit.new()
	draft.editable = false
	draft.placeholder_text = "Tap the keys to type"
	draft.custom_minimum_size.y = 50
	keyboard.add_child(draft)
	key_rows = VBoxContainer.new()
	key_rows.add_theme_constant_override("separation", 4)
	keyboard.add_child(key_rows)
	_draw_keys()
	keyboard_status = _label(keyboard, "Open a text prompt in the selected game, then tap a key here.", 16, MUTED)
	actions.erase(_button(keyboard, "Copy text", _copy_draft))

	var macro := _page("Macros")
	_label(macro, "Tap sequence", 26, TEXT)
	_label(macro, "One step per line with x%, y%, and delay in milliseconds.", 16, MUTED)
	steps.custom_minimum_size.y = 96
	steps.text = "50, 50, 500"
	macro.add_child(steps)
	_label(macro, "Repeat count", 16, MUTED)
	repeat_count.min_value = 1
	repeat_count.max_value = 100
	repeat_count.value = 1
	repeat_count.custom_minimum_size.y = 50
	macro.add_child(repeat_count)
	text_payload.placeholder_text = "Optional text after the taps"
	text_payload.custom_minimum_size.y = 50
	macro.add_child(text_payload)
	_button(macro, "Find tap point", _pick)
	_button(macro, "Run macro", _run, true)
	_button(macro, "Stop", _stop)
	tabs.tab_changed.connect(func(_index: int) -> void: tabs.update_minimum_size())
	var feedback := _card(column)
	status = _label(feedback, "", 16, MUTED)
	status.custom_minimum_size.y = 24
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


func _fit_panel() -> void:
	var horizontal := maxi(16, int((size.x - 740.0) / 2.0))
	for side in ["left", "right"]:
		inset.add_theme_constant_override("margin_" + side, horizontal)
	for side in ["top", "bottom"]:
		inset.add_theme_constant_override("margin_" + side, 16)


func _page(title: String) -> VBoxContainer:
	var padding := MarginContainer.new()
	padding.name = title
	for side in ["left", "right", "top", "bottom"]:
		padding.add_theme_constant_override("margin_" + side, 12)
	tabs.add_child(padding)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 10)
	padding.add_child(content)
	return content


func _make_theme() -> Theme:
	var ui := Theme.new()
	ui.default_font_size = 18
	ui.set_color("font_color", "Label", TEXT)
	ui.set_stylebox("tab_selected", "TabContainer", _style(ACCENT))
	ui.set_stylebox("tab_unselected", "TabContainer", _style(CONTROL))
	ui.set_stylebox("tab_hovered", "TabContainer", _style(Color("#3c6270")))
	ui.set_color("font_selected_color", "TabContainer", INK)
	ui.set_color("font_unselected_color", "TabContainer", TEXT)
	ui.set_constant("side_margin", "TabContainer", 12)
	ui.set_stylebox("panel", "PopupMenu", _style(SURFACE, OUTLINE))
	ui.set_stylebox("hover", "PopupMenu", _style(CONTROL))
	ui.set_color("font_color", "PopupMenu", TEXT)
	ui.set_constant("v_separation", "PopupMenu", 22)
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


func _button(parent: Container, caption: String, action: Callable, primary := false) -> Button:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size.y = 52
	button.size_flags_horizontal = SIZE_EXPAND_FILL
	if primary:
		button.add_theme_stylebox_override("normal", _style(ACCENT))
		button.add_theme_stylebox_override("hover", _style(Color("#c4ffeb"), ACCENT))
		button.add_theme_stylebox_override("pressed", _style(Color("#6bd5b0")))
		for state in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
			button.add_theme_color_override(state, INK)
	button.pressed.connect(action)
	parent.add_child(button)
	actions.append(button)
	return button


func _label(parent: Container, caption: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = caption
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	return label


func _settings() -> void:
	bridge_message = ""
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
		var previous := packages.find(saved.package)
		if previous >= 0:
			target.select(previous + 1)
		else:
			manual_button.set_pressed_no_signal(true)
			package_field.show()
		steps.text = saved.steps
		repeat_count.value = saved.repeats


func _draw_keys() -> void:
	for child in key_rows.get_children():
		key_rows.remove_child(child)
		child.queue_free()
	for letters in SYMBOL_ROWS if symbols else KEY_ROWS:
		var row := _key_row()
		for character in letters:
			var value: String = character.to_upper() if shifted else character
			_key(row, value, _type_key.bind(value))
	var tools := _key_row()
	_key(tools, "Shift", func() -> void:
		shifted = not shifted
		_draw_keys()
	)
	_key(tools, "ABC" if symbols else "123", func() -> void:
		symbols = not symbols
		_draw_keys()
	)
	_key(tools, "Space", _type_key.bind(" "), 1.5)
	_key(tools, "⌫", _backspace)
	_key(tools, "Enter", _dispatch_key.bind("\n"))
	_key(tools, "Clear", func() -> void: _set_draft(""))


func _key_row() -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 3)
	key_rows.add_child(row)
	return row


func _key(row: HBoxContainer, caption: String, handler: Callable, weight := 1.0) -> void:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size.y = 46
	button.size_flags_horizontal = SIZE_EXPAND_FILL
	button.size_flags_stretch_ratio = weight
	for state in ["normal", "hover", "pressed"]:
		var fill := CONTROL if state == "normal" else Color("#395a71")
		var box := _style(fill)
		box.content_margin_left = 2
		box.content_margin_right = 2
		button.add_theme_stylebox_override(state, box)
	button.pressed.connect(handler)
	row.add_child(button)


func _set_draft(value: String) -> void:
	draft.text = value
	draft.caret_column = draft.text.length()


func _type_key(value: String) -> void:
	_dispatch_key(value)
	if draft.text.length() < 500:
		_set_draft(draft.text + value)
	if shifted and not symbols:
		shifted = false
		_draw_keys()


func _backspace() -> void:
	_set_draft(draft.text.left(-1))
	_dispatch_key("\b")


func _dispatch_key(value: String) -> void:
	if bridge == null:
		return
	bridge_message = ""
	bridge.sendKey(package_field.text.strip_edges(), value)


func _copy_draft() -> void:
	if draft.text.is_empty():
		return
	DisplayServer.clipboard_set(draft.text)
	bridge_message = "Copied. Switch to the game and paste if it supports the clipboard."
	status.text = bridge_message
	keyboard_status.text = bridge_message


func _run() -> void:
	bridge_message = ""
	bridge.arm(package_field.text.strip_edges(), steps.text, int(repeat_count.value), text_payload.text, false)
	_refresh_status()


func _pick() -> void:
	bridge_message = ""
	bridge.arm(package_field.text.strip_edges(), steps.text, int(repeat_count.value), "", true)
	_refresh_status()


func _stop() -> void:
	bridge_message = ""
	bridge.stop()
	_refresh_status()


func _refresh_status() -> void:
	var ready: bool = bridge.isServiceReady()
	readiness.text = "Service connected" if ready else "Service disabled"
	readiness.add_theme_color_override("font_color", ACCENT if ready else MUTED)
	service_button.text = "Accessibility settings" if ready else "Enable accessibility service"
	status.text = bridge.getStatus() if bridge_message.is_empty() else bridge_message
	keyboard_status.text = status.text
	var point: String = bridge.takePoint()
	if not point.is_empty():
		var existing := steps.text.strip_edges()
		steps.text = point if existing == "50, 50, 500" or existing.is_empty() else existing + "\n" + point
