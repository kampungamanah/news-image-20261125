#!/usr/bin/env python3
"""One day's world news in one image: Wednesday 25 November 2026.

A pure-standard-library Python program. It draws a newspaper front page
summarising five stories first reported on 25 November 2026 and writes it
as a deterministic 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png
(or /output/entry.png). No network, no randomness, no clock, no fonts
from disk: text is drawn with a small stroke font defined below, and the
PNG bytes are encoded by hand with zlib.

Stories baked in (all first reported on Wed 25 Nov 2026):
  1. Ukraine confirms drone strikes on Russian ships in the Gulf of
     Finland and off Libya; Russia calls them "terrorist acts".
  2. China launches Shenzhou-24 from Jiuquan with Pakistani astronaut
     Muhammad Zeeshan Ali, the first foreign visitor to Tiangong.
  3. Gunmen seize a supermarket in Cartagena, Colombia, holding at
     least 30 people hostage after a failed cash-truck robbery.
  4. Solomon Islands ends its security pact with China and signs a
     new security agreement with Australia.
  5. Donald Trump awards the Presidential Medal of Freedom to Rudy
     Giuliani at the White House.
Ticker: O'Hare radar outage delays flights; South Korea's education
minister resigns over an exam-cheating scandal; the US blacklists
Singapore firm Megaspeed over Nvidia AI-chip diversion.
"""

import binascii
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# Palette: warm newsprint paper, deep navy ink, red, gold, teal.
PAPER = (246, 241, 229)
PAPER_DARK = (236, 229, 211)
INK = (22, 34, 54)
NAVY = (20, 38, 66)
NAVY_LIGHT = (38, 64, 96)
CREAM = (246, 241, 229)
GOLD = (201, 162, 39)
RED = (176, 48, 38)
RED_DARK = (140, 34, 28)
TEAL = (38, 104, 96)
SKY = (127, 179, 213)
SKY_LIGHT = (178, 214, 232)
SEA = (38, 92, 122)
SEA_DARK = (24, 64, 88)
SAND = (214, 186, 140)
GREY = (90, 98, 110)
GREY_DARK = (58, 66, 78)
WHITE = (255, 255, 255)
ORANGE = (232, 122, 44)
YELLOW = (244, 196, 66)
GREEN = (74, 124, 74)


