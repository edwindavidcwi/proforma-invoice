#!/usr/bin/env python3
# Builds a "Game Pack" for the v3 engine: the real Pokemon Red town art + map +
# where-you-can-walk data, bundled into one JS file the browser game and the
# audit both read. Uses the authentic pokered assets (so it looks exactly right).
#
#   python3 build_pack.py
import os, io, base64, re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.normpath(os.path.join(HERE, "..", "..", "pokered"))
PACK_DIR = os.path.join(HERE, "..", "pack")
os.makedirs(PACK_DIR, exist_ok=True)

TILE = 8
BLOCK = 4                      # a map block is 4x4 tiles (32x32 px)
# Classic Game Boy green (lightest -> darkest grey). Swappable later.
GB = {255: (155, 188, 15), 170: (139, 172, 15), 85: (48, 98, 48), 0: (15, 56, 15)}

MAP_NAME, TILESET, W, H = "PalletTown", "overworld", 10, 9
# Overworld walkable tile ids (from pokered data/tilesets/collision_tile_ids.asm)
WALKABLE = {0x00, 0x10, 0x1b, 0x20, 0x21, 0x23, 0x2c, 0x2d, 0x2e,
            0x30, 0x31, 0x33, 0x39, 0x3c, 0x3e, 0x52, 0x54, 0x58, 0x5b}


def data_url(img):
    buf = io.BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def colorize_rgb(gray):
    out = Image.new("RGB", gray.size); s = gray.load(); d = out.load()
    for y in range(gray.height):
        for x in range(gray.width):
            d[x, y] = GB.get(s[x, y], (155, 188, 15))
    return out


def colorize_rgba(gray):  # for the player sprite: lightest grey -> transparent
    out = Image.new("RGBA", gray.size); s = gray.load(); d = out.load()
    for y in range(gray.height):
        for x in range(gray.width):
            v = s[x, y]
            d[x, y] = (0, 0, 0, 0) if v == 255 else GB.get(v, (15, 56, 15)) + (255,)
    return out


def main():
    tileset = Image.open(os.path.join(PK, "gfx", "tilesets", TILESET + ".png")).convert("L")
    tiles_per_row = tileset.width // TILE
    bst = open(os.path.join(PK, "gfx", "blocksets", TILESET + ".bst"), "rb").read()
    blocks = [list(bst[i:i + 16]) for i in range(0, len(bst), 16)]
    blk = list(open(os.path.join(PK, "maps", MAP_NAME + ".blk"), "rb").read())

    # 8px-tile id grid for the whole map (used to derive collision)
    tw, th = W * BLOCK, H * BLOCK
    tilegrid = [[0] * tw for _ in range(th)]
    for my in range(H):
        for mx in range(W):
            bt = blocks[blk[my * W + mx]]
            for ty in range(BLOCK):
                for tx in range(BLOCK):
                    tilegrid[my * BLOCK + ty][mx * BLOCK + tx] = bt[ty * BLOCK + tx]

    # collision grid in 16px cells (each map step). A cell is walkable if the
    # tile at the player's feet (bottom-left 8px tile of the cell) is walkable.
    cw, ch = W * 2, H * 2
    walk = [[0] * cw for _ in range(ch)]
    for cy in range(ch):
        for cx in range(cw):
            walk[cy][cx] = 1 if tilegrid[cy * 2 + 1][cx * 2] in WALKABLE else 0

    # a sensible start: the walkable cell nearest the town centre
    start = None
    for r in range(0, max(cw, ch)):
        for cy in range(max(0, ch // 2 - r), min(ch, ch // 2 + r + 1)):
            for cx in range(max(0, cw // 2 - r), min(cw, cw // 2 + r + 1)):
                if walk[cy][cx]:
                    start = [cx, cy]; break
            if start: break
        if start: break

    tileset_rgb = colorize_rgb(tileset)
    sprite = Image.open(os.path.join(PK, "gfx", "sprites", "red.png")).convert("L")
    sprite_rgba = colorize_rgba(sprite)

    pack = {
        "name": MAP_NAME, "w": W, "h": H, "cw": cw, "ch": ch, "tile": TILE, "block": BLOCK,
        "tilesPerRow": tiles_per_row, "blocks": blocks, "map": blk, "walk": walk,
        "start": start, "palette": list(GB.values()),
        "tilesetURL": data_url(tileset_rgb), "spriteURL": data_url(sprite_rgba),
        "spriteFrameW": 16, "spriteFrameH": 16,
    }
    import json
    js = "// AUTO-GENERATED Game Pack (real pokered art + map). Do not edit by hand.\n"
    js += "export const PACK = " + json.dumps(pack, separators=(",", ":")) + ";\n"
    out = os.path.join(PACK_DIR, "pallet.pack.js")
    open(out, "w", encoding="utf-8").write(js)
    print("wrote", out, "(%.0f KB)" % (len(js) / 1024), "start", start)


if __name__ == "__main__":
    main()
