#!/usr/bin/env python3
# Builds the v3 "Game Pack": authentic pokered art + map + collision + grass +
# one-way LEDGES + creature sprites (wild + the player's own). One JS file the
# browser game and the audit both read.   python3 build_pack.py
import os, io, base64, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.normpath(os.path.join(HERE, "..", "..", "pokered"))
PACK_DIR = os.path.join(HERE, "..", "pack")
os.makedirs(PACK_DIR, exist_ok=True)

TILE, BLOCK = 8, 4
GB = {255: (224, 248, 208), 170: (136, 192, 112), 85: (52, 104, 86), 0: (8, 40, 48)}
CRE = {255: (255, 246, 224), 170: (214, 158, 110), 85: (120, 78, 56), 0: (40, 24, 20)}
MAP_NAME, TILESET, W, H = "Route1", "overworld", 10, 18
GRASS_TILE = 0x52
WALKABLE = {0x00, 0x10, 0x1b, 0x20, 0x21, 0x23, 0x2c, 0x2d, 0x2e, 0x30, 0x31, 0x33, 0x39, 0x3c, 0x3e, 0x52, 0x54, 0x58, 0x5b}
LEDGE_D, LEDGE_L, LEDGE_R = {0x36, 0x37}, {0x27}, {0x0d, 0x1d}   # one-way ledge tiles

def data_url(img):
    buf = io.BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def colorize(gray, pal, t=False):
    out = Image.new("RGBA" if t else "RGB", gray.size); s = gray.load(); d = out.load()
    for y in range(gray.height):
        for x in range(gray.width):
            v = s[x, y]
            d[x, y] = (0, 0, 0, 0) if (t and v == 255) else (pal.get(v, pal[0]) + ((255,) if t else ()))
    return out

def front(name): return os.path.join(PK, "gfx", "pokemon", "front", name + ".png")

def main():
    ts = Image.open(os.path.join(PK, "gfx", "tilesets", TILESET + ".png")).convert("L"); per = ts.width // TILE
    bst = open(os.path.join(PK, "gfx", "blocksets", TILESET + ".bst"), "rb").read()
    blocks = [list(bst[i:i + 16]) for i in range(0, len(bst), 16)]
    blk = list(open(os.path.join(PK, "maps", MAP_NAME + ".blk"), "rb").read())

    tw, th = W * BLOCK, H * BLOCK
    tg = [[0] * tw for _ in range(th)]
    for my in range(H):
        for mx in range(W):
            bt = blocks[blk[my * W + mx]]
            for ty in range(BLOCK):
                for tx in range(BLOCK):
                    tg[my * BLOCK + ty][mx * BLOCK + tx] = bt[ty * BLOCK + tx]

    cw, ch = W * 2, H * 2
    walk = [[0] * cw for _ in range(ch)]; grass = [[0] * cw for _ in range(ch)]; ledge = [[0] * cw for _ in range(ch)]
    for cy in range(ch):
        for cx in range(cw):
            feet = tg[cy * 2 + 1][cx * 2]
            walk[cy][cx] = 1 if feet in WALKABLE else 0
            grass[cy][cx] = 1 if feet == GRASS_TILE else 0
            ledge[cy][cx] = 1 if feet in LEDGE_D else 2 if feet in LEDGE_L else 3 if feet in LEDGE_R else 0

    # connectivity INCLUDING one-way ledge hops, so ledge-separated areas count
    LH = {1: (0, 1), 2: (-1, 0), 3: (1, 0)}      # ledge code -> hop direction
    def neighbors(x, y):
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < cw and 0 <= ny < ch and walk[ny][nx]: yield nx, ny
            elif 0 <= nx < cw and 0 <= ny < ch and ledge[ny][nx] and LH[ledge[ny][nx]] == (dx, dy):
                lx, ly = nx + dx, ny + dy                # land beyond the ledge
                if 0 <= lx < cw and 0 <= ly < ch and walk[ly][lx]: yield lx, ly
    comp = [[-1] * cw for _ in range(ch)]; best = (-1, -1, None); cid = 0
    for y0 in range(ch):
        for x0 in range(cw):
            if walk[y0][x0] and comp[y0][x0] == -1:
                st = [(x0, y0)]; comp[y0][x0] = cid; cells = []; gc = 0
                while st:
                    x, y = st.pop(); cells.append((x, y)); gc += grass[y][x]
                    for nx, ny in neighbors(x, y):
                        if comp[ny][nx] == -1: comp[ny][nx] = cid; st.append((nx, ny))
                if (gc, len(cells)) > (best[1], len(best[2]) if best[2] else 0): best = (cid, gc, cells)
                cid += 1
    bid, _, bcells = best
    start = next(([x, y] for (x, y) in (bcells or []) if not grass[y][x]), list(bcells[0]) if bcells else [0, 0])
    for y in range(ch):
        for x in range(cw):
            if comp[y][x] != bid: walk[y][x] = 0; grass[y][x] = 0   # hide unreachable pockets

    sprite = Image.open(os.path.join(PK, "gfx", "sprites", "red.png")).convert("L")
    creatures = {n: data_url(colorize(Image.open(front(n)).convert("L"), CRE, True)) for n in ("rattata", "pidgey") if os.path.exists(front(n))}
    player_cre = data_url(colorize(Image.open(front("charmander")).convert("L"), CRE, True)) if os.path.exists(front("charmander")) else list(creatures.values())[0]

    pack = {"name": MAP_NAME, "w": W, "h": H, "cw": cw, "ch": ch, "tile": TILE, "block": BLOCK,
            "tilesPerRow": per, "blocks": blocks, "map": blk, "walk": walk, "grass": grass, "ledge": ledge,
            "start": start, "encounterRate": 0.18,
            "tilesetURL": data_url(colorize(ts, GB)), "spriteURL": data_url(colorize(sprite, GB, True)),
            "creatures": creatures, "creatureNames": list(creatures.keys()),
            "playerCreature": "Charmander", "playerCreatureURL": player_cre}
    open(os.path.join(PACK_DIR, "pallet.pack.js"), "w", encoding="utf-8").write(
        "// AUTO-GENERATED Game Pack. Do not edit by hand.\nexport const PACK = " + json.dumps(pack, separators=(",", ":")) + ";\n")
    print("map %s %dx%d  grass %d  ledges %d  start %s  creatures %s" %
          (MAP_NAME, W, H, sum(sum(r) for r in grass), sum(1 for r in ledge for c in r if c), start, list(creatures)))

if __name__ == "__main__":
    main()
