#!/usr/bin/env python3
"""Bake a GBA ROM + the IodineGBA (pure-JS) emulator into ONE offline .html.

The result is a single self-contained file: all of the emulator JavaScript and
the ROM (base64) are inlined. It runs on the main thread with no Web Workers and
no SharedArrayBuffer, so it works from a plain file:// page on Windows/Android
with no server and no internet.

Note: a GBA ROM is large (FireRed is 16 MB), so the output .html is ~22 MB and
IodineGBA is a pure-JS core, so speed depends on the device.

Usage:
    python3 build_player.py [--rom PATH] [--out PATH] [--title TEXT]
"""
import argparse
import base64
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")

# Load order copied from IodineGBA's index.html (core first, then glue).
JS_FILES = [
    "IodineGBA/includes/TypedArrayShim.js",
    "IodineGBA/core/Cartridge.js",
    "IodineGBA/core/DMA.js",
    "IodineGBA/core/Emulator.js",
    "IodineGBA/core/Graphics.js",
    "IodineGBA/core/RunLoop.js",
    "IodineGBA/core/Memory.js",
    "IodineGBA/core/IRQ.js",
    "IodineGBA/core/JoyPad.js",
    "IodineGBA/core/Serial.js",
    "IodineGBA/core/Sound.js",
    "IodineGBA/core/Timer.js",
    "IodineGBA/core/Wait.js",
    "IodineGBA/core/CPU.js",
    "IodineGBA/core/Saves.js",
    "IodineGBA/core/sound/FIFO.js",
    "IodineGBA/core/sound/Channel1.js",
    "IodineGBA/core/sound/Channel2.js",
    "IodineGBA/core/sound/Channel3.js",
    "IodineGBA/core/sound/Channel4.js",
    "IodineGBA/core/CPU/ARM.js",
    "IodineGBA/core/CPU/THUMB.js",
    "IodineGBA/core/CPU/CPSR.js",
    "IodineGBA/core/graphics/Renderer.js",
    "IodineGBA/core/graphics/RendererShim.js",
    "IodineGBA/core/graphics/RendererProxy.js",
    "IodineGBA/core/graphics/BGTEXT.js",
    "IodineGBA/core/graphics/BG2FrameBuffer.js",
    "IodineGBA/core/graphics/BGMatrix.js",
    "IodineGBA/core/graphics/AffineBG.js",
    "IodineGBA/core/graphics/ColorEffects.js",
    "IodineGBA/core/graphics/Mosaic.js",
    "IodineGBA/core/graphics/OBJ.js",
    "IodineGBA/core/graphics/OBJWindow.js",
    "IodineGBA/core/graphics/Window.js",
    "IodineGBA/core/graphics/Compositor.js",
    "IodineGBA/core/memory/DMA0.js",
    "IodineGBA/core/memory/DMA1.js",
    "IodineGBA/core/memory/DMA2.js",
    "IodineGBA/core/memory/DMA3.js",
    "IodineGBA/core/cartridge/SaveDeterminer.js",
    "IodineGBA/core/cartridge/SRAM.js",
    "IodineGBA/core/cartridge/FLASH.js",
    "IodineGBA/core/cartridge/EEPROM.js",
    "IodineGBA/core/cartridge/GPIO.js",
    # glue
    # NOTE: XAudioJS/swfobject.js (an ancient Flash-detection shim) is
    # deliberately NOT loaded: it throws at top-level on real browsers
    # (navigator parsing), which aborted the whole concatenated script and
    # left GfxGlueCode without its prototype methods ("initializeVSync is not
    # a function"). We use WebAudio, not Flash, so it is unneeded. A no-op
    # `swfobject` stub is injected below so the unused Flash path can't throw.
    "user_scripts/XAudioJS/resampler.js",
    "user_scripts/XAudioJS/XAudioServer.js",
    "user_scripts/AudioGlueCode.js",
    "user_scripts/GfxGlueCode.js",
]

