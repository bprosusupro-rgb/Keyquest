extends SceneTree

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
		print("Header, target picker, and tabs fit at ", width, "px")
		viewport.free()
	quit()
