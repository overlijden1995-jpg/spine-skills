extends Node2D
## Medieval Sidescroller PoC — every character runs the SAME obstacle course.
## Course/physics/animation data come from res://data/characters.json, the
## exact file the off-line preview renderer uses, so both stay in sync.
##
## Play:        godot --path poc/godot_project
## Record film: godot --path poc/godot_project --write-movie poc/output/poc_video.avi --fixed-fps 30
##   (or pass --record-frames to dump PNG frames next to the project)

const PocChar := preload("res://scripts/Character.gd")
const VIEW := Vector2(1152, 648)

var chars: Array = []
var course: Dictionary = {}
var pivots: Dictionary = {}
var idx := 0
var runner: PocCharacter
var state := "title"           # title -> run -> attack -> run -> done
var state_t := 0.0
var vel_y := 0.0
var grounded := true
var used_triggers := {}
var double_jumped := false
var projectile: Dictionary = {}   # {pos, vel, active, color}
var dummy_hit_t := -1.0
var camera_x := 0.0
var record_frames := false
var frame_no := 0

@onready var cam: Camera2D = $Camera2D
var hud_name: Label
var hud_state: Label
var hud_bar: ColorRect

func _ready() -> void:
	var f := FileAccess.open("res://data/characters.json", FileAccess.READ)
	var parsed: Dictionary = JSON.parse_string(f.get_as_text())
	chars = parsed["characters"]
	course = parsed["course"]
	f = FileAccess.open("res://data/pivots.json", FileAccess.READ)
	pivots = JSON.parse_string(f.get_as_text())
	record_frames = "--record-frames" in OS.get_cmdline_args() or "--record-frames" in OS.get_cmdline_user_args()
	_build_hud()
	_spawn_current()
	queue_redraw()

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud_name = Label.new(); hud_name.position = Vector2(28, 18); hud_name.add_theme_font_size_override("font_size", 34)
	layer.add_child(hud_name)
	hud_state = Label.new(); hud_state.position = Vector2(28, 62); hud_state.add_theme_font_size_override("font_size", 20)
	layer.add_child(hud_state)
	var bg := ColorRect.new(); bg.color = Color(0, 0, 0, 0.45); bg.position = Vector2(28, 104); bg.size = Vector2(420, 10)
	layer.add_child(bg)
	hud_bar = ColorRect.new(); hud_bar.color = Color(0.95, 0.76, 0.19); hud_bar.position = Vector2(28, 104); hud_bar.size = Vector2(0, 10)
	layer.add_child(hud_bar)

func _spawn_current() -> void:
	if runner: runner.queue_free()
	runner = PocChar.new()
	add_child(runner)
	runner.setup(chars[idx], pivots)
	runner.position = Vector2(float(course["start_x"]), float(course["ground_y"]))
	state = "title"; state_t = 0.0; vel_y = 0.0
	used_triggers = {}; double_jumped = false
	projectile = {}; dummy_hit_t = -1.0
	var c: Dictionary = chars[idx]
	hud_name.text = "%d/10  %s — %s" % [idx + 1, c["name"], c["title"]]
	queue_redraw()

func _surface_y(x: float, feet_y: float) -> float:
	var best := -1.0
	for p in course["platforms"]:
		if x >= float(p["x"]) and x <= float(p["x"]) + float(p["w"]):
			var top := float(p["y"])
			if top >= feet_y - 12.0 and (best < 0.0 or top < best):
				best = top
	return best

func _stop_x() -> float:
	var atk: Dictionary = chars[idx]["attack"]
	var dummy_x := float(course["attack_trigger"]["dummy_x"])
	if atk["kind"] == "projectile":
		return dummy_x - 380.0
	return dummy_x - float(atk["range"]) - 24.0

