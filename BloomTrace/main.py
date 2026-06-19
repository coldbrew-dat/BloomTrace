import pygame as pg
import sys
import cv2
import mediapipe as mp
import math
from flower import Flower

#mediapipe setup
try:
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
except Exception:
    import mediapipe.solutions.hands as mp_hands
    import mediapipe.solutions.drawing_utils as mp_drawing

#pygame setup
pg.init()
WIDTH, HEIGHT = 1280, 720
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("Bloomtrace")

#hand tracking setup
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
NEON_PINK      = (255, 20, 147)
NEON_PINK_DIM  = (200, 10, 110)
HAND_CONNECTIONS = mp_hands.HAND_CONNECTIONS

#camera setup (if system has camera)
cap = cv2.VideoCapture(0)
camera_ok = cap.isOpened()

#bouquet layout
# flowers are spread wide enough that their glows never touch.
# each offset is (dx, dy) from the bouquet hold-point.
# negative y = upward.  We also store a "branch_y" — how far up the main stem
# the branch junction sits (0.0 = hold-point, 1.0 = top of main stem).
STEM_TOP_DY = -320   # how tall the main stem is (px)

flower_configs = [
    # idx  offset            branch_y   color                glow                  size
    {"offset": (   0, -300), "branch_y": 0.92, "color": (255, 105, 180), "glow": (255, 200, 220), "size": 52},
    {"offset": (-145, -240), "branch_y": 0.72, "color": (255,  80, 160), "glow": (255, 180, 210), "size": 46},
    {"offset": ( 145, -240), "branch_y": 0.72, "color": (255, 130, 190), "glow": (255, 210, 230), "size": 46},
    {"offset": (-260, -160), "branch_y": 0.48, "color": (220,  60, 150), "glow": (240, 160, 200), "size": 44},
    {"offset": ( 260, -160), "branch_y": 0.48, "color": (255, 150, 200), "glow": (255, 220, 240), "size": 44},
    {"offset": ( -80, -290), "branch_y": 0.85, "color": (240,  90, 170), "glow": (255, 190, 215), "size": 40},
    {"offset": (  80, -290), "branch_y": 0.85, "color": (255, 100, 175), "glow": (255, 200, 225), "size": 40},
    {"offset": (-185, -110), "branch_y": 0.30, "color": (255,  60, 140), "glow": (255, 170, 205), "size": 38},
    {"offset": ( 185, -110), "branch_y": 0.30, "color": (255, 170, 210), "glow": (255, 230, 245), "size": 38},
]

flowers = []
for cfg in flower_configs:
    ox, oy = cfg["offset"]
    f = Flower(
        WIDTH // 2, HEIGHT // 2,
        cfg["color"], cfg["glow"],
        size=cfg["size"],
        offset=(ox, oy),
    )
    f.branch_y = cfg["branch_y"]   # attach extra attribute
    flowers.append(f)