class Canvas:
    """An RGB framebuffer with simple flat drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x + w))
        y1 = min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._idx(x0, yy)
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, color, t=2):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def disc(self, cx, cy, r, color):
        cx = int(round(cx))
        cy = int(round(cy))
        r = int(r)
        if r <= 0:
            self.set(cx, cy, color)
            return
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle(self, cx, cy, r, color):
        self.disc(cx, cy, r, color)

    def ring(self, cx, cy, r, color, t=3):
        for k in range(t):
            rr = r - k
            if rr <= 0:
                break
            cx_i = int(round(cx))
            cy_i = int(round(cy))
            for dy in range(-rr, rr + 1):
                dx = int((rr * rr - dy * dy) ** 0.5)
                self.set(cx_i - dx, cy_i + dy, color)
                self.set(cx_i + dx, cy_i + dy, color)

    def line(self, x0, y0, x1, y1, color, t=2):
        """A thick line drawn as a chain of discs: round caps, no gaps."""
        x0 = float(x0)
        y0 = float(y0)
        x1 = float(x1)
        y1 = float(y1)
        dx = x1 - x0
        dy = y1 - y0
        dist = max(abs(dx), abs(dy), 1.0)
        steps = int(dist) + 1
        r = max(1, t // 2)
        for i in range(steps + 1):
            f = i / steps
            self.disc(x0 + dx * f, y0 + dy * f, r, color)

    def polyline(self, points, color, t=2, closed=False):
        pts = list(points)
        if closed and len(pts) > 1:
            pts = pts + [pts[0]]
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], color, t)

    def polygon(self, points, color):
        """Scanline fill of a simple polygon."""
        pts = [(float(x), float(y)) for x, y in points]
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x_a, y_a = pts[i]
                x_b, y_b = pts[(i + 1) % n]
                if (y_a <= y < y_b) or (y_b <= y < y_a):
                    f = (y - y_a) / (y_b - y_a)
                    xs.append(x_a + f * (x_b - x_a))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[k]), y, int(xs[k + 1]) - int(xs[k]) + 1, 1, color)

    def vgrad(self, x, y, w, h, top, bottom):
        for yy in range(int(y), int(y + h)):
            f = (yy - y) / max(1, h - 1)
            c = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
            self.fill_rect(x, yy, w, 1, c)


def _png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------------------
# Stroke font: each glyph is a list of polylines on a 5-wide by 7-tall
# grid (x 0..4, y 0..7, y down). Lowercase is rendered as uppercase.
# ---------------------------------------------------------------------------

FONT = {
    "A": [[(0, 7), (2, 0), (4, 7)], [(1, 4.5), (3, 4.5)]],
    "B": [[(0, 0), (0, 7)], [(0, 0), (3, 0), (4, 1), (4, 3), (3, 4), (0, 4)],
          [(0, 4), (3, 4), (4, 5), (4, 6), (3, 7), (0, 7)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 6), (1, 7), (3, 7), (4, 6)]],
    "D": [[(0, 0), (0, 7)], [(0, 0), (3, 0), (4, 1), (4, 6), (3, 7), (0, 7)]],
    "E": [[(0, 0), (0, 7)], [(0, 0), (4, 0)], [(0, 3.5), (3, 3.5)], [(0, 7), (4, 7)]],
    "F": [[(0, 0), (0, 7)], [(0, 0), (4, 0)], [(0, 3.5), (3, 3.5)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 6), (1, 7), (3, 7), (4, 6), (4, 4)],
          [(4, 4), (2, 4)]],
    "H": [[(0, 0), (0, 7)], [(4, 0), (4, 7)], [(0, 3.5), (4, 3.5)]],
    "I": [[(1, 0), (3, 0)], [(2, 0), (2, 7)], [(1, 7), (3, 7)]],
    "J": [[(1, 0), (4, 0)], [(4, 0), (4, 6), (3, 7), (1, 7)]],
    "K": [[(0, 0), (0, 7)], [(4, 0), (0, 4)], [(1.5, 3), (4, 7)]],
    "L": [[(0, 0), (0, 7)], [(0, 7), (4, 7)]],
    "M": [[(0, 7), (0, 0), (2, 3.5), (4, 0), (4, 7)]],
    "N": [[(0, 7), (0, 0), (4, 7), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1), (4, 6), (3, 7), (1, 7), (0, 6), (0, 1), (1, 0)]],
    "P": [[(0, 0), (0, 7)], [(0, 0), (3, 0), (4, 1), (4, 3), (3, 4), (0, 4)]],
    "Q": [[(1, 0), (3, 0), (4, 1), (4, 6), (3, 7), (1, 7), (0, 6), (0, 1), (1, 0)],
          [(2.5, 5), (4.5, 7.5)]],
    "R": [[(0, 0), (0, 7)], [(0, 0), (3, 0), (4, 1), (4, 3), (3, 4), (0, 4)],
          [(2, 4), (4, 7)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 3), (1, 4), (3, 4), (4, 5),
           (4, 6), (3, 7), (1, 7), (0, 6)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 7)]],
    "U": [[(0, 0), (0, 6), (1, 7), (3, 7), (4, 6), (4, 0)]],
    "V": [[(0, 0), (2, 7), (4, 0)]],
    "W": [[(0, 0), (1, 7), (2, 3.5), (3, 7), (4, 0)]],
    "X": [[(0, 0), (4, 7)], [(4, 0), (0, 7)]],
    "Y": [[(0, 0), (2, 3.5), (4, 0)], [(2, 3.5), (2, 7)]],
    "Z": [[(0, 0), (4, 0), (0, 7), (4, 7)]],
    "0": [[(1, 0), (3, 0), (4, 1), (4, 6), (3, 7), (1, 7), (0, 6), (0, 1), (1, 0)]],
    "1": [[(1, 0), (2, 0), (2, 7)], [(0, 7), (4, 7)]],
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 3), (0, 7), (4, 7)]],
    "3": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 3), (3, 4)],
          [(3, 4), (4, 5), (4, 6), (3, 7), (1, 7), (0, 6)]],
    "4": [[(3, 0), (3, 7)], [(0, 0), (0, 4), (4, 4)]],
    "5": [[(4, 0), (0, 0), (0, 3), (3, 3), (4, 4), (4, 6), (3, 7), (0, 7)]],
    "6": [[(4, 1), (3, 0), (1, 0), (0, 2), (0, 6), (1, 7), (3, 7), (4, 6),
           (4, 4), (3, 3), (1, 3), (0, 4)]],
    "7": [[(0, 0), (4, 0), (2, 7)]],
    "8": [[(1, 0), (3, 0), (4, 1), (4, 3), (3, 4), (1, 4), (0, 3), (0, 1), (1, 0)],
          [(1, 4), (3, 4), (4, 5), (4, 6), (3, 7), (1, 7), (0, 6), (0, 5), (1, 4)]],
    "9": [[(0, 6), (0, 3), (1, 1), (2, 0), (3, 1), (4, 2), (4, 5), (3, 7), (1, 7)],
          [(0, 3), (3, 3)]],
    ".": [[(1.7, 6.2), (2.3, 6.2)]],
    ",": [[(1.5, 6), (2.3, 6), (2, 7), (1.4, 7.8)]],
    ":": [[(1.7, 2), (2.3, 2)], [(1.7, 5.5), (2.3, 5.5)]],
    ";": [[(1.7, 2), (2.3, 2)], [(1.5, 5.5), (2.3, 5.5), (2, 7), (1.4, 7.8)]],
    "'": [[(2, 0), (2, 2.5)]],
    "-": [[(0.5, 3.5), (3.5, 3.5)]],
    "(": [[(3, 0), (2, 1), (2, 6), (3, 7)]],
    ")": [[(1, 0), (2, 1), (2, 6), (1, 7)]],
    "/": [[(3.5, 0), (0.5, 7)]],
    "%": [[(4, 0), (0, 7)], [(0.7, 1.2), (1.5, 1.2)], [(2.7, 5.6), (3.5, 5.6)]],
    "!": [[(2, 0), (2, 5)], [(1.7, 6.2), (2.3, 6.2)]],
    "?": [[(0.8, 1.6), (1, 0.6), (3, 0.6), (3.8, 1.6), (3.8, 2.6), (2, 4), (2, 5)],
          [(1.7, 6.2), (2.3, 6.2)]],
    "+": [[(2, 1.5), (2, 5.5)], [(0.5, 3.5), (3.5, 3.5)]],
    "=": [[(0.5, 2.5), (3.5, 2.5)], [(0.5, 4.5), (3.5, 4.5)]],
    '"': [[(1, 0), (1, 2)], [(3, 0), (3, 2)]],
    "*": [[(2, 0.5), (2, 6.5)], [(0.5, 2), (3.5, 5)], [(3.5, 2), (0.5, 5)]],
}

ADV = 5.6  # advance width, in grid units


def text_width(text, s):
    """Width in pixels of text at grid scale s."""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += ADV * s
        elif ch.upper() in FONT:
            w += ADV * s
        else:
            w += ADV * s
    return w - 1.1 * s if w else 0.0


def draw_char(cv, x, y, ch, s, color, t):
    glyph = FONT.get(ch.upper())
    if glyph is None:
        return
    for poly in glyph:
        pts = [(x + px * s, y + py * s) for px, py in poly]
        cv.polyline(pts, color, t)


def draw_text(cv, x, y, text, s, color, t=None, align="left"):
    """Draw one line; y is the top of the 7-unit glyph box."""
    if t is None:
        t = max(1, int(round(s * 0.30)))
    if align == "center":
        x = x - text_width(text, s) / 2
    elif align == "right":
        x = x - text_width(text, s)
    cx = float(x)
    for ch in text:
        if ch == " ":
            cx += ADV * s
        elif ch == "\u2022":  # bullet: a solid square
            cv.fill_rect(cx + 1.4 * s, y + 2.6 * s, 1.6 * s, 1.6 * s, color)
            cx += ADV * s
        elif ch == "\u2014":  # em dash
            cv.line(cx + 0.3 * s, y + 3.5 * s, cx + 5.0 * s, y + 3.5 * s, color, t)
            cx += ADV * s
        else:
            draw_char(cv, cx, y, ch, s, color, t)
            cx += ADV * s
    return cx


def wrap(text, s, max_w):
    """Greedy word wrap; returns a list of lines fitting max_w pixels."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for wd in words:
            trial = wd if not cur else cur + " " + wd
            if text_width(trial, s) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
    return lines