# Harmless stand-in for the removed Flash shim. XAudioJS only touches these
# from its Flash fallback (never taken with WebAudio available), but defining
# them keeps any stray reference from throwing a ReferenceError.
SWFOBJECT_STUB = (
    "var swfobject={embedSWF:function(){},registerObject:function(){},"
    "getObjectById:function(){},switchOffAutoHideShow:function(){},ua:{},"
    "getFlashPlayerVersion:function(){return{major:0,minor:0,release:0};},"
    "hasFlashPlayerVersion:function(){return false;},createSWF:function(){},"
    "showExpressInstall:function(){},removeSWF:function(){},"
    "createCSS:function(){},addDomLoadEvent:function(){},"
    "addLoadEvent:function(){},getQueryParamValue:function(){return'';},"
    "expressInstallCallback:function(){}};"
)

PAGE_CSS = r"""
:root { --bg:#10131a; --panel:#0a0d12; --accent:#e3350d; --accent2:#3b5ba5; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; height:100%; }
body {
  background: var(--bg); color:#fff; overflow:hidden;
  font-family:"Segoe UI","Helvetica Neue",Helvetica,Arial,sans-serif;
  -webkit-user-select:none; user-select:none; -webkit-touch-callout:none; touch-action:none;
}
#toolbar {
  display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  background:var(--panel); padding:8px 12px; border-bottom:3px solid var(--accent);
}
#toolbar .title { font-weight:700; color:var(--accent); margin-right:auto; font-size:16px; }
#toolbar button {
  background:var(--accent2); color:#fff; border:0; border-radius:6px;
  padding:7px 12px; font-size:13px; font-weight:600; cursor:pointer;
}
#toolbar button:active { transform:translateY(1px); }

#stage {
  position:absolute; top:52px; bottom:0; width:100%;
  display:flex; flex-direction:column; align-items:center; justify-content:flex-start;
  background:radial-gradient(ellipse at center,#1b2230 0%,#0a0d12 100%);
}
#emulator_target {
  width:min(100vw, calc((100vh - 200px) * 1.5)); height:auto; margin-top:6px;
  image-rendering:pixelated; image-rendering:crisp-edges; background:#000;
}
#hint { font-size:11px; color:#8fa3bf; text-align:center; margin:4px 8px; }

#overlay {
  display:none; position:absolute; inset:0; z-index:20; background:rgba(8,11,16,.93);
  color:#fff; flex-direction:column; align-items:center; justify-content:center;
  text-align:center; padding:24px;
}
#overlay_msg { white-space:pre-wrap; max-width:520px; line-height:1.5; }

/* On-screen controls */
.touch-controls {
  display:flex; align-items:center; justify-content:space-between;
  width:100%; max-width:680px; padding:10px 16px; margin-top:auto; gap:12px;
}
.touch-dpad { display:grid; grid-template-columns:repeat(3,52px); grid-template-rows:repeat(3,52px); gap:4px; }
.touch-dpad button { font-size:20px; }
#touch-up { grid-column:2; grid-row:1; }
#touch-left { grid-column:1; grid-row:2; }
#touch-right { grid-column:3; grid-row:2; }
#touch-down { grid-column:2; grid-row:3; }
.touch-mid { display:flex; flex-direction:column; gap:8px; align-items:center; }
.touch-mid button { width:74px; height:26px; font-size:11px; border-radius:14px; }
.touch-face { display:grid; grid-template-columns:repeat(2,64px); grid-template-rows:repeat(2,64px); gap:8px; }
.touch-shoulder { display:flex; gap:24px; width:100%; justify-content:space-between; max-width:680px; padding:0 16px; }
.touch-shoulder button { width:88px; height:30px; border-radius:8px; }
.touch-controls button, .touch-shoulder button {
  background:#2a3242; color:#fff; border:1px solid #3a4456;
  border-radius:10px; font-weight:700; cursor:pointer; touch-action:none;
}
#touch-a { background:#7a1020; } #touch-b { background:#7a1020; }
.touch-controls button.pressed, .touch-shoulder button.pressed { opacity:.55; }

@media (min-width:760px) and (pointer:fine) {
  .touch-controls, .touch-shoulder { display:none; }
}
"""