center_x, center_y = float(WIDTH // 2), float(HEIGHT // 2)

# stem colours
STEM_DARK   = ( 80, 140,  50)
STEM_MID    = (120, 190,  80)
STEM_LIGHT  = (160, 220, 110)


def draw_bezier_curve(surface, color, p0, p1, p2, width=3, steps=40):
    """Draw a smooth quadratic Bezier curve from p0 through control p1 to p2."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((int(x), int(y)))
    if len(pts) >= 2:
        pg.draw.lines(surface, color, False, pts, width)


def draw_bouquet_stems(surface, cx, cy):
    """Draw one main stem + gracefully arching branches to each flower head."""
    hold_x, hold_y = int(cx), int(cy)
    stem_tip_y = int(cy + STEM_TOP_DY)

    #main stem: gentle S-curve using two bezier segments 
    # bottom half: slight lean right
    mid_y = (hold_y + stem_tip_y) // 2
    ctrl1 = (hold_x + 8, mid_y + 40)
    draw_bezier_curve(surface, STEM_DARK,  (hold_x, hold_y), ctrl1, (hold_x + 3, mid_y), width=6)
    draw_bezier_curve(surface, STEM_LIGHT, (hold_x + 1, hold_y), ctrl1, (hold_x + 4, mid_y), width=2)
    # top half: lean back left
    ctrl2 = (hold_x - 6, mid_y - 40)
    draw_bezier_curve(surface, STEM_DARK,  (hold_x + 3, mid_y), ctrl2, (hold_x, stem_tip_y), width=6)
    draw_bezier_curve(surface, STEM_LIGHT, (hold_x + 4, mid_y), ctrl2, (hold_x + 1, stem_tip_y), width=2)

    #branches: arc naturally from stem junction up to each flower
    for f in flowers:
        jx = int(hold_x)
        jy = int(hold_y + (stem_tip_y - hold_y) * f.branch_y)

        fx = int(f.x)
        fy = int(f.y)

        #control point: start near the junction arc upward toward the flower
        #pull the control point UP and slightly toward the flower horizontally
        dx = fx - jx
        ctrl_x = jx + dx * 0.3
        ctrl_y = jy - abs(dx) * 0.55  # the wider the branch, the more it arches up

        draw_bezier_curve(surface, STEM_MID,   (jx, jy), (ctrl_x, ctrl_y), (fx, fy), width=3)
        draw_bezier_curve(surface, STEM_LIGHT, (jx + 1, jy), (ctrl_x + 1, ctrl_y), (fx + 1, fy), width=1)

        #small node dot where branch leaves the main stem
        pg.draw.circle(surface, STEM_DARK,  (jx, jy), 5)
        pg.draw.circle(surface, STEM_LIGHT, (jx, jy), 3)


def is_hand_open(landmarks):
    thumb = landmarks.landmark[4]
    pinky = landmarks.landmark[20]
    dist  = math.sqrt((thumb.x - pinky.x) ** 2 + (thumb.y - pinky.y) ** 2)
    return dist > 0.15


def draw_hand_landmarks_neon(surface, landmarks, width, height):
    lm  = landmarks.landmark
    pts = [(int(lm[i].x * width), int(lm[i].y * height)) for i in range(21)]

    for start_idx, end_idx in HAND_CONNECTIONS:
        pg.draw.line(surface, NEON_PINK_DIM, pts[start_idx], pts[end_idx], 2)

    fingertips = {4, 8, 12, 16, 20}
    for i, (px, py) in enumerate(pts):
        r = 7 if i in fingertips else 4
        pg.draw.circle(surface, NEON_PINK, (px, py), r)
        pg.draw.circle(surface, (255, 255, 255), (px, py), max(1, r - 2), 1)


clock = pg.time.Clock()

while True:
    screen.fill((0, 0, 0)) #background color 

    for event in pg.event.get():
        if event.type == pg.QUIT:
            cap.release()
            pg.quit()
            sys.exit()
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_SPACE:
                for f in flowers:
                    new_state = not f.bloomed
                    f.set_bloomed_state(new_state)
                    f.bloomed = new_state

    keys = pg.key.get_pressed()
    if keys[pg.K_w]: center_y -= 5
    if keys[pg.K_s]: center_y += 5
    if keys[pg.K_a]: center_x -= 5
    if keys[pg.K_d]: center_x += 5

    if camera_ok:
        success, img = cap.read()
        if success:
            img    = cv2.flip(img, 1)
            rgb    = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    open_state = is_hand_open(hand_landmarks)
                    for f in flowers:
                        f.set_bloomed_state(open_state)
                    index_tip = hand_landmarks.landmark[8]
                    target_x  = index_tip.x * WIDTH
                    target_y  = index_tip.y * HEIGHT
                    center_x += (target_x - center_x) * 0.1
                    center_y += (target_y - center_y) * 0.1
                    draw_hand_landmarks_neon(screen, hand_landmarks, WIDTH, HEIGHT)

    #update positions
    for f in flowers:
        f.update(center_x, center_y)

    #draw stems FIRST (behind flowers)
    draw_bouquet_stems(screen, center_x, center_y)

    #draw flowers on top
    for f in flowers:
        f.draw(screen)

    pg.display.flip()
    clock.tick(60)
