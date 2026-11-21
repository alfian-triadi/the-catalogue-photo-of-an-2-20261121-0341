#!/usr/bin/env python3
"""The Anti-Gravity Toaster — catalogue photo of an impossible gadget.

Pure stdlib. Deterministic. Writes entry.png (1024x1024) to
$MAKEFUN_OUTPUT_DIR or /output. No network, no randomness, no time.
"""
import os, struct, zlib

W = H = 1024

# ---------- canvas ----------
# framebuffer: bytearray RGB
buf = bytearray(W * H * 3)


def set_px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r; buf[i + 1] = g; buf[i + 2] = b


def blend_px(x, y, r, g, b, a):
    """Blend colour over existing pixel, a in 0..255."""
    if 0 <= x < W and 0 <= y < H and a > 0:
        i = (y * W + x) * 3
        inv = 255 - a
        buf[i] = (r * a + buf[i] * inv) // 255
        buf[i + 1] = (g * a + buf[i + 1] * inv) // 255
        buf[i + 2] = (b * a + buf[i + 2] * inv) // 255


def fill_rect(x0, y0, x1, y1, col):
    r, g, b = col
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(W, x1); y1 = min(H, y1)
    for y in range(y0, y1):
        base = y * W * 3
        for x in range(x0, x1):
            i = base + x * 3
            buf[i] = r; buf[i + 1] = g; buf[i + 2] = b


def blend_rect(x0, y0, x1, y1, col, a):
    r, g, b = col
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(W, x1); y1 = min(H, y1)
    for y in range(y0, y1):
        for x in range(x0, x1):
            blend_px(x, y, r, g, b, a)


def hline(x0, x1, y, col):
    r, g, b = col
    if 0 <= y < H:
        x0 = max(0, x0); x1 = min(W, x1)
        base = y * W * 3
        for x in range(x0, x1):
            i = base + x * 3
            buf[i] = r; buf[i + 1] = g; buf[i + 2] = b


def ellipse_fill(cx, cy, rx, ry, col, a=255):
    r, g, b = col
    for y in range(max(0, cy - ry), min(H, cy + ry + 1)):
        dy = (y - cy) / ry
        rem = 1.0 - dy * dy
        if rem < 0:
            continue
        dx = int(rx * (rem ** 0.5))
        for x in range(max(0, cx - dx), min(W, cx + dx + 1)):
            if a == 255:
                set_px(x, y, r, g, b)
            else:
                blend_px(x, y, r, g, b, a)