BODY_HTML = r"""
  <div id="toolbar">
    <span class="title">{title}</span>
    <button id="btnSound" title="Turn sound on">Sound: off</button>
    <button id="btnFull" title="Toggle fullscreen">Fullscreen</button>
    <button id="btnOpen" title="Open a different .gba ROM">Open ROM</button>
    <input id="romFile" type="file" accept=".gba,.bin" style="display:none">
  </div>

  <div id="stage">
    <canvas id="emulator_target" width="240" height="160">No Canvas Support</canvas>
    <div id="hint">Keyboard: Arrows = move &middot; X = A &middot; Z = B &middot; A/S = L/R &middot; Enter = Start &middot; Shift = Select</div>

    <div class="touch-shoulder">
      <button id="touch-l">L</button>
      <button id="touch-r">R</button>
    </div>
    <div class="touch-controls">
      <div class="touch-dpad">
        <button id="touch-up">&#9650;</button>
        <button id="touch-left">&#9664;</button>
        <button id="touch-right">&#9654;</button>
        <button id="touch-down">&#9660;</button>
      </div>
      <div class="touch-mid">
        <button id="touch-select">SELECT</button>
        <button id="touch-start">START</button>
      </div>
      <div class="touch-face">
        <button id="touch-b">B</button>
        <button id="touch-a">A</button>
      </div>
    </div>

    <div id="overlay"><div id="overlay_msg"></div></div>
  </div>
"""


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", default=os.path.join(HERE, "..", "pokefirered", "src", "pokefirered_modern.gba"))
    ap.add_argument("--out", default=os.path.join(HERE, "FireRedQuiz.html"))
    ap.add_argument("--title", default="Pokemon FireRed Quiz")
    args = ap.parse_args()

    missing = [f for f in JS_FILES if not os.path.exists(os.path.join(VENDOR, f))]
    if missing:
        sys.exit("error: missing vendored JS files:\n  " + "\n  ".join(missing))
    if not os.path.exists(args.rom):
        sys.exit("error: ROM not found: %s\nBuild it first (see game/pokefirered/README.md)." % args.rom)

    # Concatenate the emulator core + glue in load order.
    chunks = ["/* swfobject Flash-shim stub (see build_player.py) */", SWFOBJECT_STUB]
    for rel in JS_FILES:
        chunks.append("/* ==== %s ==== */" % rel)
        chunks.append(read_text(os.path.join(VENDOR, rel)))
    emu_js = "\n".join(chunks)
    driver_js = read_text(os.path.join(VENDOR, "driver.js"))

    with open(args.rom, "rb") as f:
        rom_b64 = base64.b64encode(f.read()).decode("ascii")
    rom_name = os.path.basename(args.rom)
    title_esc = html.escape(args.title)

    bios_path = os.path.join(VENDOR, "gba_bios.bin")
    if not os.path.exists(bios_path):
        sys.exit("error: missing vendor/gba_bios.bin (open-source GBA BIOS).")
    with open(bios_path, "rb") as f:
        bios_bytes = f.read()
    if len(bios_bytes) != 0x4000:
        sys.exit("error: gba_bios.bin must be exactly 16384 bytes, got %d." % len(bios_bytes))
    bios_b64 = base64.b64encode(bios_bytes).decode("ascii")

    doc = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, "
        "maximum-scale=1, user-scalable=no, viewport-fit=cover\">\n"
        "  <title>%s</title>\n  <style>%s</style>\n</head>\n<body>\n%s\n"
        "  <script>\n    window.__ROM_NAME__ = \"%s\";\n"
        "    window.__BIOS_B64__ = \"%s\";\n"
        "    window.__ROM_B64__ = \"%s\";\n  </script>\n"
        "  <script>\n%s\n</script>\n"
        "  <script>\n%s\n</script>\n"
        "</body>\n</html>\n"
    ) % (
        title_esc, PAGE_CSS, BODY_HTML.format(title=title_esc),
        rom_name.replace('"', '\\"'), bios_b64, rom_b64, emu_js, driver_js,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print("Wrote %s (%.2f MB)" % (args.out, size_mb))
    print("Open it in any browser -- no internet needed (pure-JS GBA core).")


if __name__ == "__main__":
    main()
