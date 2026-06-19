import pygame as pg
import math


class Flower:
    def __init__(self, x, y, color, glow_color, size=50, offset=(0, 0)):
        self.base_x = x
        self.base_y = y
        self.offset_x, self.offset_y = offset
        self.x = x + self.offset_x
        self.y = y + self.offset_y
        self.color = color
        self.glow_color = glow_color
        self.size = size
        self.bloomed = False
        self.bloom_progress = 0.0
        self.target_bloom_progress = 0.0
        self.bloom_speed = 0.05

    def set_bloomed_state(self, bloomed):
        self.target_bloom_progress = 1.0 if bloomed else 0.0

    def update(self, center_x, center_y):
        self.base_x, self.base_y = center_x, center_y
        self.x = self.base_x + self.offset_x
        self.y = self.base_y + self.offset_y

        if self.bloom_progress < self.target_bloom_progress:
            self.bloom_progress += self.bloom_speed
        elif self.bloom_progress > self.target_bloom_progress:
            self.bloom_progress -= self.bloom_speed
        self.bloom_progress = max(0.0, min(1.0, self.bloom_progress))

    def _draw_petal(self, screen, cx, cy, angle_deg, petal_w, petal_h, color):
        """Draw a smooth ellipse petal rotated around (cx, cy) at angle_deg."""
        surf = pg.Surface((petal_w * 2 + 4, petal_h * 2 + 4), pg.SRCALPHA)
        pg.draw.ellipse(surf, color, (2, 2, petal_w * 2, petal_h * 2))
        rotated = pg.transform.rotate(surf, -angle_deg)
        rect = rotated.get_rect(center=(cx, cy))
        screen.blit(rotated, rect)

    def draw(self, screen):
        # 1. Glow — kept subtle so overlapping glows stay clean
        glow_size = int(self.size * (0.9 + self.bloom_progress * 0.6))
        for i in range(4, 0, -1):
            alpha = int(55 * (i / 4.0) * (0.2 + self.bloom_progress * 0.8))
            gs = glow_size * i // 4
            if gs < 1:
                continue
            glow_surf = pg.Surface((gs * 2, gs * 2), pg.SRCALPHA)
            pg.draw.circle(glow_surf, (*self.glow_color, alpha), (gs, gs), gs)
            screen.blit(glow_surf, (self.x - gs, self.y - gs))

        # 2. Smooth ellipse petals — full 360° radial bloom
        num_petals = 6
        petal_w = int(self.size * 0.36)
        petal_h = int(self.size * (0.52 + self.bloom_progress * 0.42))
        dist = self.size * (0.22 + self.bloom_progress * 0.38)

        for i in range(num_petals):
            angle = (360 / num_petals) * i + (self.bloom_progress * 15)  # slight spin on bloom
            rad = math.radians(angle)
            px = self.x + math.cos(rad) * dist
            py = self.y + math.sin(rad) * dist

            shade = 0 if i % 2 == 0 else 18
            petal_color = (
                max(0, self.color[0] - shade),
                max(0, self.color[1] - shade),
                max(0, self.color[2] - shade),
                215
            )
            self._draw_petal(screen, px, py, angle + 90, petal_w, petal_h, petal_color)

        # 3. Centre circle
        centre_r = max(3, int(self.size * 0.17 * (0.4 + self.bloom_progress * 0.6)))
        pg.draw.circle(screen, (255, 230, 80), (int(self.x), int(self.y)), centre_r)
        pg.draw.circle(screen, (255, 255, 200),
                       (int(self.x) - centre_r // 3, int(self.y) - centre_r // 3),
                       max(1, centre_r // 3))

    def move(self, dx, dy):
        self.base_x += dx
        self.base_y += dy
