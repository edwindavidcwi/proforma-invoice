#!/usr/bin/env python3
# Generates the app logo/icon for Pokemon Quiz -- an ORIGINAL, kid-friendly mark
# (a graduation cap + a star, in the game's blue/purple/gold palette). No
# copyrighted Pokemon artwork is used. Outputs:
#   build/icon.ico   -- multi-size Windows icon (16..256)
#   build/logo.png   -- 512px logo for reuse (PWA, store art, the guide, etc.)
#
# Run:  python3 make_icon.py
import math, os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)

SS = 1024              # supersampled master; downscaled for crisp anti-aliasing
BLUE = (37, 99, 235)   # top of background gradient
PURP = (109, 40, 217)  # bottom of background gradient
GOLD = (255, 203, 5)   # brand yellow (tassel, star)
GOLD_D = (214, 158, 0)
WHITE = (255, 255, 255)
SHADE = (228, 232, 240)  # soft grey for the cap's underside (depth)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def star_points(cx, cy, outer, inner, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = outer if i % 2 == 0 else inner
        a = math.radians(rot + i * 180.0 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def make_master():
    S = SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # --- rounded-square background with a vertical gradient ---
    grad = Image.new("RGBA", (S, S))
    gp = grad.load()
    for y in range(S):
        c = lerp(BLUE, PURP, y / (S - 1))
        for x in range(S):
            gp[x, y] = (c[0], c[1], c[2], 255)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    pad = int(S * 0.045)
    md.rounded_rectangle([pad, pad, S - pad, S - pad], radius=int(S * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)

    # a soft top highlight for a friendly, glossy feel
    gloss = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse([int(S * 0.08), int(-S * 0.32), int(S * 0.92), int(S * 0.34)],
               fill=(255, 255, 255, 38))
    gloss = gloss.filter(ImageFilter.GaussianBlur(S * 0.02))
    img = Image.alpha_composite(img, Image.composite(
        gloss, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask))

    d = ImageDraw.Draw(img)
    cx = S / 2
    cy = S * 0.435            # cap sits a touch above centre
    bw, bh = S * 0.60, S * 0.30   # mortarboard (diamond) width/height

    # soft drop shadow under the whole cap
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.polygon([(cx, cy - bh / 2 + S * 0.03), (cx + bw / 2, cy + S * 0.03),
                (cx, cy + bh / 2 + S * 0.03), (cx - bw / 2, cy + S * 0.03)],
               fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.02))
    img = Image.alpha_composite(img, shadow)
    d = ImageDraw.Draw(img)

    # --- cap base (the part over the head): a rounded trapezoid, slightly grey ---
    cap_top = cy + S * 0.012
    d.polygon([(cx - S * 0.155, cap_top), (cx + S * 0.155, cap_top),
               (cx + S * 0.205, cy + S * 0.165), (cx - S * 0.205, cy + S * 0.165)],
              fill=SHADE)
    d.ellipse([cx - S * 0.205, cy + S * 0.135, cx + S * 0.205, cy + S * 0.195], fill=SHADE)

    # --- mortarboard (flat top) as a white diamond ---
    diamond = [(cx, cy - bh / 2), (cx + bw / 2, cy), (cx, cy + bh / 2), (cx - bw / 2, cy)]
    d.polygon(diamond, fill=WHITE)

    # centre button
    br = S * 0.022
    d.ellipse([cx - br, cy - br, cx + br, cy + br], fill=GOLD)

    # --- tassel: cord from the button to the right tip, then hanging down ---
    tip = (cx + bw / 2, cy)
    hang_y = cy + S * 0.20
    lw = max(2, int(S * 0.014))
    d.line([(cx, cy), tip], fill=GOLD, width=lw)
    d.line([tip, (tip[0], hang_y)], fill=GOLD, width=lw)
    # the tassel fringe (a little gold bell + strands)
    d.ellipse([tip[0] - S * 0.028, hang_y - S * 0.01, tip[0] + S * 0.028, hang_y + S * 0.05], fill=GOLD)
    for off in (-0.022, -0.008, 0.008, 0.022):
        d.line([(tip[0] + S * off, hang_y + S * 0.03), (tip[0] + S * off, hang_y + S * 0.085)],
               fill=GOLD_D, width=max(2, int(S * 0.006)))

    # --- gold star badge, lower-right, for a fun "reward" pop ---
    scx, scy, so = S * 0.735, S * 0.735, S * 0.135
    d.polygon(star_points(scx, scy, so * 1.16, so * 0.49), fill=WHITE)      # white halo
    d.polygon(star_points(scx, scy, so, so * 0.42), fill=GOLD)
    d.polygon(star_points(scx, scy, so * 0.62, so * 0.26), fill=GOLD_D)     # subtle inner depth

    return img


def main():
    master = make_master().resize((256, 256), Image.LANCZOS)
    ico = os.path.join(OUT, "icon.ico")
    master.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                            (64, 64), (128, 128), (256, 256)])
    png = os.path.join(OUT, "logo.png")
    make_master().resize((512, 512), Image.LANCZOS).save(png)
    # runtime window/taskbar icon, bundled with the app (assets/** ships in the build)
    win_png = os.path.join(HERE, "assets", "icon.png")
    os.makedirs(os.path.dirname(win_png), exist_ok=True)
    master.save(win_png)
    print("wrote", ico, ",", png, "and", win_png)


if __name__ == "__main__":
    main()