def draw_para(cv, x, y, text, s, color, max_w, leading=None, t=None):
    """Draw wrapped text; returns the y just below the last line."""
    if leading is None:
        leading = int(round(9.2 * s))
    for ln in wrap(text, s, max_w):
        draw_text(cv, x, y, ln, s, color, t)
        y += leading
    return y

# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def card_frame(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 2)
    cv.fill_rect(x, y, w, 6, NAVY)


def kicker(cv, x, y, text, s=2.4, color=RED):
    draw_text(cv, x, y, text, s, color, max(1, int(round(s * 0.34))))
    cv.fill_rect(x, y + int(7.6 * s) + 3, int(text_width(text, s)), 3, GOLD)
    return y + int(7.6 * s) + 10


def headline(cv, x, y, lines, s, color=INK):
    for ln in lines:
        draw_text(cv, x, y, ln, s, color, max(2, int(round(s * 0.32))))
        y += int(round(9.4 * s))
    return y


def body(cv, x, y, text, s, max_w, color=GREY_DARK):
    return draw_para(cv, x, y, text, s, color, max_w, int(round(9.6 * s)),
                     max(1, int(round(s * 0.30))))


# ---------------------------------------------------------------------------
# Small flat illustrations, drawn with the same primitives
# ---------------------------------------------------------------------------

