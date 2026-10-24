class_name PocCharacter
extends Node2D
## Procedurally-rigged 2D character: a Bone hierarchy of Node2Ds with
## Sprite2D parts (extracted from the magenta sheets). The hierarchy and
## animation curves mirror the Spine 4.2 skeleton in poc/spine/<id>/
## (same bone names: hip/torso/head/*-upper-arm/*-upper-leg/...).
## Animation is state-driven: idle / run / jump / attack / shoot / celebrate,
## matching the Spine preset generators (idle, walk, run, jump, attack, shoot).

var data: Dictionary
var pivots: Dictionary = {}
var bones: Dictionary = {}        # name -> Node2D
var weapon_sprite: Sprite2D
var phase := 0.0                  # run-cycle phase (radians)
var attack_t := -1.0              # >=0 while attacking
var face := 1.0

const UPPER_ARM_LEN := 40.0
const LOWER_ARM_LEN := 38.0
const UPPER_LEG_LEN := 44.0
const LOWER_LEG_LEN := 42.0

func _bone(parent: Node, bone_name: String, pos: Vector2) -> Node2D:
	var b := Node2D.new()
	b.name = bone_name
	b.position = pos
	parent.add_child(b)
	bones[bone_name] = b
	return b

func _attach(bone: Node2D, part: String, z: int = 0) -> Sprite2D:
	var tex: Texture2D = load("res://assets/%s/%s.png" % [data["id"], part])
	var s := Sprite2D.new()
	s.texture = tex
	s.z_index = z
	var pv: Array = pivots.get(part, {}).get("pivot", [tex.get_width() / 2.0, tex.get_height() / 2.0])
	# Sprite2D is centred; shift it so the bone origin sits on the part pivot.
	s.offset = Vector2(tex.get_width() / 2.0 - float(pv[0]), tex.get_height() / 2.0 - float(pv[1]))
	bone.add_child(s)
	return s

func setup(char_data: Dictionary, all_pivots: Dictionary) -> void:
	data = char_data
	pivots = all_pivots.get(data["id"], {})
	scale = Vector2.ONE * float(data.get("scale", 1.0))
	# --- skeleton (Godot y-down: up is -y) ---
	var hip := _bone(self, "hip", Vector2(0, -98))
	var torso := _bone(hip, "torso", Vector2(0, -6))
	var neck := _bone(torso, "neck", Vector2(0, -60))
	_bone(neck, "head", Vector2(0, -6))
	var lua := _bone(torso, "left-upper-arm", Vector2(-11, -50))
	_bone(lua, "left-lower-arm", Vector2(0, UPPER_ARM_LEN))
	var rua := _bone(torso, "right-upper-arm", Vector2(11, -50))
	var rla := _bone(rua, "right-lower-arm", Vector2(0, UPPER_ARM_LEN))
	_bone(rla, "weapon-bone", Vector2(0, LOWER_ARM_LEN))
	var lul := _bone(hip, "left-upper-leg", Vector2(-7, 0))
	var lll := _bone(lul, "left-lower-leg", Vector2(0, UPPER_LEG_LEN))
	_bone(lll, "left-foot", Vector2(0, LOWER_LEG_LEN))
	var rul := _bone(hip, "right-upper-leg", Vector2(7, 0))
	var rll := _bone(rul, "right-lower-leg", Vector2(0, UPPER_LEG_LEN))
	_bone(rll, "right-foot", Vector2(0, LOWER_LEG_LEN))
	# --- skins (draw order mirrors the Spine slot order) ---
	_attach(bones["left-upper-arm"], "left-upper-arm", -4)
	_attach(bones["left-lower-arm"], "left-lower-arm", -4)
	_attach(bones["left-lower-arm"], "accessory", -3)
	_attach(bones["left-upper-leg"], "left-upper-leg", -2)
	_attach(bones["left-lower-leg"], "left-lower-leg", -2)
	_attach(bones["left-foot"], "left-foot", -2)
	_attach(bones["hip"], "hip", 0)
	_attach(bones["torso"], "torso", 1)
	_attach(bones["head"], "head", 2)
	_attach(bones["right-upper-leg"], "right-upper-leg", 0)
	_attach(bones["right-lower-leg"], "right-lower-leg", 0)
	_attach(bones["right-foot"], "right-foot", 0)
	_attach(bones["right-upper-arm"], "right-upper-arm", 3)
	_attach(bones["right-lower-arm"], "right-lower-arm", 3)
	weapon_sprite = _attach(bones["weapon-bone"], "weapon", 4)

