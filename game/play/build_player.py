#!/usr/bin/env python3
"""Bake the Pokemon Quiz ROM + binjgb emulator into ONE self-contained .html.

The output file has no external dependencies: the WebAssembly core, the
emulator JavaScript, and the ROM itself are all inlined (the binary parts as
base64). You can copy that single .html to a phone or PC, open it in any modern
browser, and play completely offline -- nothing is downloaded.

Usage:
    python3 build_player.py [--rom PATH] [--out PATH] [--title TEXT]

Defaults:
    --rom   ../pokered/pokered.gbc
    --out   PokemonQuiz.html   (next to this script)
    --title "Pokemon Quiz"
"""
import argparse
import base64
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")

PAGE_CSS = r"""
:root { --bg:#0b1f2a; --panel:#06141c; --accent:#ffcb05; --accent2:#3b5ba5; }
* { box-sizing: border-box; }
body {
  background: var(--bg); color: #fff; margin: 0; padding: 0; overflow: hidden;
  font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
  touch-action: none; -webkit-user-select: none; user-select: none;
  -webkit-touch-callout: none;
}
#toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  background: var(--panel); padding: 8px 12px;
  border-bottom: 3px solid var(--accent);
}
#toolbar .title {
  font-weight: 700; color: var(--accent); margin-right: auto;
  font-size: 16px; letter-spacing: 0.3px;
}
#toolbar button {
  background: var(--accent2); color: #fff; border: 0; border-radius: 6px;
  padding: 7px 12px; font-size: 13px; font-weight: 600; cursor: pointer;
}
#toolbar button:hover { filter: brightness(1.15); }
#toolbar button:active { transform: translateY(1px); }

#game {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; position: absolute; top: 52px; bottom: 0;
  width: 100%; touch-action: none; background:
    radial-gradient(ellipse at center, #103043 0%, #06141c 100%);
}
#game canvas {
  width: min(100vw, calc((100vh - 52px) * 1.111)); height: auto;
  image-rendering: auto;            /* default: Smooth (bilinear upscale) */
  background: #000;
}
/* Crisp: show the original hard pixels. */
#game canvas.crisp {
  image-rendering: -moz-crisp-edges; image-rendering: -webkit-crisp-edges;
  image-rendering: pixelated; image-rendering: crisp-edges;
}
/* LCD: smooth image plus subtle horizontal scanlines, like a handheld screen. */
#game.lcd::after {
  content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 10;
  background: repeating-linear-gradient(
    to bottom, rgba(0,0,0,0.16) 0, rgba(0,0,0,0.16) 1px,
    transparent 1px, transparent 3px);
  mix-blend-mode: multiply;
}

#overlay {
  display: none; position: absolute; inset: 0; z-index: 20;
  background: rgba(3,18,26,0.92); color: #fff;
  flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 24px;
}
#overlay_msg { white-space: pre-wrap; max-width: 520px; line-height: 1.5; }

#hint {
  position: absolute; left: 0; right: 0; bottom: 6px; text-align: center;
  font-size: 11px; color: #9fc0d0; pointer-events: none;
}

/* --- On-screen gamepad (from binjgb/gb-studio, see LICENSE.gbstudio) --- */
#controller {
  display: none; position: fixed; bottom: 0px; height: 210px; width: 100%;
  touch-action: none; opacity: 0.8;
}
#controller_dpad { position: absolute; bottom: 20px; left: 0px; width: 184px; height: 184px; }
#controller_dpad:before {
  content: ""; display: block; width: 48px; height: 48px;
  background: radial-gradient(ellipse at center, #5c5c5c 0%, #555 59%, #5c5c5c 60%);
  position: absolute; left: 68px; top: 68px;
}
#controller_left  { position: absolute; left: 20px;  top: 68px;  width: 48px; height: 48px;
  background: radial-gradient(ellipse at center, #666 0%, #5c5c5c 80%);
  border-top-left-radius: 4px; border-bottom-left-radius: 4px; }
#controller_right { position: absolute; left: 116px; top: 68px;  width: 48px; height: 48px;
  background: radial-gradient(ellipse at center, #666 0%, #5c5c5c 80%);
  border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
#controller_up    { position: absolute; left: 68px;  top: 20px;  width: 48px; height: 48px;
  background: radial-gradient(ellipse at center, #666 0%, #5c5c5c 80%);
  border-top-left-radius: 4px; border-top-right-radius: 4px; }
#controller_down  { position: absolute; left: 68px;  top: 116px; width: 48px; height: 48px;
  background: radial-gradient(ellipse at center, #666 0%, #5c5c5c 80%);
  border-bottom-left-radius: 4px; border-bottom-right-radius: 4px; }
#controller_a { position: absolute; bottom: 110px; right: 20px; }
#controller_b { position: absolute; bottom: 80px;  right: 100px; }
.roundBtn {
  display: flex; justify-content: center; align-items: center; font-weight: bold;
  font-size: 32px; color: #440f1f; width: 64px; height: 64px; border-radius: 64px;
  background: radial-gradient(ellipse at center, #ab1465 0%, #8b1e57 100%);
  box-shadow: 0px 4px 5px rgba(0,0,0,0.2);
}
.capsuleBtn {
  font-weight: bold; font-size: 10px; color: #111; display: flex;
  justify-content: center; align-items: center; text-transform: uppercase;
  width: 64px; height: 32px; border-radius: 40px;
  background: radial-gradient(ellipse at center, #666 0%, #555 100%);
  box-shadow: 0px 4px 5px rgba(0,0,0,0.2);
}
#controller_start  { position: absolute; bottom: 20px; right: 15px; }
#controller_select { position: absolute; bottom: 20px; right: 100px; }
.btnPressed { opacity: 0.5; }
@media only screen and (max-width: 500px) and (max-height: 400px) {
  #controller { display: none; }
}
@media only screen and (min-width: 300px) and (orientation: landscape) {
  #controller { bottom: 50%; transform: translateY(50%); opacity: 0.5; }
}
"""

