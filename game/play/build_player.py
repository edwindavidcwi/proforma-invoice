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
  justify-content: flex-start; padding-top: 10px;
  position: absolute; top: 50px; bottom: 0;
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

/* ===================== Aesthetic overhaul ===================== */
body { background: linear-gradient(165deg, #0e2735 0%, #06131b 60%, #03090d 100%); }
#toolbar {
  background: linear-gradient(180deg, #0d2433, #06141c);
  box-shadow: 0 2px 12px rgba(0,0,0,0.45); gap: 6px;
  flex-wrap: nowrap; overflow-x: auto; overflow-y: hidden;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
#toolbar::-webkit-scrollbar { display: none; }
#toolbar .title { font-size: 15px; text-shadow: 0 1px 2px rgba(0,0,0,0.5); flex: 0 0 auto; }
#toolbar button {
  flex: 0 0 auto; white-space: nowrap;
  background: linear-gradient(180deg, #4a6fc4, #33508f);
  border-radius: 9px; padding: 7px 10px; font-size: 12px;
  box-shadow: 0 2px 0 rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.18);
}
#toolbar button:active { transform: translateY(1px); box-shadow: inset 0 2px 5px rgba(0,0,0,0.4); }
#toolbar button.on { background: linear-gradient(180deg, #ffd23f, #f0a818); color: #3a2600; }
/* segmented speed control */
.seg { display: inline-flex; border-radius: 9px; overflow: hidden; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.14); }
.seg .spd { background: #173042; border-radius: 0; box-shadow: none; padding: 8px 11px; min-width: 40px; }
.seg .spd:active { transform: none; }
.seg .spd.on { background: linear-gradient(180deg, #ffd23f, #f0a818); color: #3a2600; }

/* console screen frame */
#brand {
  display: flex; align-items: center; gap: 9px; margin-bottom: 11px;
  font-weight: 800; letter-spacing: 2.5px; font-size: 12px;
  text-transform: uppercase; color: #c2dceb; opacity: 0.92;
}
#led {
  width: 9px; height: 9px; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #ffa3a3, #d11d2a 70%);
  box-shadow: 0 0 7px #ff3b3b;
}
#game canvas {
  width: min(92vw, calc((100vh - 300px) * 1.1111));
  border: 10px solid #25394a; border-radius: 14px;
  box-shadow: 0 14px 32px rgba(0,0,0,0.55), inset 0 0 0 3px #16242e, 0 0 0 1px #0a141b;
  background: #0b1418;
}
#hint { bottom: 10px; }

/* on-screen gamepad polish */
#controller { opacity: 0.94; height: 230px; }
.roundBtn {
  width: 74px; height: 74px; font-size: 30px; color: #ffe3ef;
  text-shadow: 0 1px 1px rgba(0,0,0,0.45);
  background: radial-gradient(circle at 38% 30%, #e0277e 0%, #a3165a 62%, #7d1246 100%);
  box-shadow: 0 6px 0 #5c0d33, 0 9px 13px rgba(0,0,0,0.4), inset 0 2px 3px rgba(255,255,255,0.35);
}
.roundBtn.btnPressed { transform: translateY(4px); opacity: 1;
  box-shadow: 0 2px 0 #5c0d33, inset 0 3px 7px rgba(0,0,0,0.45); }
.capsuleBtn {
  color: #14181d; letter-spacing: 1px;
  background: linear-gradient(180deg, #818790, #585d64);
  box-shadow: 0 4px 0 #383c42, 0 6px 9px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.3);
}
.capsuleBtn.btnPressed { transform: translateY(3px); opacity: 1;
  box-shadow: 0 1px 0 #383c42, inset 0 2px 5px rgba(0,0,0,0.45); }
#controller_dpad:before {
  background: radial-gradient(circle at center, #6c7178 0%, #4e535a 60%, #3a3e44 100%);
  border-radius: 6px; box-shadow: inset 0 0 5px rgba(0,0,0,0.5);
}
#controller_up, #controller_down, #controller_left, #controller_right {
  background: linear-gradient(180deg, #6c7178, #494e55);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 3px 6px rgba(0,0,0,0.35);
}

/* ============== Control-bar redesign v2 (responsive, touch-first) ============== */
/* A flex column so the toolbar can wrap onto multiple rows without ever
   overlapping the game. Nothing is hidden off-screen anymore. */
html, body { height: 100%; }
body { display: flex; flex-direction: column; }

#toolbar {
  position: relative; z-index: 30;
  flex: 0 0 auto; flex-wrap: wrap; overflow: visible;
  align-items: center; gap: 7px 8px; padding: 9px 12px;
}
#toolbar .title {
  width: 100%; margin: 0 0 1px 0; font-size: 13px; letter-spacing: 1.6px;
  text-transform: uppercase; opacity: 0.92;
}
@media (min-width: 780px) {
  #toolbar .title { width: auto; margin: 0 auto 0 0; font-size: 15px; }
}
/* Logical groups, separated by faint dividers. */
.group { display: inline-flex; align-items: center; gap: 6px; }
.group + .group { padding-left: 8px; border-left: 1px solid rgba(255,255,255,0.10); }

/* Bigger, friendlier tap targets (Apple/Google min is ~44px). */
#toolbar button {
  min-height: 42px; padding: 8px 13px; font-size: 13px; border-radius: 11px;
  display: inline-flex; align-items: center; gap: 5px;
}
.seg { border-radius: 11px; }
.seg .spd { min-height: 42px; min-width: 48px; font-size: 15px; padding: 8px 12px; }
#btnPause.on { background: linear-gradient(180deg, #ffd23f, #f0a818); color: #3a2600; }

/* Let the game area fill whatever height the wrapped bar leaves. */
#game { position: relative; top: 0; bottom: auto; flex: 1 1 auto; padding-top: 14px; }
#hint { color: #98bccf; }

/* ===================== Console UI v3 (menu-driven, save slots) ===================== */
:root { --gold:#ffcb05; }
/* Minimal top bar: title + two quick actions (Pause, Menu). Everything else
   lives in the slide-up menu, so the play area stays clean and uncluttered. */
#toolbar {
  flex: 0 0 auto; flex-wrap: nowrap; overflow: visible;
  align-items: center; gap: 10px; padding: 10px 14px;
  background: linear-gradient(180deg, #0e2838, #071620);
  border-bottom: 3px solid var(--gold);
}
#toolbar .title {
  display: flex; align-items: center; gap: 9px; width: auto; margin: 0 auto 0 0;
  font-size: 15px; font-weight: 800; letter-spacing: 1.4px; text-transform: uppercase;
  color: var(--gold); text-shadow: 0 1px 2px rgba(0,0,0,.5); opacity: 1;
}
#led {
  width: 9px; height: 9px; border-radius: 50%; flex: 0 0 auto;
  background: radial-gradient(circle at 35% 30%, #ff6d6d, #c5121f 70%); box-shadow: 0 0 8px #ff3b3b;
}
.quick { display: flex; gap: 9px; flex: 0 0 auto; }
.quick button {
  min-height: 44px; padding: 10px 16px; font-size: 14px; font-weight: 700; border: 0;
  border-radius: 12px; cursor: pointer; color: #fff;
  background: linear-gradient(180deg, #4a6fc4, #33508f);
  box-shadow: 0 3px 0 rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.18);
}
#btnMenu { background: linear-gradient(180deg, #ffd23f, #f0a818); color: #3a2600; }
.quick button:active { transform: translateY(2px); box-shadow: inset 0 2px 6px rgba(0,0,0,.4); }
#btnPause.on { background: linear-gradient(180deg, #7fe0a3, #39ad6b); color: #04361d; }

/* Handheld-console screen housing. */
#game { padding-top: 18px; }
#screenwrap {
  position: relative; padding: 14px 14px 24px; border-radius: 24px;
  background: linear-gradient(160deg, #2c4255, #16242e);
  box-shadow: 0 18px 42px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.07),
              inset 0 0 0 1px rgba(0,0,0,.25);
}
#screenwrap::after {  /* speaker grille */
  content: ""; position: absolute; left: 50%; transform: translateX(-50%); bottom: 9px;
  width: 64px; height: 7px; border-radius: 6px; opacity: .65;
  background: repeating-linear-gradient(90deg, #0a141b 0 3px, transparent 3px 6px);
}
#game canvas {
  display: block; width: min(90vw, calc((100vh - 320px) * 1.1111)); height: auto;
  border: 8px solid #0c161d; border-radius: 10px; background: #0b1418;
  box-shadow: inset 0 0 0 2px #1d2c38, 0 6px 18px rgba(0,0,0,.5);
}
#hint { bottom: 10px; font-size: 11px; color: #8fb3c6; padding: 0 14px; }
/* On touch devices the on-screen gamepad fills the bottom, so the keyboard
   hint would just overlap the Select/Start buttons -- hide it there. */