func _process(delta: float) -> void:
	delta = min(delta, 1.0 / 30.0)
	state_t += delta
	var c: Dictionary = chars[idx]
	var atk: Dictionary = c["attack"]
	match state:
		"title":
			runner.pose("idle", state_t)
			if state_t > 0.9: state = "run"; state_t = 0.0
		"run", "attack":
			if state == "attack":
				runner.attack_t = state_t
				runner.pose("attack", state_t)
				if atk["kind"] == "projectile" and state_t >= 0.3 and projectile.is_empty():
					projectile = {"pos": runner.hand_global() + Vector2(20, -10),
						"vel": Vector2(float(atk["projectile_speed"]), 0.0), "active": true}
				if state_t >= float(atk["duration"]):
					state = "run"; state_t = 0.0; runner.attack_t = -1.0
			else:
				runner.position.x += float(c["speed"]) * delta
				runner.phase += delta * float(c["speed"]) / 34.0
				# jump triggers
				for i in course["jump_triggers"].size():
					var tr: Dictionary = course["jump_triggers"][i]
					if not used_triggers.has(i) and grounded and runner.position.x >= float(tr["x"]):
						used_triggers[i] = true
						vel_y = -float(c["jump_velocity"]) * float(tr["vy"])
						grounded = false
				# rogue double-jump / mage glide specials
				if not grounded and c.get("special", "") == "double_jump" and not double_jumped \
						and runner.position.x > float(course["spikes"]["x"]) - 40.0 and vel_y > -80.0:
					vel_y = -float(c["jump_velocity"]) * 0.72; double_jumped = true
				if state == "run" and runner.position.x >= _stop_x() and dummy_hit_t < 0.0:
					state = "attack"; state_t = 0.0
			# gravity + ground (hover in place while attacking/casting)
			if state == "attack":
				vel_y = 0.0
			elif true:
				vel_y += float(c["gravity"]) * delta
				if c.get("special", "") == "glide" and vel_y > 130.0 and not grounded:
					vel_y = 130.0
				var feet := runner.position.y
				runner.position.y += vel_y * delta
				var surf := _surface_y(runner.position.x, feet)
				if surf >= 0.0 and runner.position.y >= surf and vel_y >= 0.0:
					runner.position.y = surf; vel_y = 0.0; grounded = true
				elif surf < 0.0 or runner.position.y < (surf if surf >= 0.0 else 1e9) - 14.0:
					if runner.position.y < 640.0: grounded = false
				if runner.position.y > 660.0:  # fell in a pit: respawn on last ground
					runner.position.y = float(course["ground_y"]); vel_y = 0.0; grounded = true
			if state == "run":
				runner.pose("air" if not grounded else "run", state_t)
			if runner.position.x >= float(course["finish_x"]):
				state = "done"; state_t = 0.0
		"done":
			runner.pose("celebrate", state_t)
			if state_t > 1.0:
				idx += 1
				if idx >= chars.size():
					get_tree().quit()
				else:
					_spawn_current()
	# projectile flight
	if not projectile.is_empty() and projectile.get("active", false):
		projectile["pos"] += projectile["vel"] * delta
		if projectile["pos"].x >= float(course["attack_trigger"]["dummy_x"]):
			projectile["active"] = false; dummy_hit_t = 0.0
	if dummy_hit_t >= 0.0: dummy_hit_t += delta
	# melee hit check
	if state == "attack" and atk["kind"] == "melee" and state_t >= 0.3 and dummy_hit_t < 0.0:
		dummy_hit_t = 0.0
	# camera + HUD
	camera_x = clamp(runner.position.x - 380.0, 0.0, float(course["world_width"]) - VIEW.x)
	cam.position = Vector2(camera_x + VIEW.x / 2.0, VIEW.y / 2.0)
	hud_state.text = "ANIM: %s   WEAPON: %s   ATTACK: %s" % [
		("ATTACK" if state == "attack" else ("JUMP" if not grounded else state.to_upper())),
		c["weapon_label"], atk["label"]]
	hud_bar.size.x = 420.0 * clamp(runner.position.x / float(course["finish_x"]), 0.0, 1.0)
	queue_redraw()
	if record_frames:
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		DirAccess.make_dir_recursive_absolute("res://frames")
		img.save_png("res://frames/frame_%05d.png" % frame_no)
		frame_no += 1