def draw_sea_scene(cv, x, y, w, h):
    """Two ships on a dark sea, a drone above, an explosion burst."""
    cv.fill_rect(x, y, w, h, SKY_LIGHT)
    cv.fill_rect(x, y + int(h * 0.55), w, h - int(h * 0.55), SEA)
    cv.fill_rect(x, y + int(h * 0.55), w, 3, SEA_DARK)
    # distant ship (left)
    sx, sy = x + 30, y + int(h * 0.55)
    cv.polygon([(sx, sy), (sx + 150, sy), (sx + 135, sy + 26), (sx + 15, sy + 26)],
               GREY_DARK)
    cv.fill_rect(sx + 60, sy - 26, 8, 26, GREY_DARK)
    cv.fill_rect(sx + 95, sy - 16, 6, 16, GREY_DARK)
    cv.polygon([(sx + 68, sy - 26), (sx + 96, sy - 26), (sx + 82, sy - 36)], RED)
    # near ship (right), listing after the hit
    nx, ny = x + w - 230, y + int(h * 0.55) + 6
    cv.polygon([(nx, ny), (nx + 190, ny), (nx + 172, ny + 30), (nx + 18, ny + 30)],
               INK)
    cv.fill_rect(nx + 80, ny - 34, 9, 34, INK)
    cv.fill_rect(nx + 120, ny - 22, 7, 22, INK)
    # explosion burst above the near ship
    ex, ey = nx + 95, ny - 52
    for ang in range(0, 360, 30):
        import math as _m
        r1 = 30
        dx = _m.cos(_m.radians(ang)) * r1
        dy = _m.sin(_m.radians(ang)) * r1
        cv.line(ex, ey, ex + dx, ey + dy, ORANGE, 7)
    cv.disc(ex, ey, 16, YELLOW)
    cv.disc(ex, ey, 9, ORANGE)
    # drone quadcopter
    dx0, dy0 = x + w - 90, y + 14
    cv.line(dx0 - 16, dy0 - 8, dx0 + 16, dy0 + 8, INK, 4)
    cv.line(dx0 + 16, dy0 - 8, dx0 - 16, dy0 + 8, INK, 4)
    cv.disc(dx0, dy0, 6, INK)
    cv.disc(dx0 - 18, dy0 - 10, 4, GREY)
    cv.disc(dx0 + 18, dy0 - 10, 4, GREY)
    cv.disc(dx0 - 18, dy0 + 10, 4, GREY)
    cv.disc(dx0 + 18, dy0 + 10, 4, GREY)


