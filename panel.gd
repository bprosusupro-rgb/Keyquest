extends Control

var bridge: Object
var target := OptionButton.new()
var package_field := LineEdit.new()
var steps := TextEdit.new()
var repeat_count := SpinBox.new()
var status := Label.new()
var packages := PackedStringArray()
var text_payload := LineEdit.new()
var actions: Array[Button] = []


func _ready() -> void:
	var inset := MarginContainer.new()
	add_child(inset)
	inset.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		inset.add_theme_constant_override("margin_" + side, 28)
	var scroll := ScrollContainer.new()
	inset.add_child(scroll)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 10)
	scroll.add_child(column)
	var title := _label(column, "Quest Panel Macros")
	title.add_theme_font_size_override("font_size", 34)
	_button(column, "Open Android accessibility settings", _settings)
	_label(column, "Target app")
	column.add_child(target)
	target.item_selected.connect(_choose_target)
	package_field.placeholder_text = "Android package, e.g. com.example.game"
	column.add_child(package_field)
	_label(column, "Steps · x%, y%, delay after tap in milliseconds")
	steps.custom_minimum_size.y = 110
	steps.text = "50, 50, 500"
	column.add_child(steps)
	_label(column, "Repeat count · one-step macros work as auto-clickers")
	repeat_count.min_value = 1
	repeat_count.max_value = 100
	repeat_count.value = 1
	column.add_child(repeat_count)
	_label(column, "Optional text to enter after the taps")
	text_payload.placeholder_text = "Requires an Android text input connection"
	column.add_child(text_payload)
	var row := HBoxContainer.new()
	column.add_child(row)
	_button(row, "Find tap point", _pick)
	_button(row, "Run in target", _run)
	_button(row, "Stop", _stop)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(status)
	if not Engine.has_singleton("QuestMacros"):
		status.text = "Install the Android APK to connect to the accessibility service."
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


func _button(parent: Container, caption: String, action: Callable) -> void:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size.y = 44
	button.size_flags_horizontal = SIZE_EXPAND_FILL
	button.pressed.connect(action)
	parent.add_child(button)
	actions.append(button)


func _label(parent: Container, caption: String) -> Label:
	var label := Label.new()
	label.text = caption
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	return label


func _settings() -> void:
	bridge.openSettings()


func _reload_targets() -> void:
	var items = JSON.parse_string(bridge.listApps())
	packages.clear()
	target.clear()
	target.add_item("Select an installed app or enter its package")
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
	status.text = bridge.getStatus()
	var point: String = bridge.takePoint()
	if not point.is_empty():
		var existing := steps.text.strip_edges()
		steps.text = point if existing == "50, 50, 500" or existing.is_empty() else existing + "\n" + point
