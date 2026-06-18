#!/usr/bin/env python3
# v3 asset-pipeline proof: compose a REAL Pokemon Red map from the authentic
# pokered assets (tileset PNG + blockset + .blk layout) + the real player sprite,
# so we can confirm the look BEFORE writing any web renderer. This is exactly the
# data the v3 engine's Asset Registry + Renderer will use.
#
#   python3 compose_map.py PalletTown OVERWORLD 10 9
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.normpath(os.path.join(HERE, "..", "..", "pokered"))
OUT = os.path.join(HERE, "..", "preview")
os.makedirs(OUT, exist_ok=True)

# Classic Game Boy green palette (lightest -> darkest). Easily swappable; this is
# just the display palette, the tiles themselves are the authentic art.
GB = {255: (155, 188, 15), 170: (139, 172, 15), 85: (48, 98, 48), 0: (15, 56, 15)}
TILE = 8
BLOCK_TILES = 4          # a block is 4x4 tiles
SCALE = 3


def load_tileset(name):
    im = Image.open(os.path.join(PK, "gfx", "tilesets", name + ".png")).convert("L")
    cols = im.width // TILE
    tiles = []
    n = (im.width // TILE) * (im.height // TILE)
    for i in range(n):
        tx, ty = (i % cols) * TILE, (i // cols) * TILE
        tiles.append(im.crop((tx, ty, tx + TILE, ty + TILE)))
    return tiles


def load_blockset(name):
    data = open(os.path.join(PK, "gfx", "blocksets", name + ".bst"), "rb").read()
    return [data[i:i + 16] for i in range(0, len(data), 16)]   # 16 tile-ids per block


def colorize(gray_img):
    rgb = Image.new("RGB", gray_img.size)
    src = gray_img.load(); dst = rgb.load()
    for y in range(gray_img.height):
        for x in range(gray_img.width):
            dst[x, y] = GB.get(src[x, y], (155, 188, 15))
    return rgb


def compose(map_name, tileset_name, w, h):
    tiles = load_tileset(tileset_name)
    blocks = load_blockset(tileset_name)
    blk = open(os.path.join(PK, "maps", map_name + ".blk"), "rb").read()
    img = Image.new("L", (w * BLOCK_TILES * TILE, h * BLOCK_TILES * TILE), 255)
    for my in range(h):
        for mx in range(w):
            block_id = blk[my * w + mx]
            btiles = blocks[block_id]
            for ty in range(BLOCK_TILES):
                for tx in range(BLOCK_TILES):
                    tid = btiles[ty * BLOCK_TILES + tx]
                    if tid < len(tiles):
                        px = (mx * BLOCK_TILES + tx) * TILE
                        py = (my * BLOCK_TILES + ty) * TILE
                        img.paste(tiles[tid], (px, py))
    out = colorize(img)
    overlay_player(out, w, h)
    out = out.resize((out.width * SCALE, out.height * SCALE), Image.NEAREST)
    dst = os.path.join(OUT, map_name + ".png")
    out.save(dst)
    print("wrote", dst, out.size)


def overlay_player(rgb, w, h):
    # the real Red overworld sprite (first frame = facing down), placed roughly
    # where the player starts in town. White (255) is treated as transparent.
    sp = Image.open(os.path.join(PK, "gfx", "sprites", "red.png")).convert("L")
    frame = sp.crop((0, 0, 16, 16))
    col = colorize(frame); col_px = col.load(); fr_px = frame.load()
    px0 = (w * BLOCK_TILES * TILE) // 2 - 8
    py0 = (h * BLOCK_TILES * TILE) // 2
    for y in range(16):
        for x in range(16):
            if fr_px[x, y] != 255:               # skip the white background
                rgb.putpixel((px0 + x, py0 + y), col_px[x, y])


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "PalletTown"
    ts = sys.argv[2] if len(sys.argv) > 2 else "overworld"
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 9
    compose(name, ts.lower(), w, h)
