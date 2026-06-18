#!/usr/bin/env python3
# Builds the v3 "Game Pack": authentic pokered art + map + collision + a GRASS
# map (so wild encounters only happen in tall grass, like the real game) + wild
# creature sprites. One JS file the browser game and the audit both read.
#   python3 build_pack.py
import os, io, base64, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.normpath(os.path.join(HERE, "..", "..", "pokered"))
PACK_DIR = os.path.join(HERE, "..", "pack")
os.makedirs(PACK_DIR, exist_ok=True)

TILE, BLOCK = 8, 4
# Softer, natural Game-Boy green (lightest -> darkest). Nicer than harsh lime.
GB = {255: (224, 248, 208), 170: (136, 192, 112), 85: (52, 104, 86), 0: (8, 40, 48)}
# warm palette for wild creatures so they stand out against the green
CRE = {255: (255, 246, 224), 170: (214, 158, 110), 85: (120, 78, 56), 0: (40, 24, 20)}

MAP_NAME, TILESET, W, H = "Route1", "overworld", 10, 18
GRASS_TILE = 0x52   # overworld tall-grass tile (pokered): encounters only here
WALKABLE = {0x00, 0x10, 0x1b, 0x20, 0x21, 0x23, 0x2c, 0x2d, 0x2e,
            0x30, 0x31, 0x33, 0x39, 0x3c, 0x3e, 0x52, 0x54, 0x58, 0x5b}


def data_url(img):
    buf = io.BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def colorize(gray, pal, transparent_light=False):
    mode = "RGBA" if transparent_light else "RGB"
    out = Image.new(mode, gray.size); s = gray.load(); d = out.load()
    for y in range(gray.height):
        for x in range(gray.width):
            v = s[x, y]
            if transparent_light and v == 255: d[x, y] = (0, 0, 0, 0)
            else: d[x, y] = (pal.get(v, pal[0]) + ((255,) if transparent_light else ()))
    return out


def main():
    tileset = Image.open(os.path.join(PK, "gfx", "tilesets", TILESET + ".png")).convert("L")
    per = tileset.width // TILE
    bst = open(os.path.join(PK, "gfx", "blocksets", TILESET + ".bst"), "rb").read()
    blocks = [list(bst[i:i + 16]) for i in range(0, len(bst), 16)]
    blk = list(open(os.path.join(PK, "maps", MAP_NAME + ".blk"), "rb").read())

    tw, th = W * BLOCK, H * BLOCK
    tilegrid = [[0] * tw for _ in range(th)]
    for my in range(H):
        for mx in range(W):
            bt = blocks[blk[my * W + mx]]
            for ty in range(BLOCK):
                for tx in range(BLOCK):
                    tilegrid[my * BLOCK + ty][mx * BLOCK + tx] = bt[ty * BLOCK + tx]

    cw, ch = W * 2, H * 2
    walk = [[0] * cw for _ in range(ch)]
    grass = [[0] * cw for _ in range(ch)]
    for cy in range(ch):
        for cx in range(cw):
            feet = tilegrid[cy * 2 + 1][cx * 2]
            walk[cy][cx] = 1 if feet in WALKABLE else 0
            grass[cy][cx] = 1 if feet == GRASS_TILE else 0

    # Start inside the largest connected walkable region that CONTAINS grass, so
    # the player can always walk to a battle. (Our derived collision can wrongly
    # wall off small pockets; this guarantees a playable, grass-reachable area.)
    comp = [[-1] * cw for _ in range(ch)]
    best_id, best_grass, best_cells = -1, -1, None
    cid = 0
    for sy0 in range(ch):
        for sx0 in range(cw):
            if walk[sy0][sx0] and comp[sy0][sx0] == -1:
                stack = [(sx0, sy0)]; comp[sy0][sx0] = cid; cells = []; gc = 0
                while stack:
                    x, y = stack.pop(); cells.append((x, y)); gc += grass[y][x]
                    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < cw and 0 <= ny < ch and walk[ny][nx] and comp[ny][nx] == -1:
                            comp[ny][nx] = cid; stack.append((nx, ny))
                if gc > best_grass or (gc == best_grass and len(cells) > (len(best_cells) if best_cells else 0)):
                    best_id, best_grass, best_cells = cid, gc, cells
                cid += 1
    start = None
    for (x, y) in (best_cells or []):
        if not grass[y][x]: start = [x, y]; break        # prefer a non-grass tile to stand on
    if start is None and best_cells: start = list(best_cells[0])
    if start is None: start = [PACK_FALLBACK := 0, 0]
    # mask walk/grass to ONLY the playable region, so the player can't reach the
    # disconnected pockets (which would look like invisible walls everywhere)
    for y in range(ch):
        for x in range(cw):
            if comp[y][x] != best_id:
                walk[y][x] = 0; grass[y][x] = 0

    sprite = Image.open(os.path.join(PK, "gfx", "sprites", "red.png")).convert("L")
    creatures = {}
    for name in ("rattata", "pidgey"):
        p = os.path.join(PK, "gfx", "pokemon", "front", name + ".png")
        if os.path.exists(p):
            creatures[name] = data_url(colorize(Image.open(p).convert("L"), CRE, True))

    pack = {
        "name": MAP_NAME, "w": W, "h": H, "cw": cw, "ch": ch, "tile": TILE, "block": BLOCK,
        "tilesPerRow": per, "blocks": blocks, "map": blk, "walk": walk, "grass": grass,
        "start": start, "encounterRate": 0.18,
        "tilesetURL": data_url(colorize(tileset, GB)),
        "spriteURL": data_url(colorize(sprite, GB, True)),
        "creatures": creatures, "creatureNames": list(creatures.keys()),
    }
    js = "// AUTO-GENERATED Game Pack (real pokered art + map + grass). Do not edit by hand.\n"
    js += "export const PACK = " + json.dumps(pack, separators=(",", ":")) + ";\n"
    open(os.path.join(PACK_DIR, "pallet.pack.js"), "w", encoding="utf-8").write(js)
    g = sum(sum(r) for r in grass)
    print("wrote pack/pallet.pack.js  map %s %dx%d  grass cells %d  start %s  creatures %s"
          % (MAP_NAME, W, H, g, start, list(creatures)))


if __name__ == "__main__":
    main()
