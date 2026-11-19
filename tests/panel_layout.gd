extends SceneTree

class KeyReceiver extends RefCounted:
	var keys: Array[String] = []
	var target := ""

	func sendKey(package_name: String, key: String) -> void:
		target = package_name
		keys.append(key)

func _initialize() -> void:
	call_deferred("_check")

func _check() -> void:
	for width in [360, 540, 960]:
		var viewport := SubViewport.new()
		viewport.size = Vector2i(width, 400)
		root.add_child(viewport)
		var panel = load("res://panel.tscn").instantiate()
		viewport.add_child(panel)
		await process_frame
		await process_frame
		var scroll: ScrollContainer = panel.inset.get_child(0)
		var column: VBoxContainer = scroll.get_child(0)
		var tabs: TabContainer = panel.tabs
		var brand: HBoxContainer = column.get_child(0)
		var title: Label = brand.get_child(1)
		if title.get_line_count() != 1 or brand.size.y > 64.0:
			push_error("Title wraps at width %d (%d lines, header %.1f px)" % [width, title.get_line_count(), brand.size.y])
			quit(1)
			return
		if panel.target.get_global_rect().end.y > scroll.get_global_rect().end.y:
			push_error("Target picker is below the fold at width %d" % width)
			quit(1)
			return
		for tab_index in range(2):
			tabs.current_tab = tab_index
			await process_frame
			await process_frame
			if column.get_combined_minimum_size().x > scroll.size.x - scroll.get_v_scroll_bar().size.x:
				push_error("Layout clips at width %d on tab %d" % [width, tab_index])
				quit(1)
				return
			if not tabs.get_tab_control(tab_index).visible:
				push_error("Selected tab did not display")
				quit(1)
				return
		tabs.current_tab = 0
		var receiver := KeyReceiver.new()
		panel.bridge = receiver
		panel.package_field.text = "org.example.game"
		panel.key_rows.get_child(0).get_child(0).pressed.emit()
		panel.key_rows.get_child(3).get_child(0).pressed.emit()
		panel.key_rows.get_child(0).get_child(1).pressed.emit()
		panel.key_rows.get_child(3).get_child(2).pressed.emit()
		panel.key_rows.get_child(3).get_child(1).pressed.emit()
		panel.key_rows.get_child(0).get_child(0).pressed.emit()
		panel.key_rows.get_child(3).get_child(3).pressed.emit()
		if panel.draft.text != "qW ":
			push_error("On-screen keys or Backspace did not update the draft")
			quit(1)
			return
		panel.key_rows.get_child(3).get_child(4).pressed.emit()
		if receiver.target != "org.example.game" or receiver.keys != ["q", "W", " ", "1", "\b", "\n"]:
			push_error("A key press did not immediately dispatch to the selected target")
			quit(1)
			return
		panel.key_rows.get_child(3).get_child(5).pressed.emit()
		if not panel.draft.text.is_empty():
			push_error("Clear did not empty the draft")
			quit(1)
			return
		print("Header, tabs, and in-app keys passed at ", width, "px")
		viewport.free()
	quit()