func _draw() -> void:
	# sky, parallax castle + hills
	draw_rect(Rect2(camera_x - 60, 0, VIEW.x + 120, VIEW.y), Color.html("171233"))
	draw_circle(Vector2(camera_x + 980, 92), 34, Color.html("e8e3d8"))  # moon
	for p in course["platforms"]:
		var r := Rect2(float(p["x"]), float(p["y"]), float(p["w"]), float(p["h"]))
		if p["type"] == "ground":
			draw_rect(r, Color.html("57412a"))
			draw_rect(Rect2(r.position, Vector2(r.size.x, 16)), Color.html("3f7a3a"))
		else:
			draw_rect(r, Color.html("6e5136"))
			draw_rect(Rect2(r.position, Vector2(r.size.x, 6)), Color.html("8a6a44"))
			draw_line(r.position + Vector2(14, 24), r.position + Vector2(4, 70), Color.html("4a3826"), 6)
			draw_line(r.position + r.size + Vector2(-14, 0), r.position + Vector2(r.size.x - 4, 70), Color.html("4a3826"), 6)
	# start banner + finish banner
	draw_rect(Rect2(60, 380, 10, 140), Color.html("8a6a44"))
	draw_polygon(PackedVector2Array([Vector2(70, 384), Vector2(140, 396), Vector2(70, 410)]), PackedColorArray([Color.html("c9372c")]))
	var fx := float(course["finish_x"]) + 40.0
	draw_rect(Rect2(fx, 360, 10, 160), Color.html("8a6a44"))
	for row in range(4):
		for col in range(4):
			draw_rect(Rect2(fx + 10 + col * 13, 364 + row * 13, 13, 13), Color.WHITE if (row + col) % 2 == 0 else Color.html("1c1c26"))
	# spikes in the pit
	var sp: Dictionary = course["spikes"]
	for i in range(9):
		var sx := float(sp["x"]) + i * 20.0
		draw_polygon(PackedVector2Array([Vector2(sx, 648), Vector2(sx + 10, 606), Vector2(sx + 20, 648)]), PackedColorArray([Color.html("c8ccd8")]))
	# training dummy
	var dx := float(course["attack_trigger"]["dummy_x"])
	var tilt := 0.0
	if dummy_hit_t >= 0.0: tilt = min(dummy_hit_t * 3.0, 1.0) * 38.0
	draw_line(Vector2(dx, 520), Vector2(dx, 430), Color.html("6e5136"), 8)
	var head_c := Vector2(dx, 408) + Vector2(tilt * 0.6, tilt * 0.3)
	draw_circle(head_c, 20, Color.html("d9b06a"))
	draw_circle(head_c + Vector2(6, -2), 3, Color.html("30241a"))
	draw_arc(head_c, 30, 0, TAU, 24, Color.html("a83242"), 5)
	draw_line(Vector2(dx - 34, 452), Vector2(dx + 34, 452), Color.html("6e5136"), 7)
	if dummy_hit_t >= 0.0 and dummy_hit_t < 0.35:
		draw_arc(Vector2(dx - 10, 430), 52, -0.6, 1.1, 20, Color(1, 1, 1, 1.0 - dummy_hit_t * 2.5), 5)
	# projectile
	if not projectile.is_empty() and projectile.get("active", false):
		var pp: Vector2 = projectile["pos"]
		var col := Color.html(str(chars[idx]["attack"]["color"]))
		draw_circle(pp, 9, col)
		draw_circle(pp, 16, Color(col, 0.3))
		draw_line(pp - Vector2(26, 0), pp, col, 4)