def poly_fill(pts, col):
    """Scanline fill of a convex/concave polygon (even-odd)."""
    r, g, b = col
    ys = [p[1] for p in pts]
    y0, y1 = max(0, min(ys)), min(H - 1, max(ys))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1p = pts[i]
            x2, y2p = pts[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa, xb = int(xs[k]), int(xs[k + 1])
            for x in range(max(0, xa), min(W, xb + 1)):
                set_px(x, y, r, g, b)


def rrect(x0, y0, x1, y1, rad, col):
    """Rounded rect via scanlines: rect body + corner ellipses."""
    fill_rect(x0, y0 + rad, x1, y1 - rad, col)
    fill_rect(x0 + rad, y0, x1 - rad, y0 + rad, col)
    fill_rect(x0 + rad, y1 - rad, x1 - rad, y1, col)
    ellipse_fill(x0 + rad, y0 + rad, rad, rad, col)
    ellipse_fill(x1 - rad, y0 + rad, rad, rad, col)
    ellipse_fill(x0 + rad, y1 - rad, rad, rad, col)
    ellipse_fill(x1 - rad, y1 - rad, rad, rad, col)


def vgrad_rect(x0, y0, x1, y1, top, bot):
    """Vertical gradient rect, per-row colour."""
    for y in range(max(0, y0), min(H, y1)):
        t = (y - y0) / max(1, (y1 - y0 - 1))
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        hline(x0, x1, y, (r, g, b))


# ---------- 5x7 bitmap font ----------
FONT = {
    'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    'V': ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    'I': ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'G': ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    '-': ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    '1': ["00100", "01100", "00100", "00100", "00100", "00100", "11111"],
    '.': ["00000", "00000", "00000", "00000", "00000", "00000", "00100"],
}


def draw_text(s, cx, y, scale, col):
    gw = 5 * scale + scale  # glyph + gap
    total = len(s) * gw - scale
    x = cx - total // 2
    for ch in s:
        g = FONT.get(ch)
        if g:
            for row in range(7):
                for c in range(5):
                    if g[row][c] == '1':
                        fill_rect(x + c * scale, y + row * scale,
                                  x + (c + 1) * scale, y + (row + 1) * scale, col)
        x += gw


# ---------- scene ----------
def main():
    # 1. background gradient #f5f2ed -> #dcd7cf, floor darker below y=800
    for y in range(H):
        if y < 800:
            t = y / 799.0
            r = int(245 + (220 - 245) * t)
            g = int(242 + (215 - 242) * t)
            b = int(237 + (207 - 237) * t)
        else:
            t = (y - 800) / 223.0
            r = int(220 + (210 - 220) * t)
            g = int(215 + (205 - 215) * t)
            b = int(207 + (196 - 207) * t)
        hline(0, W, y, (r, g, b))
    hline(0, W, 800, (198, 192, 183))
    hline(0, W, 801, (198, 192, 183))

    # 2. soft shadow ellipse (blurred via small mask)
    # build mask at 1/4 scale
    sw, sh = 256, 256
    mask = bytearray(sw * sh)
    scx, scy, srx, sry = 128, 203, 75, 9
    for yy in range(sh):
        dy = (yy - scy) / sry
        if abs(dy) > 1:
            continue
        dx = int(srx * ((1 - dy * dy) ** 0.5))
        for xx in range(max(0, scx - dx), min(sw, scx + dx + 1)):
            mask[yy * sw + xx] = 110
    # box blur radius 3 on mask (2 passes)
    for _ in range(2):
        tmp = bytearray(sw * sh)
        for yy in range(sh):
            for xx in range(sw):
                s = 0; n = 0
                for dy in (-3, 0, 3):
                    y2 = yy + dy
                    if 0 <= y2 < sh:
                        for dx in (-3, 0, 3):
                            x2 = xx + dx
                            if 0 <= x2 < sw:
                                s += mask[y2 * sw + x2]; n += 1
                tmp[yy * sw + xx] = s // max(1, n)
        mask = tmp
    # upsample bilinear into bbox (212..812, 778..846)
    for y in range(778, 847):
        fy = (y - 778) / 68.0 * (sh - 1)
        y0i = int(fy); y1i = min(sh - 1, y0i + 1); ty = fy - y0i
        for x in range(212, 813):
            fx = (x - 212) / 600.0 * (sw - 1)
            x0i = int(fx); x1i = min(sw - 1, x0i + 1); tx = fx - x0i
            v = (mask[y0i * sw + x0i] * (1 - tx) * (1 - ty)
                 + mask[y0i * sw + x1i] * tx * (1 - ty)
                 + mask[y1i * sw + x0i] * (1 - tx) * ty
                 + mask[y1i * sw + x1i] * tx * ty)
            a = int(v)
            if a > 0:
                blend_px(x, y, 40, 36, 32, a)

    # 3. plate + butter (one accessory, bottom right)
    ellipse_fill(770, 845, 95, 26, (251, 250, 247))
    ellipse_fill(770, 843, 88, 22, (250, 249, 246))
    # butter pat: small rounded slab
    rrect(730, 822, 812, 838, 6, (246, 223, 142))
    rrect(734, 818, 808, 826, 4, (250, 231, 160))
    # plate rim shadow
    for x in range(680, 861):
        blend_px(x, 868, 60, 55, 50, 18)

    # 4. toast slices (floating, rotated polygons)
    def toast(cx, cy, angle_deg, w=110, h=130):
        import math
        a = math.radians(angle_deg)
        ca, sa = math.cos(a), math.sin(a)

        def rot(px, py):
            return (cx + px * ca - py * sa, cy + px * sa + py * ca)
        hw, hh = w / 2, h / 2
        # crust polygon (slightly domed top via 6 points)
        pts = [rot(-hw, -hh + 18), rot(-hw + 14, -hh), rot(hw - 14, -hh),
               rot(hw, -hh + 18), rot(hw, hh), rot(-hw, hh)]
        pts = [(int(x), int(y)) for x, y in pts]
        poly_fill(pts, (201, 138, 70))
        # crumb inner polygon
        pts2 = [rot(-hw + 11, -hh + 26), rot(-hw + 22, -hh + 10),
                rot(hw - 22, -hh + 10), rot(hw - 11, -hh + 26),
                rot(hw - 11, hh - 11), rot(-hw + 11, hh - 11)]
        pts2 = [(int(x), int(y)) for x, y in pts2]
        poly_fill(pts2, (242, 212, 155))
        # highlight
        pts3 = [rot(-hw + 20, -hh + 22), rot(-hw + 30, -hh + 14),
                rot(hw - 30, -hh + 14), rot(hw - 22, -hh + 24)]
        pts3 = [(int(x), int(y)) for x, y in pts3]
        poly_fill(pts3, (250, 226, 178))
    toast(410, 400, -10)
    toast(614, 395, 9)

    # 5. toaster body (floating: gap between body bottom 760 and shadow ~812)
    # chrome vertical gradient via scanline rows clipped to rounded rect:
    # draw gradient rect then cut corners by repainting bg? simpler: draw
    # gradient as rows, then overlay corner background using corner masks.
    for y in range(470, 761):
        t = (y - 470) / 290.0
        if t < 0.5:
            tt = t / 0.5
            r = int(236 + (201 - 236) * tt); g = int(238 + (204 - 238) * tt)
            b = int(241 + (210 - 241) * tt)
        else:
            tt = (t - 0.5) / 0.5
            r = int(201 + (154 - 201) * tt); g = int(204 + (160 - 204) * tt)
            b = int(210 + (168 - 210) * tt)
        # rounded ends: shrink row near top/bottom
        rad = 46
        if y < 470 + rad:
            dy = (470 + rad - y) / rad
            inset = int(rad * (1 - (1 - dy * dy) ** 0.5))
        elif y > 760 - rad:
            dy = (y - (760 - rad)) / rad
            inset = int(rad * (1 - (1 - dy * dy) ** 0.5))
        else:
            inset = 0
        hline(282 + inset, 742 - inset, y, (r, g, b))
    # brushed lines: faint vertical strips
    for x in range(300, 730, 7):
        blend_rect(x, 510, x + 1, 750, (255, 255, 255), 10)
        blend_rect(x + 3, 510, x + 4, 750, (120, 125, 135), 8)
    # bottom edge shade
    blend_rect(282, 748, 742, 761, (90, 95, 105), 60)
    # top dark panel
    rrect(282, 470, 742, 502, 46, (58, 60, 64))
    # chrome top highlight + levitation glow under the body
    for y in range(504, 510):
        blend_rect(300, y, 724, y + 1, (255, 255, 255), 55 - (y - 504) * 8)
    ellipse_fill(512, 776, 220, 14, (255, 255, 255), 22)
    # slots
    rrect(350, 478, 470, 496, 8, (42, 44, 47))
    rrect(554, 478, 674, 496, 8, (42, 44, 47))
    # slot inner highlight
    hline(352, 468, 494, (70, 72, 76))
    hline(556, 672, 494, (70, 72, 76))

    # lever on right side
    rrect(742, 640, 762, 682, 6, (70, 72, 78))
    rrect(742, 640, 762, 652, 6, (95, 98, 104))

    # brand text LEVITRON
    draw_text("LEVITRON", 512, 596, 3, (51, 54, 59))
    # small text AG-1 bottom right of face
    draw_text("AG-1", 690, 726, 2, (90, 94, 100))

    # dial at (400,690) r26
    ellipse_fill(400, 690, 27, 27, (40, 42, 46))
    ellipse_fill(400, 690, 24, 24, (226, 228, 232))
    import math
    for k in range(9):
        ang = math.radians(-135 + k * 33.75)
        x1 = int(400 + 19 * math.cos(ang)); y1 = int(690 + 19 * math.sin(ang))
        x2 = int(400 + 23 * math.cos(ang)); y2 = int(690 + 23 * math.sin(ang))
        # short tick line
        steps = 6
        for s in range(steps + 1):
            t = s / steps
            set_px(int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t), 60, 62, 66)
    # needle pointing up-right
    na = math.radians(-50)
    for s in range(19):
        t = s / 18.0
        set_px(int(400 + 18 * math.cos(na) * t), int(690 + 18 * math.sin(na) * t), 200, 40, 40)
    ellipse_fill(400, 690, 4, 4, (60, 62, 66))

    # LED red at (610,690) with glow
    ellipse_fill(610, 690, 14, 14, (220, 60, 50), 40)
    ellipse_fill(610, 690, 8, 8, (220, 60, 50), 90)
    ellipse_fill(610, 690, 5, 5, (235, 70, 60))

    # 6. vignette (darken corners slightly) — per-pixel once over full canvas
    cx, cy = 512, 512
    for y in range(H):
        dy = (y - cy) / 512.0
        for x in range(W):
            dx = (x - cx) / 512.0
            d2 = dx * dx + dy * dy
            if d2 > 0.85:
                a = int(min(38, (d2 - 0.85) * 120))
                i = (y * W + x) * 3
                buf[i] = buf[i] * (255 - a) // 255
                buf[i + 1] = buf[i + 1] * (255 - a) // 255
                buf[i + 2] = buf[i + 2] * (255 - a) // 255

    # ---------- PNG write ----------
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter None
        raw += buf[y * W * 3:(y + 1) * W * 3]

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return c

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print(f"wrote {path} {len(png)} bytes")


if __name__ == "__main__":
    main()