def draw_rocket(cv, cx, y, h):
    """A small upright rocket with a flame."""
    w = int(h * 0.42)
    x0 = cx - w // 2
    top = y
    cv.polygon([(x0, top + int(h * 0.45)), (x0 + w // 2, top),
                (x0 + w, top + int(h * 0.45))], RED)
    cv.fill_rect(x0, top + int(h * 0.45), w, int(h * 0.32), WHITE)
    cv.rect(x0, top + int(h * 0.45), w, int(h * 0.32), INK, 2)
    cv.disc(cx, top + int(h * 0.58), 7, SKY)
    cv.ring(cx, top + int(h * 0.58), 7, INK, 2)
    cv.polygon([(x0, top + int(h * 0.77)), (x0 - 14, top + h),
                (x0 + 6, top + int(h * 0.80))], RED)
    cv.polygon([(x0 + w, top + int(h * 0.77)), (x0 + w + 14, top + h),
                (x0 + w - 6, top + int(h * 0.80))], RED)
    cv.polygon([(cx - 8, top + int(h * 0.80)), (cx + 8, top + int(h * 0.80)),
                (cx, top + h + 22)], ORANGE)
    cv.polygon([(cx - 4, top + int(h * 0.80)), (cx + 4, top + int(h * 0.80)),
                (cx, top + h + 12)], YELLOW)


def draw_shop(cv, x, y, w, h):
    """A supermarket front with a striped awning."""
    cv.fill_rect(x, y + int(h * 0.30), w, int(h * 0.70), SAND)
    cv.rect(x, y + int(h * 0.30), w, int(h * 0.70), INK, 2)
    for i in range(6):
        col = RED if i % 2 == 0 else WHITE
        cv.fill_rect(x + i * (w // 6), y, w // 6 + 1, int(h * 0.34), col)
    cv.rect(x, y, w, int(h * 0.34), INK, 2)
    cv.fill_rect(x + 14, y + int(h * 0.52), 34, int(h * 0.48), NAVY)
    cv.fill_rect(x + w - 48, y + int(h * 0.52), 34, int(h * 0.48), NAVY)
    cv.fill_rect(x + w // 2 - 16, y + int(h * 0.44), 32, int(h * 0.56), INK)


def draw_islands(cv, x, y, w, h):
    """Pacific islands: green isles on blue waves."""
    cv.fill_rect(x, y, w, h, SKY_LIGHT)
    for i in range(3):
        wy = y + int(h * (0.35 + 0.22 * i))
        cv.line(x + 8, wy, x + w - 8, wy, SEA, 3)
    cv.disc(x + int(w * 0.28), y + int(h * 0.42), 22, GREEN)
    cv.disc(x + int(w * 0.30), y + int(h * 0.36), 12, GREEN)
    cv.disc(x + int(w * 0.68), y + int(h * 0.55), 17, GREEN)
    cv.disc(x + int(w * 0.66), y + int(h * 0.50), 9, GREEN)
    cv.disc(x + int(w * 0.85), y + int(h * 0.30), 11, GREEN)
    cv.disc(x + int(w * 0.28), y + int(h * 0.42), 22, GREEN)
    cv.line(x + int(w * 0.28) - 8, y + int(h * 0.42) - 26,
            x + int(w * 0.28) - 8, y + int(h * 0.42) - 6, INK, 3)
    cv.polygon([(x + int(w * 0.28) - 8, y + int(h * 0.42) - 26),
                (x + int(w * 0.28) + 10, y + int(h * 0.42) - 20),
                (x + int(w * 0.28) - 8, y + int(h * 0.42) - 14)], RED)


def draw_medal(cv, cx, y, h):
    """A gold medal on a ribbon."""
    cv.polygon([(cx - 26, y), (cx - 8, y), (cx - 2, y + int(h * 0.42)),
                (cx - 20, y + int(h * 0.42))], RED)
    cv.polygon([(cx + 26, y), (cx + 8, y), (cx + 2, y + int(h * 0.42)),
                (cx + 20, y + int(h * 0.42))], NAVY)
    cy = y + int(h * 0.66)
    cv.disc(cx, cy, 30, GOLD)
    cv.ring(cx, cy, 30, INK, 3)
    cv.ring(cx, cy, 20, INK, 2)
    draw_text(cv, cx - 8, cy - 12, "1", 3.4, INK, 2)


def draw_chip(cv, x, y, w, h):
    """A black AI chip with pins."""
    s = min(w, h)
    cx, cy = x + w // 2, y + h // 2
    side = int(s * 0.62)
    for i in range(4):
        px = cx - side // 2 + i * (side // 3)
        cv.line(px, cy - side // 2 - 12, px, cy - side // 2, INK, 4)
        cv.line(px, cy + side // 2, px, cy + side // 2 + 12, INK, 4)
        py = cy - side // 2 + i * (side // 3)
        cv.line(cx - side // 2 - 12, py, cx - side // 2, py, INK, 4)
        cv.line(cx + side // 2, py, cx + side // 2 + 12, py, INK, 4)
    cv.fill_rect(cx - side // 2, cy - side // 2, side, side, INK)
    cv.fill_rect(cx - side // 4, cy - side // 4, side // 2, side // 2, TEAL)
    draw_text(cv, cx - 10, cy - 13, "AI", 3.6, WHITE, 2)

# ---------------------------------------------------------------------------
# Composition: a newspaper front page
# ---------------------------------------------------------------------------

def compose():
    cv = Canvas(W, H, PAPER)
    # faint paper rule border
    cv.rect(10, 10, W - 20, H - 20, GOLD, 2)

    # ---- Masthead -------------------------------------------------------
    cv.fill_rect(0, 0, W, 158, NAVY)
    cv.fill_rect(0, 158, W, 4, GOLD)
    draw_text(cv, W // 2, 22, "THE WORLD IN ONE DAY", 2.6, GOLD,
              max(1, int(round(2.6 * 0.34))), align="center")
    draw_text(cv, W // 2, 52, "WEDNESDAY, 25 NOVEMBER 2026", 5.0, CREAM,
              2, align="center")
    cv.fill_rect(112, 116, W - 224, 3, GOLD)
    draw_text(cv, W // 2, 128, "UKRAINE  •  CHINA  •  COLOMBIA  •  THE PACIFIC  •  WASHINGTON",
              2.2, CREAM, 1, align="center")

    # ---- Lead story: Ukraine -------------------------------------------
    lx, ly, lw, lh = 28, 174, 608, 392
    card_frame(cv, lx, ly, lw, lh)
    y = kicker(cv, lx + 20, ly + 18, "WAR IN UKRAINE  —  LEAD STORY")
    y = headline(cv, lx + 20, y + 4, ["UKRAINE STRIKES", "RUSSIAN SHIPS IN", "TWO SEAS"],
                 4.4)
    y = body(cv, lx + 20, y + 8,
             "Zelenskiy confirms a drone hit on a Russian cargo ship in the "
             "Gulf of Finland. Kyiv also says it sank a Russian warship off "
             "Libya. Moscow calls the attacks \"terrorist acts\".",
             2.5, lw - 40)
    draw_sea_scene(cv, lx + 16, ly + lh - 96, lw - 32, 80)

    # ---- Right column ---------------------------------------------------
    rx, rw = 652, 344
    # Space: Shenzhou-24
    ax, ay, ah = rx, 174, 188
    card_frame(cv, ax, ay, rw, ah)
    y = kicker(cv, ax + 16, ay + 16, "SPACE  —  CHINA", s=2.0)
    draw_rocket(cv, ax + rw - 46, ay + 40, 44)
    y = headline(cv, ax + 16, y + 2, ["SHENZHOU-24", "LIFTS OFF"], 3.0)
    body(cv, ax + 16, y + 4,
         "China flies three to Tiangong. Pakistan's Zeeshan Ali, 40, is "
         "the first foreign visitor.",
         2.2, rw - 32)
    # Colombia: Cartagena siege
    bx, by, bh = rx, 378, 188
    card_frame(cv, bx, by, rw, bh)
    y = kicker(cv, bx + 16, by + 16, "COLOMBIA", s=2.0)
    y = headline(cv, bx + 16, y + 2, ["HOSTAGE SIEGE", "IN CARTAGENA"], 3.0)
    body(cv, bx + 16, y + 4,
         "Gunmen hold 30 people hostage in a Cartagena supermarket. Five "
         "elderly women freed.",
         2.2, rw - 32)

    # ---- Bottom row: three stories --------------------------------------
    byy, bhh, bw = 582, 314, 312
    # Pacific
    cx0 = 28
    card_frame(cv, cx0, byy, bw, bhh)
    y = kicker(cv, cx0 + 16, byy + 16, "THE PACIFIC", s=2.2)
    y = headline(cv, cx0 + 16, y + 2, ["SOLOMONS DROPS", "CHINA PACT"], 3.2)
    body(cv, cx0 + 16, y + 4,
         "Solomon Islands ends its security deal with Beijing and signs a "
         "new one with Australia.",
         2.3, bw - 32)
    draw_islands(cv, cx0 + 16, byy + bhh - 92, bw - 32, 76)
    # Washington
    cx1 = 356
    card_frame(cv, cx1, byy, bw, bhh)
    y = kicker(cv, cx1 + 16, byy + 16, "UNITED STATES", s=2.2)
    y = headline(cv, cx1 + 16, y + 2, ["MEDAL OF FREEDOM", "FOR GIULIANI"], 3.2)
    body(cv, cx1 + 16, y + 4,
         "Trump awards the top US civilian honour to Rudy Giuliani, the "
         "former New York mayor.",
         2.3, bw - 32)
    draw_medal(cv, cx1 + bw // 2, byy + bhh - 96, 84)
    # Technology / trade
    cx2 = 684
    card_frame(cv, cx2, byy, bw, bhh)
    y = kicker(cv, cx2 + 16, byy + 16, "TECHNOLOGY  —  TRADE", s=2.2)
    y = headline(cv, cx2 + 16, y + 2, ["US BLACKLISTS", "CHIP FIRM"], 3.2)
    body(cv, cx2 + 16, y + 4,
         "Washington blacklists Singapore's Megaspeed, accused of funnelling "
         "Nvidia AI chips to China.",
         2.3, bw - 32)
    draw_chip(cv, cx2 + 16, byy + bhh - 96, bw - 32, 80)

    # ---- Ticker ----------------------------------------------------------
    cv.fill_rect(28, 912, 968, 48, RED)
    draw_text(cv, 44, 920,
              "ALSO TODAY:  O'HARE RADAR OUTAGE DELAYS FLIGHTS  •  SOUTH KOREA",
              2.2, CREAM, 1)
    draw_text(cv, 44, 940,
              "EDUCATION MINISTER QUITS OVER EXAM CHEATING  •  NATO VOWS SPACE DEFENCE",
              2.2, CREAM, 1)

    # ---- Footer ----------------------------------------------------------
    draw_text(cv, W // 2, 974,
              "SUMMARY OF STORIES FIRST REPORTED ON 25 NOVEMBER 2026",
              2.0, INK, 1, align="center")
    draw_text(cv, W // 2, 994, "SOURCES: REUTERS, AP, XINHUA",
              2.0, GREY, 1, align="center")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(compose(), path)
    print(f"wrote {path} ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
