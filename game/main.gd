extends Node2D
## A deterministic side-scrolling parade: ten palette/gear variants run, jump, and attack.
const NAMES = ["Iron Warden", "Foxblade", "Northwind", "Vermilion"]
const COLORS = [Color("#b8c8d8"),Color("#d69a43"),Color("#7599b6"),Color("#a94857")]
const COURSE = 4400.0
var elapsed := 0.0
var speed := 165.0
var paused := false
var show_labels := true
var font: Font

func _ready():
    font = ThemeDB.fallback_font
    RenderingServer.set_default_clear_color(Color("#101827"))

func _process(delta):
    if not paused: elapsed += delta
    queue_redraw()

func _input(event):
    if event is InputEventKey and event.pressed and not event.echo:
        match event.keycode:
            KEY_SPACE: paused = !paused
            KEY_L: show_labels = !show_labels
            KEY_R: elapsed = 0.0

func _draw():
    var w = get_viewport_rect().size.x
    var h = get_viewport_rect().size.y
    draw_rect(Rect2(0,0,w,h),Color("#101827"))
    # layered dusk sky and distant castle silhouettes
    for i in range(8):
        var x = fposmod(i*235.0 - elapsed*15.0, w+235)-235
        draw_rect(Rect2(x,345,130,115),Color("#19263a"))
        draw_rect(Rect2(x+22,290,22,55),Color("#19263a"))
        draw_rect(Rect2(x+83,270,24,75),Color("#19263a"))
        draw_colored_polygon(PackedVector2Array([Vector2(x+18,290),Vector2(x+33,268),Vector2(x+48,290)]),Color("#19263a"))
    draw_rect(Rect2(0,480,w,240),Color("#293b39"))
    draw_rect(Rect2(0,500,w,220),Color("#4c4536"))
    # obstacle course is shared exactly for each contestant
    for j in range(22):
        var ox = fposmod(j*245.0 - elapsed*speed, w+80)-40
        if j%4==1:
            draw_rect(Rect2(ox,454,34,46),Color("#8b563d")); draw_rect(Rect2(ox-5,449,44,7),Color("#d0a76b"))
        elif j%4==2:
            draw_circle(Vector2(ox+10,484),10,Color("#aeb8b7")); draw_circle(Vector2(ox+28,488),7,Color("#748083"))
        elif j%4==3:
            draw_rect(Rect2(ox,405,8,76),Color("#75523b")); draw_rect(Rect2(ox-14,407,36,8),Color("#c7a263"))
    # four fighters share the course; phase offsets make their motion distinct
    for i in range(4):
        var col = i
        var x = 170 + col*310.0
        var y = 434
        var phase = elapsed*7.8 + i*0.63
        var stride = sin(phase)*17.0
        var attack = fposmod(elapsed*0.72 + i*0.29, 3.7) < 0.52
        var jump = fposmod(elapsed*0.57 + i*0.41, 4.2) < 0.68
        var bob = abs(sin(phase*0.5))*4.0 - (32.0 if jump else 0.0)
        var c = COLORS[i]
        var px = x
        var py = y+bob
        # ground shadow
        draw_ellipse(Vector2(px, y+10),Vector2(22,5),Color(0,0,0,0.3))
        # legs: pivot motion conveys run cycle; boots and armor
        var leg_a = Vector2(px-5+stride*.35,py-25)
        var leg_b = Vector2(px+5-stride*.35,py-25)
        draw_line(Vector2(px-4,py-44),leg_a,c.darkened(.28),10)
        draw_line(leg_a,Vector2(leg_a.x+stride*.22,py-8),c,9)
        draw_line(Vector2(px+4,py-44),leg_b,c.darkened(.18),10)
        draw_line(leg_b,Vector2(leg_b.x-stride*.22,py-8),c,9)
        draw_line(Vector2(leg_a.x+stride*.22,py-8),Vector2(leg_a.x+stride*.22+8,py-7),Color("#292d36"),6)
        draw_line(Vector2(leg_b.x-stride*.22,py-8),Vector2(leg_b.x-stride*.22+8,py-7),Color("#292d36"),6)
        # torso and belt
        draw_rect(Rect2(px-12,py-66,24,28),c)
        draw_rect(Rect2(px-12,py-45,24,5),Color("#49382d"))
        draw_circle(Vector2(px,py-52),3,Color("#e6c56d"))
        # shield and animated sword arm
        draw_line(Vector2(px-10,py-62),Vector2(px-20,py-43+stride*.16),c.darkened(.24),7)
        draw_ellipse(Vector2(px-23,py-38+stride*.16),Vector2(8,12),Color("#bd995d"))
        draw_line(Vector2(px+10,py-62),Vector2(px+16,py-47),c.darkened(.17),7)
        var sword_end = Vector2(px+(43 if attack else 25),py-(70 if attack else 48))
        draw_line(Vector2(px+16,py-47),sword_end,Color("#ad8952"),4)
        draw_line(sword_end,sword_end+Vector2(15,-8),Color("#dfe8eb"),3)
        # head, helmet, plume
        draw_circle(Vector2(px+2,py-76),10,Color("#d99c70"))
        draw_arc(Vector2(px+2,py-78),11,PI,TAU,16,c,7)
        draw_rect(Rect2(px-8,py-86,21,6),c.darkened(.1))
        draw_circle(Vector2(px+6,py-76),1.4,Color("#29252a"))
        if i%3==1:
            draw_line(Vector2(px+2,py-89),Vector2(px+12,py-101),Color("#bb473a"),4)
        if show_labels:
            draw_string(font,Vector2(px-42,py+28),NAMES[i],HORIZONTAL_ALIGNMENT_CENTER,84,12,Color("#e7e1d2"))
    # overlay title / controls
    draw_string(font,Vector2(32,42),"MEDIEVAL MOTION LAB",HORIZONTAL_ALIGNMENT_LEFT,-1,24,Color("#f0d59a"))
    draw_string(font,Vector2(32,67),"FOUR WARRIORS  ·  ONE COURSE  ·  RUN / JUMP / ATTACK",HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color("#a8b5c4"))
    var progress = fposmod(elapsed*speed,COURSE)/COURSE
    draw_rect(Rect2(32,h-27,w-64,5),Color("#354252"))
    draw_rect(Rect2(32,h-27,(w-64)*progress,5),Color("#e2b967"))
    draw_string(font,Vector2(32,h-39),"SPACE pause  ·  R reset  ·  L labels",HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color("#a8b5c4"))

func draw_ellipse(center: Vector2, radius: Vector2, color: Color):
    var points := PackedVector2Array()
    for k in range(16):
        var a = TAU*k/16.0
        points.append(center+Vector2(cos(a)*radius.x,sin(a)*radius.y))
    draw_colored_polygon(points,color)