@media (pointer: coarse) { #hint { display: none; } }

/* ---- slide-up menu sheet ---- */
#menu {
  display: none; position: fixed; inset: 0; z-index: 50;
  background: rgba(2,10,15,.66); -webkit-backdrop-filter: blur(3px); backdrop-filter: blur(3px);
  align-items: flex-end; justify-content: center;
}
#menu.show { display: flex; }
@media (min-width: 760px) { #menu { align-items: center; } }
#menu_card {
  width: 100%; max-width: 560px; max-height: 86vh; display: flex; flex-direction: column;
  color: #eaf3f8; background: linear-gradient(180deg, #0f2937, #0a1922);
  border: 1px solid rgba(255,255,255,.10); border-top: 4px solid var(--gold);
  border-radius: 20px 20px 0 0; box-shadow: 0 -10px 40px rgba(0,0,0,.6);
  animation: pq_slideup .22s ease;
}
@media (min-width: 760px) { #menu_card { border-radius: 20px; } }
@keyframes pq_slideup { from { transform: translateY(26px); opacity: .5; } to { transform: none; opacity: 1; } }
#menu_head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 18px; font-weight: 800; font-size: 18px; color: var(--gold);
  border-bottom: 1px solid rgba(255,255,255,.08);
}
#btnMenuClose {
  width: 40px; height: 40px; border-radius: 11px; border: 0; cursor: pointer;
  font-size: 17px; background: #1b3142; color: #cfe2ee;
}
#menu_body { padding: 14px 16px 24px; overflow-y: auto; display: grid; gap: 14px; }
.card {
  background: rgba(255,255,255,.035); border: 1px solid rgba(255,255,255,.07);
  border-radius: 14px; padding: 13px 14px;
}
.card h3 {
  margin: 0 0 10px; font-size: 12px; letter-spacing: 1.6px; text-transform: uppercase;
  color: #9cc0d4; font-weight: 700;
}
.btnrow { display: flex; flex-wrap: wrap; gap: 9px; }
.card button {
  min-height: 44px; padding: 10px 15px; font-size: 14px; font-weight: 600; border: 0;
  border-radius: 11px; cursor: pointer; color: #fff;
  background: linear-gradient(180deg, #33506f, #26405a);
  box-shadow: 0 2px 0 rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.12);
}
.card button:active { transform: translateY(1px); }
.card button.on { background: linear-gradient(180deg, #ffd23f, #f0a818); color: #3a2600; }

/* segmented speed control inside the menu */
#menu .seg { display: inline-flex; border-radius: 12px; overflow: hidden; box-shadow: inset 0 0 0 1px rgba(255,255,255,.14); }
#menu .seg .spd { min-height: 48px; min-width: 78px; font-size: 16px; border-radius: 0; box-shadow: none; background: #15303f; color: #fff; }
#menu .seg .spd.on { background: linear-gradient(180deg, #ffd23f, #f0a818); color: #3a2600; }

/* save slots */
#slots { display: grid; gap: 9px; }
.slot {
  display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 8px;
  background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.07);
  border-radius: 12px; padding: 9px 11px;
}
.slot-meta { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
.slot-meta b { font-size: 14px; }
.slot-meta span { font-size: 11.5px; color: #8fb3c6; }
.slot button { min-height: 40px; min-width: 64px; padding: 8px 12px; font-size: 13px; font-weight: 700; border: 0; border-radius: 10px; cursor: pointer; }
.slot-save { background: linear-gradient(180deg, #4a6fc4, #33508f); color: #fff; }
.slot-load { background: linear-gradient(180deg, #7fe0a3, #39ad6b); color: #04361d; }
.slot button:disabled { opacity: .4; cursor: default; }

/* toast */
#toast {
  position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%) translateY(20px);
  background: #0c2030; color: #eaf3f8; border: 1px solid var(--gold);
  padding: 10px 16px; border-radius: 30px; font-size: 13px; font-weight: 600;
  opacity: 0; pointer-events: none; transition: opacity .2s, transform .2s; z-index: 60;
}
#toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

/* ---- "Big screen" immersive mode ----
   A pure-CSS toggle that hides the top bar and enlarges the screen. It works
   everywhere (even where the Fullscreen API is blocked, e.g. a file opened
   straight from Downloads); the script also requests real fullscreen as a bonus
   when the platform allows it. A floating button (and Esc / Back) exits. */
#btnExitFs {
  display: none; position: fixed; top: 12px; right: 12px; z-index: 70;
  width: 46px; height: 46px; border-radius: 50%; border: 0; cursor: pointer;
  font-size: 18px; color: #fff; background: rgba(13,36,51,.82);
  box-shadow: 0 2px 10px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.18);
}
body.immersive #btnExitFs { display: block; }
body.immersive #toolbar { display: none; }
body.immersive #game { padding-top: 8px; }
body.immersive #screenwrap { padding: 8px 8px 14px; border-radius: 12px; }
body.immersive #game canvas { width: min(98vw, calc((100vh - 30px) * 1.1111)); }
"""

BODY_HTML = r"""
  <div id="toolbar">
    <span class="title"><span id="led"></span>{title}</span>
    <div class="quick">
      <button id="btnPause" title="Pause or resume (or press Space)">&#10073;&#10073; Pause</button>
      <button id="btnMenu" title="Open the menu (saves &amp; settings)">&#9776; Menu</button>
    </div>
  </div>

  <div id="game">
    <div id="screenwrap">
      <canvas id="mainCanvas" width="160" height="144">No Canvas Support</canvas>
    </div>
    <div id="hint">Arrows move &middot; X = A &middot; Z = B &middot; Enter = Start &middot; Space = pause &middot; tap &#9776; Menu for saves &amp; settings</div>
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

  <div id="menu">
    <div id="menu_card">
      <div id="menu_head"><span>&#9776; Menu</span><button id="btnMenuClose" title="Close">&#10005;</button></div>
      <div id="menu_body">
        <section class="card">
          <h3>Speed</h3>
          <span class="seg" title="Game speed">
            <button class="spd on" data-spd="1">1&times;</button>
            <button class="spd" data-spd="2">2&times;</button>
            <button class="spd" data-spd="4">4&times;</button>
            <button class="spd" data-spd="8">8&times;</button>
          </span>
        </section>
        <section class="card">
          <h3>Save slots</h3>
          <div id="slots"></div>
        </section>
        <section class="card">
          <h3>Display</h3>
          <button id="btnFilter" title="Cycle display filter (HD / Smooth / Crisp / LCD)">&#128444; HD</button>
        </section>
        <section class="card">
          <h3>Audio &amp; reading</h3>
          <div class="btnrow">
            <button id="btnSound" title="Music / sound on or off">&#128266; Sound</button>
            <button id="btnRead" title="Read dialogue aloud (text-to-speech)">&#128483; Read: Off</button>
          </div>
        </section>
        <section class="card">
          <h3>System</h3>
          <div class="btnrow">
            <button id="btnFull" title="Make the game fill the screen">&#9974; Big screen</button>
            <button id="btnOpen" title="Open a different .gb / .gbc ROM">&#128193; Open ROM</button>
          </div>
        </section>
      </div>
    </div>
  </div>

  <button id="btnExitFs" title="Exit big screen">&#10005;</button>
  <div id="toast"></div>
  <input id="romFile" type="file" accept=".gb,.gbc,.bin" style="display:none">
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
  // HD = Scale3x upscaler (smooths jagged edges); Smooth = bilinear blur;
  // Crisp = original pixels; LCD = smooth + scanlines.
  var modes = [['hd', 'HD'], ['smooth', 'Smooth'], ['crisp', 'Crisp'], ['lcd', 'LCD']];
  var i = 0;
  try {
    var saved = localStorage.getItem('pq_filter');
    for (var k = 0; k < modes.length; k++) if (modes[k][0] === saved) i = k;
  } catch (e) {}
  function apply() {
    var key = modes[i][0];
    var hd = (key === 'hd');
    window.__hd = hd;                       // read by the WebGL renderer on init
    if (window.__glSetHD) window.__glSetHD(hd);
    canvas.classList.toggle('crisp', key === 'crisp');
    game.classList.toggle('lcd', key === 'lcd');
    btn.textContent = '🖼 ' + modes[i][1];
    try { localStorage.setItem('pq_filter', key); } catch (e) {}
  }
  btn.addEventListener('click', function () { i = (i + 1) % modes.length; apply(); });
  apply();
})();
"""


# Game-speed control (1x / 2x / 4x). Sets window.__speed, which player.js reads
# in its run loop to advance more emulated ticks per real frame.
SPEED_JS = r"""
(function () {
  var btns = Array.prototype.slice.call(document.querySelectorAll('.spd'));
  if (!btns.length) return;
  function set(s) {
    window.__speed = s;
    btns.forEach(function (b) { b.classList.toggle('on', +b.getAttribute('data-spd') === s); });
    try { localStorage.setItem('pq_speed', String(s)); } catch (e) {}
    if (window.__applyVolume) window.__applyVolume();
  }
  btns.forEach(function (b) { b.addEventListener('click', function () { set(+b.getAttribute('data-spd')); }); });
  var saved = 1; try { saved = parseInt(localStorage.getItem('pq_speed'), 10) || 1; } catch (e) {}
  set([1, 2, 4, 8].indexOf(saved) >= 0 ? saved : 1);
})();
"""

# Make the page installable / "Add to Home screen" as a standalone app: inject a
# web-app manifest (as a blob URL) plus theme-color and an icon. Note: a file
# opened directly from Downloads can't trigger a full PWA install prompt
# (browsers require an https origin); this enables the standalone display and
# Add-to-Home-Screen where the platform allows it.
PWA_JS = r"""
(function () {
  var icon =
    "data:image/svg+xml;base64," + btoa(
      '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">' +
      '<rect width="512" height="512" rx="96" fill="#06141c"/>' +
      '<circle cx="256" cy="256" r="150" fill="#fff" stroke="#111" stroke-width="14"/>' +
      '<path d="M106 256h300" stroke="#111" stroke-width="28"/>' +
      '<path d="M106 256a150 150 0 0 1 300 0z" fill="#e3350d"/>' +
      '<circle cx="256" cy="256" r="46" fill="#fff" stroke="#111" stroke-width="14"/>' +
      '<text x="256" y="470" font-family="Arial" font-weight="bold" font-size="64" ' +
      'fill="#ffcb05" text-anchor="middle">QUIZ</text></svg>');
  var manifest = {
    name: document.title, short_name: "PokeQuiz", display: "standalone",
    orientation: "any", background_color: "#06141c", theme_color: "#06141c",
    start_url: ".", icons: [{ src: icon, sizes: "512x512", type: "image/svg+xml", purpose: "any" }]
  };
  function head(el) { document.head.appendChild(el); }
  try {
    var url = URL.createObjectURL(new Blob([JSON.stringify(manifest)], { type: "application/manifest+json" }));
    var link = document.createElement("link"); link.rel = "manifest"; link.href = url; head(link);
  } catch (e) {}
  var theme = document.createElement("meta"); theme.name = "theme-color"; theme.content = "#06141c"; head(theme);
  var apple = document.createElement("link"); apple.rel = "apple-touch-icon"; apple.href = icon; head(apple);
  var cap = document.createElement("meta"); cap.name = "apple-mobile-web-app-capable"; cap.content = "yes"; head(cap);
})();
"""


# Read-aloud (text-to-speech). Scrapes the on-screen text from the emulator's
# tile buffer (wTileMap @ 0xC3A0), converts Game Boy tiles to text via the
# pokered charmap, and speaks new dialogue. Major named characters get male /
# female voices (by keyword); system "notices" use a third voice; everyone else
# a neutral narrator. Voices differ by pitch/rate so it works on any device.
TTS_JS = r"""
(function () {
  var btn = document.getElementById('btnRead');
  var nativeTTS = window.AndroidTTS && window.AndroidTTS.speak ? window.AndroidTTS : null;
  if (!btn || (!window.speechSynthesis && !nativeTTS)) { if (btn) btn.style.display = 'none'; return; }
  var TILE = 0xC3A0, W = 20;
  function ch(t) {
    if (t === 0x7f) return ' ';
    if (t >= 0x80 && t <= 0x99) return String.fromCharCode(65 + t - 0x80);
    if (t >= 0xa0 && t <= 0xb9) return String.fromCharCode(97 + t - 0xa0);
    if (t >= 0xf6 && t <= 0xff) return String.fromCharCode(48 + t - 0xf6);
    var m = {0x9a:'(',0x9b:')',0x9c:':',0x9d:';',0x9e:'[',0x9f:']',0xe0:"'",0xe3:'-',
      0xe6:'?',0xe7:'!',0xe8:'.',0xba:'e',0xbb:"'d",0xbc:"'l",0xbd:"'s",0xbe:"'t",
      0xbf:"'v",0xe4:"'r",0xe5:"'m",0x75:'...',0x54:'Poke',0xe1:'Poke',0xe2:'mon',
      0x70:"'",0x71:"'",0x72:'"',0x73:'"'};
    return (t in m) ? m[t] : '';
  }
  function readScreenLines() {
    var em = window.__emulator;
    if (!em || !em.module || !em.e) return [];
    var rd = function (a) { return em.module._emulator_read_mem(em.e, a); };
    var rows = [];
    for (var r = 1; r <= 16; r++) {
      var line = '', letters = 0;
      for (var c = 1; c <= 18; c++) {
        var t = rd(TILE + r * W + c); line += ch(t);
        if (t >= 0x80 && t <= 0xb9) letters++;
      }
      line = line.replace(/\s+/g, ' ').trim();
      if (letters >= 2) rows.push(line);
    }
    return rows;
  }
  var vMale = null, vFemale = null, vNote = null;
  function pickVoices() {
    var all = speechSynthesis.getVoices() || [];
    var en = all.filter(function (v) { return /^en/i.test(v.lang) || /english/i.test(v.name); });
    var pool = en.length ? en : all;
    function f(re) { for (var i = 0; i < pool.length; i++) if (re.test(pool[i].name)) return pool[i]; return null; }
    vFemale = f(/female|samantha|victoria|zira|fiona|tessa|karen|moira|susan|woman/i) || pool[0] || null;
    vMale = f(/male|david|daniel|fred|alex|george|james|arthur|man\b/i) || pool[1] || pool[0] || null;
    vNote = f(/google|en-US|en-GB|english/i) || pool[2] || pool[0] || null;
  }
  pickVoices(); speechSynthesis.onvoiceschanged = pickVoices;
  var FEM = /\b(MOM|MOTHER|NURSE|JOY|MISTY|ERIKA|SABRINA|LORELEI|DAISY|JESSIE|LASS|BEAUTY|LADY|GIRL|SISTER|GRANNY|NIDORINA|CLEFAIRY)\b/;
  var MAL = /\b(OAK|PROF|GARY|BLUE|BROCK|SURGE|KOGA|BLAINE|GIOVANNI|BRUNO|LANCE|YOUNGSTER|BUG|CATCHER|GENTLEMAN|BOY|MAN|FATHER|DAD|SAILOR|BIKER|ROCKET|GRAMPS|JR)\b/;
  function kindOf(text) { var U = text.toUpperCase(); if (FEM.test(U)) return 'f'; if (MAL.test(U)) return 'm'; return 'n'; }
  function speak(text) {
    var k = kindOf(text);
    var pitch = k === 'f' ? 1.5 : k === 'm' ? 0.6 : 1.05;
    var rate = k === 'm' ? 0.95 : 1.0;
    // Prefer the native Android engine (reliable voices in a WebView); fall back
    // to the browser's Web Speech API everywhere else (desktop, real browsers).
    if (nativeTTS) {
      try { nativeTTS.speak(text, pitch, rate); return; } catch (e) {}
    }
    var u = new SpeechSynthesisUtterance(text);
    u.pitch = pitch; u.rate = rate;
    if (k === 'f') { if (vFemale) u.voice = vFemale; }
    else if (k === 'm') { if (vMale) u.voice = vMale; }
    else { if (vNote) u.voice = vNote; }
    // Queue (don't cancel) so consecutive sentences play in order, not cut off.
    try { speechSynthesis.speak(u); } catch (e) {}
  }
  var prevKey = '', recent = [], buffer = '', prevStable = [], timer = null, on = false;
  try { on = localStorage.getItem('pq_read') === '1'; } catch (e) {}
  function inRecent(line) {
    for (var i = 0; i < recent.length; i++) if (recent[i] === line) return true;
    return false;
  }
  // Speak COMPLETE sentences. Game Boy text wraps one sentence across several
  // lines/pages, so we accumulate the on-screen text (each line added once) into
  // a buffer and only speak whole sentences (ending in . ! or ?), keeping any
  // unfinished tail for when the next page reveals the rest. This keeps natural
  // sentence flow instead of reading each line as if it were its own sentence.
  function flushSentences(force) {
    // Sentence end = . ! ? NOT inside a number (so "4.7?" / "1.0?" stay whole).
    var re = /[\s\S]*?[.!?]+(?=\s|$|["')\]])/g, m, idx = 0;
    while ((m = re.exec(buffer)) !== null) {
      var s = m[0].trim();
      if (s) speak(s);
      idx = re.lastIndex;
    }
    var rem = buffer.slice(idx);
    if (force) { var t = rem.trim(); if (t) speak(t); rem = ''; }
    buffer = rem;
  }
  function poll() {
    var lines = readScreenLines();
    if (lines.length === 0) {                 // box closed: finish the last sentence, reset
      flushSentences(true); recent.length = 0; prevStable = []; prevKey = ''; return;
    }
    var key = lines.join('|');
    if (key !== prevKey) { prevKey = key; return; }   // act only once the text settles
    // A hard cut (a new screen sharing no line with the last) ends the old thought.
    var overlap = false;
    for (var i = 0; i < lines.length; i++) if (prevStable.indexOf(lines[i]) >= 0) overlap = true;
    if (!overlap && prevStable.length) flushSentences(true);
    for (var i = 0; i < lines.length; i++) {
      var ln = lines[i];
      if (ln.length < 2 || /^ABCDEFGHIJKLMNOP/.test(ln) || inRecent(ln)) continue;
      buffer += (buffer && !/\s$/.test(buffer) ? ' ' : '') + ln;   // append new line
      recent.push(ln);
      if (recent.length > 12) recent.shift();
    }
    flushSentences(false);
    prevStable = lines;
  }
  function stopSpeaking() {
    if (nativeTTS && nativeTTS.stop) { try { nativeTTS.stop(); } catch (e) {} }
    if (window.speechSynthesis) { try { speechSynthesis.cancel(); } catch (e) {} }
  }
  function setOn(v) {
    on = v; btn.textContent = '🗣 Read: ' + (on ? 'On' : 'Off');
    btn.classList.toggle('on', on);
    try { localStorage.setItem('pq_read', on ? '1' : '0'); } catch (e) {}
    if (on) { if (!timer) timer = setInterval(poll, 180); }
    else { if (timer) { clearInterval(timer); timer = null; } stopSpeaking(); buffer = ''; recent.length = 0; prevStable = []; prevKey = ''; }
  }
  btn.addEventListener('click', function () { setOn(!on); });
  setOn(on);
})();
"""


# Pause / resume button. Drives vm.togglePause() (same path as the Space key)
# so the game can be paused by touch on a phone. The label tracks the real state
# (it also flips when Space is pressed) by polling the emulator a few times/sec.
PAUSE_JS = r"""
(function () {
  var btn = document.getElementById('btnPause');
  if (!btn) return;
  function sync() {
    var em = window.__emulator;
    var paused = !!(em && em.isPaused);
    btn.innerHTML = paused ? '▶ Play' : '❚❚ Pause';
    btn.classList.toggle('on', paused);
  }
  btn.addEventListener('click', function () {
    if (window.__vm) { window.__vm.togglePause(); }
    if (window.__resumeAudio) window.__resumeAudio();
    setTimeout(sync, 0);
  });
  setInterval(sync, 350);
  sync();
})();
"""


# Sound on/off switch. The game's own audio is kept muted (it would speed up
# during fast-forward); instead the Sound button toggles the independent,
# constant-tempo background music (see MUSIC_JS). "Replace all audio" mode.
SOUND_JS = r"""
(function () {
  var btn = document.getElementById('btnSound');
  if (!btn) return;
  var on = true;
  try { if (localStorage.getItem('pq_sound') === '0') on = false; } catch (e) {}
  window.__soundOn = on;
  window.__applyVolume = function () {
    if (window.__vm) window.__vm.volume = 0;            // game audio replaced by our track
    if (on) { if (window.__musicStart) window.__musicStart(); }
    else    { if (window.__musicStop)  window.__musicStop();  }
  };
  function apply() {
    window.__soundOn = on;
    window.__applyVolume();
    btn.textContent = on ? '🔊 Music: On' : '🔈 Music: Off';
    btn.classList.toggle('on', on);
    try { localStorage.setItem('pq_sound', on ? '1' : '0'); } catch (e) {}
  }
  btn.addEventListener('click', function () { on = !on; apply(); });
  // vm is created when the ROM loads (async); apply once it's ready.
  var tries = 0, t = setInterval(function () {
    if (window.__vm || tries++ > 60) { apply(); if (window.__vm) clearInterval(t); }
  }, 100);
})();
"""


# Original, royalty-free 8-bit background music that ALWAYS plays at normal tempo,
# independent of the emulator's speed (the game's own audio is muted). A tiny
# Web Audio sequencer loops a cheerful original tune written for this app.
MUSIC_JS = r"""
(function () {
  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  var ctx = null, master = null, playing = false, timer = null, step = 0, nextTime = 0;
  var TEMPO = 120, spb = 60 / TEMPO / 2;              // seconds per 8th-note step
  // Original loop in C major (I-V-vi-IV). 0 = rest. Melody (square) + bass (triangle).
  var MEL = [72,0,76,0,79,0,76,0, 74,0,79,0,74,0,0,0,
             69,0,72,0,76,0,72,0, 65,0,69,0,72,0,0,0,
             72,0,76,0,79,0,83,0, 81,0,79,0,76,0,74,0,
             72,0,71,0,74,0,71,0, 72,0,0,0, 0,0,0,0];
  var BASS = [48,0,0,0,0,0,0,0, 43,0,0,0,0,0,0,0,
              45,0,0,0,0,0,0,0, 41,0,0,0,0,0,0,0,
              48,0,0,0,0,0,0,0, 43,0,0,0,0,0,0,0,
              45,0,0,0,0,0,0,0, 43,0,0,0,0,0,0,0];
  function midi(n){ return 440 * Math.pow(2, (n - 69) / 12); }
  function blip(freq, t, dur, type, vol){
    var o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(master);
    o.start(t); o.stop(t + dur + 0.03);
  }
  function schedule(){
    while (nextTime < ctx.currentTime + 0.3) {
      var i = step % MEL.length;
      if (MEL[i])  blip(midi(MEL[i]),  nextTime, spb * 0.95, 'square',   0.16);
      if (BASS[i]) blip(midi(BASS[i]), nextTime, spb * 3.6,  'triangle', 0.22);
      nextTime += spb; step++;
    }
  }
  window.__musicStart = function () {
    if (!ctx) { ctx = new AC(); master = ctx.createGain(); master.connect(ctx.destination); }
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch (e) {} }
    master.gain.value = 0.5;
    if (playing) return;
    playing = true; nextTime = ctx.currentTime + 0.1;
    timer = setInterval(schedule, 60);
  };
  window.__musicStop = function () {
    playing = false;
    if (timer) { clearInterval(timer); timer = null; }
    if (master) master.gain.value = 0;
  };
  // Browsers block audio until a user gesture; start on the first tap/key if on.
  function kick(){ if (window.__soundOn !== false) window.__musicStart(); }
  ['pointerdown', 'keydown', 'touchend'].forEach(function (ev) {
    window.addEventListener(ev, kick);
  });
})();
"""


# Slide-up menu: open/close the sheet and render the multiple save/load slots.
# Slot persistence lives in player.js (window.__pqSave / __pqLoad / __pqSlots),
# which key each slot per-ROM so different games don't clobber each other.
MENU_JS = r"""
(function () {
  var menu = document.getElementById('menu');
  var openBtn = document.getElementById('btnMenu');
  var closeBtn = document.getElementById('btnMenuClose');
  var slotsBox = document.getElementById('slots');
  var toastEl = document.getElementById('toast');
  if (!menu || !openBtn) return;

  var toastTimer = null;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 1700);
  }
  window.__pqToast = toast;

  function fmt(ts) {
    if (!ts) return 'Empty';
    try {
      var d = new Date(ts);
      return d.toLocaleDateString() + '  ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return 'Saved'; }
  }

  function renderSlots() {
    if (!slotsBox) return;
    var info = (window.__pqSlots && window.__pqSlots()) || [];
    slotsBox.innerHTML = '';
    info.forEach(function (s) {
      var row = document.createElement('div'); row.className = 'slot';
      var meta = document.createElement('div'); meta.className = 'slot-meta';
      var name = document.createElement('b'); name.textContent = 'Slot ' + s.slot;
      var when = document.createElement('span'); when.textContent = s.used ? fmt(s.ts) : 'Empty';
      meta.appendChild(name); meta.appendChild(when);

      var save = document.createElement('button'); save.className = 'slot-save'; save.textContent = 'Save';
      var load = document.createElement('button'); load.className = 'slot-load'; load.textContent = 'Load';
      if (!s.used) load.disabled = true;

      save.addEventListener('click', function () {
        if (window.__pqSave && window.__pqSave(s.slot)) { toast('Saved to slot ' + s.slot); renderSlots(); }
        else toast('Start the game first, then save');
      });
      load.addEventListener('click', function () {
        if (window.__pqLoad && window.__pqLoad(s.slot)) { toast('Loaded slot ' + s.slot); close(); }
        else toast('Slot ' + s.slot + ' is empty');
      });

      row.appendChild(meta); row.appendChild(save); row.appendChild(load);
      slotsBox.appendChild(row);
    });
  }

  function open() { renderSlots(); menu.classList.add('show'); }
  function close() { menu.classList.remove('show'); }

  openBtn.addEventListener('click', open);
  if (closeBtn) closeBtn.addEventListener('click', close);
  // Tap the dimmed backdrop (outside the card) to close.
  menu.addEventListener('click', function (e) { if (e.target === menu) close(); });
  window.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
"""


# "Big screen" / immersive toggle. Hides the top bar and enlarges the screen via
# a CSS class (works even when the Fullscreen API is blocked), and also requests
# real fullscreen when allowed. Exit via the floating button, Esc, or Back.
FS_JS = r"""
(function () {
  var btn = document.getElementById('btnFull');
  var exitBtn = document.getElementById('btnExitFs');
  var menu = document.getElementById('menu');
  function nativeOn() {
    var el = document.documentElement;
    var req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) { try { var p = req.call(el); if (p && p.catch) p.catch(function () {}); } catch (e) {} }
  }
  function nativeOff() {
    var ex = document.exitFullscreen || document.webkitExitFullscreen;
    if ((document.fullscreenElement || document.webkitFullscreenElement) && ex) {
      try { ex.call(document); } catch (e) {}
    }
  }
  function enter() {
    document.body.classList.add('immersive');
    if (menu) menu.classList.remove('show');
    nativeOn();
  }
  function exit() {
    document.body.classList.remove('immersive');
    nativeOff();
  }
  function toggle() {
    if (document.body.classList.contains('immersive')) exit(); else enter();
  }
  if (btn) btn.addEventListener('click', toggle);
  if (exitBtn) exitBtn.addEventListener('click', exit);
  window.addEventListener('keydown', function (e) { if (e.key === 'Escape') exit(); });
  // If the user leaves native fullscreen (system gesture/Back), drop immersive too.
  document.addEventListener('fullscreenchange', function () {
    if (!(document.fullscreenElement || document.webkitFullscreenElement)) {
      document.body.classList.remove('immersive');
    }
  });
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
        '  <script>\n%s\n</script>\n'
        '  <script>\n%s\n</script>\n'
        '  <script>\n%s\n</script>\n'
        '  <script>\n%s\n</script>\n'
        '  <script>\n%s\n</script>\n'
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
        SPEED_JS,
        PWA_JS,
        TTS_JS,
        MUSIC_JS,
        SOUND_JS,
        PAUSE_JS,
        MENU_JS,
        FS_JS,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print("Wrote %s (%.2f MB)" % (args.out, size_mb))
    print("ROM: %s  |  WASM: %s" % (args.rom, binjgb_wasm))
    print("Open it in any browser -- no internet needed.")


if __name__ == "__main__":
    main()