BODY_HTML = r"""
  <div id="toolbar">
    <span class="title">{title}</span>
    <button id="btnSave"  title="Save game state (or press F6)">Save</button>
    <button id="btnLoad"  title="Load game state (or press F9)">Load</button>
    <button id="btnFull"  title="Toggle fullscreen">Fullscreen</button>
    <button id="btnFilter" title="Cycle display filter (Smooth / Crisp / LCD)">Filter: Smooth</button>
    <button id="btnOpen"  title="Open a different .gb / .gbc ROM">Open ROM</button>
    <input id="romFile" type="file" accept=".gb,.gbc,.bin" style="display:none">
  </div>

  <div id="game">
    <canvas id="mainCanvas" width="160" height="144">No Canvas Support</canvas>
    <div id="hint">Keyboard: Arrows = move &middot; Z = B &middot; X = A &middot; Enter = Start &middot; Tab = Select &middot; Shift = fast-forward &middot; Backspace = rewind</div>
    <div id="overlay"><div id="overlay_msg"></div></div>
  </div>

  <div id="controller">
    <div id="controller_dpad">
      <div id="controller_left"></div>
      <div id="controller_right"></div>
      <div id="controller_up"></div>
      <div id="controller_down"></div>
    </div>
    <div id="controller_select" class="capsuleBtn">Select</div>
    <div id="controller_start" class="capsuleBtn">Start</div>
    <div id="controller_b" class="roundBtn">B</div>
    <div id="controller_a" class="roundBtn">A</div>
  </div>
"""


# Display-filter control. Cycles the canvas between Smooth (bilinear, default),
# Crisp (original pixels), and LCD (smooth + scanlines). Works for both the
# WebGL and Canvas2D renderers because the 160x144 canvas is CSS-scaled either
# way. The choice is remembered in localStorage.
FILTER_JS = r"""
(function () {
  var canvas = document.getElementById('mainCanvas');
  var game = document.getElementById('game');
  var btn = document.getElementById('btnFilter');
  if (!canvas || !game || !btn) return;
  var modes = [['smooth', 'Smooth'], ['crisp', 'Crisp'], ['lcd', 'LCD']];
  var i = 0;
  try {
    var saved = localStorage.getItem('pq_filter');
    for (var k = 0; k < modes.length; k++) if (modes[k][0] === saved) i = k;
  } catch (e) {}
  function apply() {
    var key = modes[i][0];
    canvas.classList.toggle('crisp', key === 'crisp');
    game.classList.toggle('lcd', key === 'lcd');
    btn.textContent = 'Filter: ' + modes[i][1];
    try { localStorage.setItem('pq_filter', key); } catch (e) {}
  }
  btn.addEventListener('click', function () { i = (i + 1) % modes.length; apply(); });
  apply();
})();
"""


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def b64_of(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", default=os.path.join(HERE, "..", "pokered", "pokered.gbc"))
    ap.add_argument("--out", default=os.path.join(HERE, "PokemonQuiz.html"))
    ap.add_argument("--title", default="Pokemon Quiz")
    args = ap.parse_args()

    binjgb_js = os.path.join(VENDOR, "binjgb.js")
    binjgb_wasm = os.path.join(VENDOR, "binjgb.wasm")
    player_js = os.path.join(VENDOR, "player.js")

    for p in (binjgb_js, binjgb_wasm, player_js):
        if not os.path.exists(p):
            sys.exit("error: missing required file: %s" % p)
    if not os.path.exists(args.rom):
        sys.exit("error: ROM not found: %s\n"
                 "Build the ROM first (cd ../pokered && make)." % args.rom)

    rom_name = os.path.basename(args.rom)
    wasm_b64 = b64_of(binjgb_wasm)
    rom_b64 = b64_of(args.rom)
    emu_js = read_text(binjgb_js)
    wrap_js = read_text(player_js)
    title_esc = html.escape(args.title)

    # Assemble the single document. Order matters:
    #   1) data blocks (WASM + ROM as base64 strings)
    #   2) the emulator core (defines window.Binjgb)
    #   3) the player wrapper (boots the core with the inlined data)
    doc = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1, '
        'maximum-scale=1, user-scalable=no, viewport-fit=cover">\n'
        '  <meta name="mobile-web-app-capable" content="yes">\n'
        "  <title>%s</title>\n"
        "  <style>%s</style>\n"
        "</head>\n"
        "<body>\n"
        "%s\n"
        '  <script>\n'
        '    window.__ROM_NAME__ = %s;\n'
        '    window.__WASM_B64__ = "%s";\n'
        '    window.__ROM_B64__ = "%s";\n'
        "  </script>\n"
        '  <script>\n%s\n</script>\n'
        '  <script>\n%s\n</script>\n'
        '  <script>\n%s\n</script>\n'
        "</body>\n"
        "</html>\n"
    ) % (
        title_esc,
        PAGE_CSS,
        BODY_HTML.format(title=title_esc),
        '"%s"' % rom_name.replace('"', '\\"'),
        wasm_b64,
        rom_b64,
        emu_js,
        wrap_js,
        FILTER_JS,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print("Wrote %s (%.2f MB)" % (args.out, size_mb))
    print("ROM: %s  |  WASM: %s" % (args.rom, binjgb_wasm))
    print("Open it in any browser -- no internet needed.")


if __name__ == "__main__":
    main()