func _rot(bone_name: String, deg: float) -> void:
	bones[bone_name].rotation_degrees = deg

## state: idle|run|air|attack|celebrate ; t: seconds in state
func pose(state: String, t: float, speed_ratio: float = 1.0) -> void:
	var s := sin(phase)
	var c := cos(phase)
	match state:
		"idle":  # Spine 'idle': breathing sway
			_rot("torso", 1.5 * sin(t * 3.9))
			_rot("head", -2.0 * sin(t * 3.9 + 0.4))
			_rot("right-upper-arm", 3.0 * sin(t * 3.9))
			_rot("left-upper-arm", -3.0 * sin(t * 3.9))
			_rot("right-upper-leg", 2); _rot("left-upper-leg", -2)
			_rot("right-lower-leg", 2); _rot("left-lower-leg", 2)
			bones["hip"].position.y = -98 + 1.5 * sin(t * 7.8)
			weapon_sprite.rotation_degrees = -160
		"run", "walk":  # Spine 'run'/'walk': opposing arm/leg swing, hip bob
			var amp := 38.0 if state == "run" else 26.0
			_rot("right-upper-leg", amp * s)
			_rot("left-upper-leg", -amp * s)
			_rot("right-lower-leg", max(0.0, -52.0 * c) + 6)
			_rot("left-lower-leg", max(0.0, 52.0 * c) + 6)
			_rot("right-foot", -amp * 0.4 * s)
			_rot("left-foot", amp * 0.4 * s)
			_rot("right-upper-arm", -amp * 0.8 * s)
			_rot("left-upper-arm", amp * 0.8 * s)
			_rot("right-lower-arm", -18 - 10 * c)
			_rot("left-lower-arm", -18 + 10 * c)
			_rot("torso", 7 + 3 * sin(phase * 2.0))
			_rot("head", -5)
			bones["hip"].position.y = -98 - abs(sin(phase)) * 6.0
			weapon_sprite.rotation_degrees = -150 + 8 * s
		"air":  # Spine 'jump' air pose: tuck + arms up
			_rot("right-upper-leg", -28); _rot("left-upper-leg", 14)
			_rot("right-lower-leg", 42); _rot("left-lower-leg", 18)
			_rot("right-upper-arm", -52); _rot("left-upper-arm", 40)
			_rot("right-lower-arm", -24); _rot("left-lower-arm", -14)
			_rot("torso", -4); _rot("head", -6)
			weapon_sprite.rotation_degrees = -140
		"attack":  # Spine 'attack' (melee) or 'shoot' (ranged)
			var d := float(data["attack"]["duration"])
			var k := clamp(attack_t / d, 0.0, 1.0)
			if data["attack"]["kind"] == "projectile":
				var aim := sin(min(k * 3.0, 1.0) * PI * 0.5)
				_rot("right-upper-arm", -78 * aim)
				_rot("left-upper-arm", -52 * aim)
				_rot("left-lower-arm", -18 * aim)
				_rot("torso", 6 * aim); _rot("head", -4 * aim)
			else:
				# wind-up (k<.35) -> strike (k<.6) -> recover
				var ang: float
				if k < 0.35: ang = lerpf(0.0, 55.0, k / 0.35)
				elif k < 0.6: ang = lerpf(55.0, -95.0, (k - 0.35) / 0.25)
				else: ang = lerpf(-95.0, 0.0, (k - 0.6) / 0.4)
				_rot("right-upper-arm", ang)
				_rot("right-lower-arm", ang * 0.35 - 10)
				_rot("torso", -ang * 0.14)
				weapon_sprite.rotation_degrees = -160 + ang * 0.4
			_rot("right-upper-leg", 10); _rot("left-upper-leg", -12)
			_rot("right-lower-leg", 8); _rot("left-lower-leg", 10)
		"celebrate":
			_rot("right-upper-arm", -150 + 12 * sin(t * 10.0))
			_rot("left-upper-arm", -130 - 12 * sin(t * 10.0))
			_rot("torso", 3 * sin(t * 5.0)); _rot("head", -4)
			bones["hip"].position.y = -98 - abs(sin(t * 6.0)) * 8.0
			weapon_sprite.rotation_degrees = -30

func hand_global() -> Vector2:
	return (bones["weapon-bone"] as Node2D).global_position
