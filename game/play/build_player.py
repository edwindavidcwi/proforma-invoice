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
  background: linear-gradient(180deg, #0a1c26, var(--panel)); padding: 9px 14px;
  border-bottom: 3px solid var(--accent); box-shadow: 0 2px 10px rgba(0,0,0,.4);
}
#toolbar .title {
  font-weight: 800; color: var(--accent); margin-right: auto;
  font-size: 16px; letter-spacing: 0.4px; text-shadow: 0 1px 0 #6b4e00, 0 0 12px rgba(255,203,5,.25);
}
#toolbar button {
  background: linear-gradient(180deg, #4a6fc4, #33509a); color: #fff; border: 0; border-radius: 9px;
  padding: 8px 13px; font-size: 13px; font-weight: 600; cursor: pointer;
  box-shadow: 0 2px 0 rgba(0,0,0,.35); transition: transform .08s, filter .12s;
}
#toolbar button:hover { filter: brightness(1.13); }
#toolbar button:active { transform: translateY(2px); box-shadow: 0 0 0 rgba(0,0,0,.35); }

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
#btnFF { position: absolute; bottom: 60px; left: 50%; transform: translateX(-50%); }
#btnFF.btnPressed { transform: translateX(-50%) translateY(3px); }
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
/* ---- learning visual aid: real shapes & colours drawn over the empty top
   band of the battle screen during shape/colour questions ---- */
#visualAid { position: fixed; z-index: 22; display: none; pointer-events: none; }
#visualAid.show { display: block; }
#visualAid .vaCard { display: flex; align-items: center; justify-content: center;
  gap: 8%; width: 100%; height: 100%; box-sizing: border-box; padding: 4%;
  background: rgba(255,255,255,.92); border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,.45); }
#visualAid svg { width: auto; height: 100%; max-width: 100%; }
#visualAid .swatch { flex: 1 1 0; min-width: 0; height: 88%; border-radius: 8px;
  border: 2px solid rgba(0,0,0,.4); }
#visualAid .op { flex: 0 0 auto; font: 700 100% / 1 system-ui, sans-serif; color: #222; }
/* ---- parent Report Card ---- */
:root { --good:#43c06a; --mid:#f2b134; --low:#ef6b62; }
.pqOpenBtn { width: 100%; padding: 13px; border: 0; border-radius: 13px; cursor: pointer;
  font: 700 14px/1 system-ui, sans-serif; color: #3a2600; letter-spacing: .01em;
  background: linear-gradient(180deg, #ffd23f, #f0a818); box-shadow: 0 3px 0 #c1860f;
  display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform .08s; }
.pqOpenBtn:active { transform: translateY(2px); box-shadow: 0 1px 0 #c1860f; }
#pqReport { display: none; position: fixed; inset: 0; z-index: 60; padding: 14px;
  background: rgba(2,10,15,.74); -webkit-backdrop-filter: blur(5px); backdrop-filter: blur(5px);
  align-items: center; justify-content: center; }
#pqReport.show { display: flex; animation: pqFade .18s ease; }
@keyframes pqFade { from { opacity: 0; transform: scale(.98); } to { opacity: 1; transform: none; } }
#pqReportCard { width: min(96vw, 480px); max-height: 90vh; display: flex; flex-direction: column;
  background: linear-gradient(180deg, #15293a, #0f1d28); color: #e4eef5; border-radius: 18px;
  overflow: hidden; box-shadow: 0 24px 60px rgba(0,0,0,.6), inset 0 0 0 1px rgba(255,255,255,.05);
  font-family: system-ui, "Segoe UI", sans-serif; }
#pqReportHead { display: flex; align-items: center; gap: 8px; padding: 15px 18px; font-weight: 800;
  font-size: 17px; color: #2a1c00; background: linear-gradient(180deg, #ffd23f, #f4ad1b); }
#pqReportHead span { margin-right: auto; }
#pqReportHead button { background: rgba(0,0,0,.14); border: 0; color: #2a1c00; width: 28px; height: 28px;
  border-radius: 8px; font-size: 16px; cursor: pointer; line-height: 1; }
#pqReportBody { padding: 16px 18px; overflow-y: auto; }
/* summary stat tiles */
.pgStats { display: flex; gap: 10px; margin-bottom: 6px; }
.pgTile { flex: 1; background: #0c1923; border: 1px solid #213340; border-radius: 12px; padding: 12px 8px; text-align: center; }
.pgTileVal { font-size: 24px; font-weight: 800; color: #e4eef5; line-height: 1.1; }
.pgTileVal.good { color: var(--good); } .pgTileVal.mid { color: var(--mid); } .pgTileVal.low { color: var(--low); }
.pgTileLbl { font-size: 11px; color: #88a6b8; margin-top: 3px; text-transform: uppercase; letter-spacing: .04em; }
/* section headers */
.pgSec { display: flex; align-items: baseline; gap: 8px; margin: 18px 0 8px; font-size: 12px;
  font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: #aecadb; }
.pgSec span { font-weight: 500; text-transform: none; letter-spacing: 0; font-size: 11px; color: #6f8b9a; }
/* rows */
.pgItem { border-radius: 10px; overflow: hidden; margin: 4px 0; background: #0c1923; border: 1px solid #1b2c38; }
.pgRow { display: flex; align-items: center; gap: 9px; padding: 9px 11px; font-size: 13px; }
.pgClick { cursor: pointer; } .pgClick:hover { background: #122430; }
.pgChev { color: #6f8b9a; font-size: 15px; transition: transform .15s; width: 10px; flex: 0 0 auto; }
.pgRow.open .pgChev { transform: rotate(90deg); }
.pgLbl { flex: 0 0 34%; font-weight: 600; }
.pgBar { flex: 1 1 auto; height: 10px; border-radius: 5px; background: #1f3340; overflow: hidden; }
.pgBar i { display: block; height: 100%; border-radius: 5px; transition: width .4s ease; }
.pgBar.good i { background: linear-gradient(90deg, #36a85c, #6fe08a); }
.pgBar.mid  i { background: linear-gradient(90deg, #d99a1e, #f5c451); }
.pgBar.low  i { background: linear-gradient(90deg, #d8514a, #f58a83); }
.pgPct { flex: 0 0 auto; min-width: 38px; text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }
.pgPct.good { color: var(--good); } .pgPct.mid { color: var(--mid); } .pgPct.low { color: var(--low); }
.pgN { flex: 0 0 auto; min-width: 26px; text-align: right; font-size: 11px; color: #6f8b9a; }
/* drill-down */
.pgDetailWrap { display: none; padding: 0 11px 6px 30px; }
.pgRow.open + .pgDetailWrap { display: block; }
.pgQ { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-top: 1px solid #182a36; font-size: 12.5px; }
.pgQt { flex: 1 1 auto; color: #cfe0ec; }
.pgA { flex: 0 0 auto; background: rgba(67,192,106,.16); color: #7fe0a0; border-radius: 6px; padding: 2px 7px; font-weight: 600; }
.pgM { flex: 0 0 auto; color: var(--low); font-weight: 700; min-width: 26px; text-align: right; }
.pgNone { color: #80a0b2; font-size: 12.5px; padding: 6px 0 2px; }
/* teaching plan card */
.pgPlan { background: linear-gradient(180deg, #143427, #0f2920); border: 1px solid #245a3e;
  border-left: 4px solid var(--good); border-radius: 12px; padding: 13px 15px; }
.pgPlanHd { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.pgPlanHd span:first-child { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #8fd0a8; }
.pgPlanHd b { color: #fff; } .pgPlanHd .pgPct { margin-left: auto; }
.pgPlanTip { margin-top: 9px; font-size: 13px; line-height: 1.5; color: #d6eade; }
.pgPlanSub { margin-top: 11px; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #8fd0a8; }
.pgPlan .pgQ { border-top-color: rgba(255,255,255,.07); }
/* empty state */
.pgEmpty { text-align: center; padding: 24px 10px; }
.pgEmoji { font-size: 44px; } .pgEmptyT { font-size: 17px; font-weight: 700; margin: 8px 0 4px; }
.pgDim { color: #88a6b8; font-size: 13px; line-height: 1.5; }
#pqReportFoot { padding: 12px 18px; border-top: 1px solid #1b2c38; text-align: right; }
#pqReportReset { background: transparent; color: #ef8a83; border: 1px solid #5a3343; border-radius: 9px; padding: 8px 13px; cursor: pointer; font-size: 12.5px; }
#pqReportReset:hover { background: rgba(239,107,98,.12); }
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
      <button id="btnPause" title="Pause or resume">&#10073;&#10073; Pause</button>
      <button id="btnFullTop" title="Fill the screen (big screen)">&#9974; Full</button>
      <button id="btnMenu" title="Open the menu (saves &amp; settings)">&#9776; Menu</button>
    </div>
  </div>

  <div id="game">
    <div id="screenwrap">
      <canvas id="mainCanvas" width="160" height="144">No Canvas Support</canvas>
    </div>
    <div id="hint">Arrows move &middot; Z = A &middot; X = B &middot; Enter = Start &middot; hold Space = fast-forward &middot; tap &#9776; Menu for saves &amp; settings</div>
    <div id="overlay"><div id="overlay_msg"></div></div>
    <div id="visualAid" aria-hidden="true"></div>
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
    <div id="btnFF" class="capsuleBtn" title="Hold to fast-forward">&#9193;</div>
    <div id="controller_b" class="roundBtn">B</div>
    <div id="controller_a" class="roundBtn">A</div>
  </div>

  <div id="menu">
    <div id="menu_card">
      <div id="menu_head"><span>&#9776; Menu</span><button id="btnMenuClose" title="Close">&#10005;</button></div>
      <div id="menu_body">
        <section class="card">
          <h3>Fast-forward speed <small>(normal play is 2&times;; hold Space to boost &mdash; music stays at normal speed)</small></h3>
          <span class="seg" title="Speed while holding Space">
            <button class="spd" data-spd="3">3&times;</button>
            <button class="spd on" data-spd="4">4&times;</button>
            <button class="spd" data-spd="6">6&times;</button>
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
          <h3>Audio</h3>
          <div class="btnrow">
            <button id="btnSound" title="Music &amp; sound effects on or off">&#128266; Sound</button>
          </div>
        </section>
        <section class="card">
          <h3>Read aloud <small>(speaks the question &amp; choices)</small></h3>
          <div class="btnrow">
            <button id="btnRead" title="Read the question and answer choices out loud">&#128483; Read aloud</button>
            <button id="btnVoice" title="Switch the speaking voice">&#127908; Voice</button>
            <button id="btnReadAgain" title="Hear the current question again">&#128260; Again</button>
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


# Game-speed control. Normal play runs at 2x (BASE) for a snappy feel. The music
# is an INDEPENDENT track (see MUSIC_JS) played from captured buffers, so it keeps
# its normal speed no matter how fast the game runs -- fast-forward never speeds
# up the music. Holding Space "fast-forwards" to the boost speed chosen in the
# menu (default 4x). window.__speed is what player.js reads in its run loop.
SPEED_JS = r"""
(function () {
  var BASE = 2;                                   // normal play speed
  var btns = Array.prototype.slice.call(document.querySelectorAll('.spd'));
  var boost = 4;
  try { var v = parseInt(localStorage.getItem('pq_boost'), 10); if ([3,4,6,8].indexOf(v) >= 0) boost = v; } catch (e) {}
  var boosting = false;

  function applySpeed() {
    window.__speed = boosting ? boost : BASE;          // music is independent, so speed never touches audio
  }
  function setBoost(s) {
    boost = s;
    btns.forEach(function (b) { b.classList.toggle('on', +b.getAttribute('data-spd') === s); });
    try { localStorage.setItem('pq_boost', String(s)); } catch (e) {}
    applySpeed();
  }
  btns.forEach(function (b) { b.addEventListener('click', function () { setBoost(+b.getAttribute('data-spd')); }); });
  setBoost(boost);
  applySpeed();

  // Hold Space to fast-forward; release to return to normal 2x. (Typing in a
  // text field, if any ever exists, is left alone.)
  function isTyping(e) { var t = e.target; return t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA'); }
  window.addEventListener('keydown', function (e) {
    if (e.code !== 'Space' || isTyping(e)) return;
    e.preventDefault();
    if (!boosting) { boosting = true; applySpeed(); }
  }, true);
  window.addEventListener('keyup', function (e) {
    if (e.code !== 'Space' || isTyping(e)) return;
    e.preventDefault();
    if (boosting) { boosting = false; applySpeed(); }
  }, true);
  // If focus is lost mid-hold (alt-tab), drop the boost so it can't get stuck on.
  window.addEventListener('blur', function () { if (boosting) { boosting = false; applySpeed(); } });

  // On-screen fast-forward for touch devices: hold the dedicated button if present.
  var ffBtn = document.getElementById('btnFF');
  if (ffBtn) {
    var press = function (on) { return function (ev) { ev.preventDefault(); boosting = on; ffBtn.classList.toggle('btnPressed', on); applySpeed(); }; };
    ffBtn.addEventListener('pointerdown', press(true));
    ffBtn.addEventListener('pointerup', press(false));
    ffBtn.addEventListener('pointerleave', press(false));
    ffBtn.addEventListener('pointercancel', press(false));
  }
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


# Sound on/off switch. The game's own EMULATED audio is kept muted (it would
# speed up during fast-forward); instead the real Pokemon Red music plays as an
# independent, fixed-speed track (MUSIC_JS), and this button turns that track
# (plus the answer/UI sound effects) on or off.
SOUND_JS = r"""
(function () {
  var btn = document.getElementById('btnSound');
  if (!btn) return;
  var on = true;
  try { if (localStorage.getItem('pq_sound') === '0') on = false; } catch (e) {}
  window.__soundOn = on;
  window.__applyVolume = function () {
    if (window.__vm) window.__vm.volume = 0;            // emulated audio replaced by our independent track
    if (on) { if (window.__musicStart) window.__musicStart(); }
    else    { if (window.__musicStop)  window.__musicStop();  }
  };
  function apply() {
    window.__soundOn = on;
    window.__applyVolume();
    btn.textContent = on ? '🔊 Sound: On' : '🔈 Sound: Off';
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


# Background music = the game's OWN soundtrack, played by a SECOND, hidden Game
# Boy. The visible emulator can run fast (2x / fast-forward) with its audio muted;
# this second binjgb instance (same inlined ROM + WASM, so ~0 extra download) runs
# locked at normal 1x speed and its audio IS heard. A poller reads which song the
# visible game is playing (wChannelSoundIDs music id 0xBA-0xFC + wAudioROMBank) and
# tells the hidden instance to play that exact song -- by writing a tiny
# `ld a,id; ld c,bank; call PlayMusic; jr -2` stub into a V-blank-safe RAM scratch
# (wOverworldMap, 0xc6e8) and pointing its CPU there; the V-blank interrupt then
# advances + loops the song the ROM's own way (full length, seamless). So the real
# music plays correctly EVERYWHERE (title, intro, every town, every battle) and
# never speeds up. A tiny SFX bus adds correct/wrong answer + UI feedback.
# (pickTrack/readState are kept only for the headless context test.)
MUSIC_JS = r"""
(function () {
  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  var ctx = null, master = null, musicGain = null, sfxGain = null;

  // ---- the hidden, audio-only Game Boy ----
  var mod = null, e2 = null, audioPtr = null, booting = false, ready = false;
  var running = false, raf = 0, lastSec = 0, startSec = 0;
  var curId = 0, curBank = 0, poller = null, lastStreak = null, stubSet = false;
  var TPF = 70224, CPU = 4194304, FRAMES = 4096, LAT = 0.1;
  var EV_AUDIO = 2, EV_TICKS = 4;
  var STUB = 0xc6e8, PLAYMUSIC = 0x23a1, MUS_LO = 0xba, MUS_HI = 0xfc;
  // RAM mailbox the stub polls (in the same V-blank-safe wOverworldMap scratch).
  var FLAG = 0xc700, IDV = 0xc701, BANKV = 0xc702;

  function b64bytes(b64) {
    var s = atob(b64), a = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) a[i] = s.charCodeAt(i);
    return a;
  }

  // Boot a second binjgb instance from the same inlined ROM/WASM, run it to the
  // title screen (so its audio engine + interrupts are live), then it's ready to
  // be told what to play.
  function boot() {
    if (booting || ready) return;
    if (typeof Binjgb !== 'function' || !window.__WASM_B64__ || !window.__ROM_B64__) return;
    booting = true;
    Binjgb({ wasmBinary: b64bytes(window.__WASM_B64__) }).then(function (m) {
      try {
        mod = m;
        var rom = b64bytes(window.__ROM_B64__);
        var size = (rom.length + 0x7fff) & ~0x7fff;
        var p = m._malloc(size); m.HEAPU8.fill(0, p, p + size); m.HEAPU8.set(rom, p);
        e2 = m._emulator_new_simple(p, size, ctx.sampleRate, FRAMES, 2);
        if (e2 === 0) { booting = false; return; }
        audioPtr = m._get_audio_buffer_ptr(e2);
        var tgt = m._emulator_get_ticks_f64(e2) + 400 * TPF;   // run to title (discard this audio)
        while (true) { if (m._emulator_run_until_f64(e2, tgt) & EV_TICKS) break; }
        setupStub();                                           // hand control to the polling stub (one set_PC)
        ready = true; booting = false;
        if (running) { lastSec = performance.now() / 1000; startSec = 0; pump(); }
      } catch (e) { booting = false; }
    }).catch(function () { booting = false; });
  }

  // Install a tiny loop in RAM that watches FLAG and, when set, calls PlayMusic
  // with the requested id/bank -- then changing songs is just a memory write at a
  // safe point. We do set_PC exactly ONCE (here); forcing the PC on every change
  // can land mid-interrupt and corrupt the stack, which silenced the audio after
  // a few switches.
  function setupStub() {
    if (stubSet) return;
    // loop: if(FLAG){ FLAG=0; c=[BANKV]; a=[IDV]; call PlayMusic; } repeat
    var code = [0xfa, FLAG & 0xff, (FLAG >> 8) & 0xff,   // ld a,[FLAG]
                0xa7,                                    // and a
                0x28, 0xfa,                              // jr z,-6  (back to top)
                0xaf,                                    // xor a
                0xea, FLAG & 0xff, (FLAG >> 8) & 0xff,   // ld [FLAG],a  (clear)
                0xfa, BANKV & 0xff, (BANKV >> 8) & 0xff, // ld a,[BANKV]
                0x4f,                                    // ld c,a
                0xfa, IDV & 0xff, (IDV >> 8) & 0xff,     // ld a,[IDV]
                0xcd, PLAYMUSIC & 0xff, (PLAYMUSIC >> 8) & 0xff, // call PlayMusic
                0x18, 0xea];                             // jr -22  (back to top)
    for (var i = 0; i < code.length; i++) mod._emulator_write_mem(e2, STUB + i, code[i]);
    mod._emulator_write_mem(e2, FLAG, 0);
    mod._emulator_set_PC(e2, STUB);
    stubSet = true;
  }

  // Ask the hidden instance to play song `id` from audio bank `bank` -- just fill
  // the mailbox; the stub picks it up. No forced PC change.
  function inject(id, bank) {
    if (!ready) return;
    mod._emulator_write_mem(e2, IDV, id & 0xff);
    mod._emulator_write_mem(e2, BANKV, bank & 0xff);
    mod._emulator_write_mem(e2, FLAG, 1);
    curId = id; curBank = bank;
  }

  // Read the hidden instance's freshly generated audio and schedule it. At 1x the
  // generation rate matches real time, so playback stays smooth.
  function pushAudio() {
    var now = ctx.currentTime;
    if (!startSec || startSec < now || startSec > now + 0.5) startSec = now + LAT;
    var buf = ctx.createBuffer(2, FRAMES, ctx.sampleRate);
    var c0 = buf.getChannelData(0), c1 = buf.getChannelData(1);
    for (var i = 0; i < FRAMES; i++) {
      c0[i] = (mod.HEAPU8[audioPtr + 2 * i] - 128) / 128;        // 8-bit unsigned -> centered float
      c1[i] = (mod.HEAPU8[audioPtr + 2 * i + 1] - 128) / 128;
    }
    var src = ctx.createBufferSource(); src.buffer = buf; src.connect(musicGain); src.start(startSec);
    startSec += FRAMES / ctx.sampleRate;
  }

  // Drive the hidden instance in real time (1x), independent of the visible game's
  // speed, so fast-forward never speeds the music up.
  function pump() {
    if (!running || !ready) return;
    raf = requestAnimationFrame(pump);
    var now = performance.now() / 1000;
    var dt = Math.min(Math.max(now - lastSec, 0), 0.25); lastSec = now;
    var tgt = mod._emulator_get_ticks_f64(e2) + dt * CPU;
    while (true) {
      var ev = mod._emulator_run_until_f64(e2, tgt);
      if (ev & EV_AUDIO) pushAudio();
      if (ev & EV_TICKS) break;
    }
  }

  // ---- follow the visible game's current song ----
  function syncSong() {
    var em = window.__emulator;
    if (!em || !em.module || em.e == null || typeof em.module._emulator_read_mem !== 'function') return;
    var m = em.module, e = em.e;
    var bank = m._emulator_read_mem(e, 0xc0ef) & 0xff;          // wAudioROMBank
    var id = 0;
    for (var c = 0; c < 4; c++) {                              // wChannelSoundIDs[CHAN1..4]
      var v = m._emulator_read_mem(e, 0xc026 + c) & 0xff;
      if (v >= MUS_LO && v <= MUS_HI) { id = v; break; }        // music ids only; ignore SFX/cries
    }
    if (ready && id && (id !== curId || bank !== curBank)) inject(id, bank);
  }

  // ---- live game state from emulator RAM (kept for the headless context test) ----
  function readState() {
    var em = window.__emulator;
    if (!em || !em.module || em.e == null) return null;
    var m = em.module;
    if (typeof m._emulator_read_mem !== 'function') return null;
    var rd = function (a) { return m._emulator_read_mem(em.e, a) & 0xff; };
    return { inBattle: rd(0xd057), trClass: rd(0xd031), curOpp: rd(0xd059),
             gym: rd(0xd05c), result: rd(0xcf0b), map: rd(0xd35e), tileset: rd(0xd367),
             streak: rd(0xdef0) };
  }
  function isBoss(c) {
    return (c >= 0x22 && c <= 0x28) || c === 0x1d ||
           c === 0x2c || c === 0x21 || c === 0x2e || c === 0x2f;
  }
  function pickTrack(s) {
    if (!s) return 'town';
    if (s.inBattle === 1 || s.inBattle === 2) {
      if (s.inBattle === 2 || s.curOpp >= 200) {
        var cls = s.trClass || (s.curOpp >= 200 ? s.curOpp - 200 : 0);
        if (cls === 0x19 || cls === 0x2a || cls === 0x2b) return 'rival';
        if (s.gym !== 0 || isBoss(cls)) return 'boss';
        return 'trainer';
      }
      return 'wild';
    }
    var t = s.tileset;
    if (t === 6 || t === 18) return 'centre';
    if (t === 17 || t === 11 || t === 15) return 'cave';
    if (t === 0 || t === 23) return (s.map <= 0x0a) ? 'town' : 'route';
    if (t === 3 || t === 9) return 'route';
    return 'centre';
  }
  function poll() {
    if (!running) return;
    var em = window.__emulator;
    if (em && em.module && em.e != null && typeof em.module._emulator_read_mem === 'function') {
      var st = em.module._emulator_read_mem(em.e, 0xdef0) & 0xff;  // wQuizStreak
      if (lastStreak === null) lastStreak = st;
      else if (st > lastStreak) sfx('correct');
      else if (st === 0 && lastStreak > 0) sfx('wrong');
      lastStreak = st;
    }
    syncSong();
  }

  // ---- SFX bus (correct/wrong answer + UI blips) ----
  var pulseCache = {};
  function pulse(duty) {
    if (pulseCache[duty]) return pulseCache[duty];
    var n = 28, real = new Float32Array(n), imag = new Float32Array(n);
    for (var k = 1; k < n; k++) imag[k] = (2 / (k * Math.PI)) * Math.sin(Math.PI * k * duty);
    var w = ctx.createPeriodicWave(real, imag);
    pulseCache[duty] = w; return w;
  }
  function midi(n) { return 440 * Math.pow(2, (n - 69) / 12); }
  function tone(dest, freq, t, dur, wave, vol) {
    var o = ctx.createOscillator(), g = ctx.createGain();
    if (typeof wave === 'string') o.type = wave; else o.setPeriodicWave(wave);
    o.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest);
    o.start(t); o.stop(t + dur + 0.03);
  }
  function ensure() {
    if (ctx) return;
    ctx = new AC();
    master = ctx.createGain(); master.gain.value = (window.__soundOn === false ? 0 : 0.6); master.connect(ctx.destination);
    musicGain = ctx.createGain(); musicGain.gain.value = 0.9; musicGain.connect(master);
    sfxGain = ctx.createGain(); sfxGain.gain.value = 0.7; sfxGain.connect(master);
  }
  function sfx(name) {
    if (window.__soundOn === false) return;
    ensure();
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch (e) {} }
    var t = ctx.currentTime + 0.01;
    if (name === 'ui') {
      tone(sfxGain, 880, t, 0.05, pulse(0.5), 0.16);
    } else if (name === 'correct') {
      [0, 4, 7, 12].forEach(function (o, i) { tone(sfxGain, midi(72 + o), t + i * 0.06, 0.13, pulse(0.5), 0.2); });
    } else if (name === 'wrong') {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sawtooth';
      o.frequency.setValueAtTime(220, t);
      o.frequency.exponentialRampToValueAtTime(85, t + 0.26);
      g.gain.setValueAtTime(0.22, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.3);
      o.connect(g); g.connect(sfxGain); o.start(t); o.stop(t + 0.32);
    }
  }
  window.__sfx = sfx;
  // A subtle blip when the player taps our overlay chrome (toolbar / menu).
  if (typeof document !== 'undefined') {
    document.addEventListener('click', function (e) {
      var t = e.target; if (!t || !t.closest) return;
      if (t.closest('#toolbar button, #menu button, .slot button')) sfx('ui');
    }, true);
  }

  // Lower the music while the read-aloud voice is speaking, then restore it, so
  // the spoken question is clear over the soundtrack.
  window.__musicDuck = function (down) {
    if (!master) return;
    master.gain.value = (window.__soundOn === false) ? 0 : (down ? 0.16 : 0.6);
  };

  window.__musicStart = function () {
    ensure();
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch (e) {} }
    master.gain.value = (window.__soundOn === false ? 0 : 0.6);
    if (running) return;
    running = true; lastStreak = null;
    if (!ready) boot();
    else { lastSec = performance.now() / 1000; startSec = 0; pump(); }
    if (!poller) poller = setInterval(poll, 200);
  };
  window.__musicStop = function () {
    running = false;
    if (raf) { cancelAnimationFrame(raf); raf = 0; }
    if (poller) { clearInterval(poller); poller = null; }
    if (master) master.gain.value = 0;
  };

  // Inspection hook (also used by the headless music test).
  window.__music = { pick: pickTrack, read: readState, get track() { return curId; } };

  // Browsers block audio until a user gesture; start/resume on the first tap/key.
  function kick() {
    if (window.__soundOn === false) return;
    if (window.__musicStart) window.__musicStart();
    if (ctx && ctx.state === 'suspended') { try { ctx.resume(); } catch (e) {} }
  }
  ['pointerdown', 'keydown', 'touchend'].forEach(function (ev) { window.addEventListener(ev, kick); });
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
  var btn = document.getElementById('btnFull');        // in the menu sheet
  var topBtn = document.getElementById('btnFullTop');  // in the top toolbar
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
  if (topBtn) topBtn.addEventListener('click', toggle);
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


# Learning visual aid: while a shape or colour question is on screen during a
# battle, draw the real shape (or colour swatches) over the empty top band of
# the Game Boy screen. The Game Boy itself is monochrome, so the colours/shapes
# are rendered here in the browser layer -- it reads the live tilemap (what is
# actually drawn on screen) and keyword-matches it, so it only appears for the
# relevant question and never interferes with the game.
VISUAL_JS = r"""
(function () {
  'use strict';
  var el = null;
  // Region of the 160x144 GB screen used for the aid (the empty top band; the
  // question box occupies rows 6-17). Tweak here to reposition.
  var GB = { x: 46, y: 3, w: 68, h: 40 };
  function dec(b) {
    if (b >= 0x80 && b <= 0x99) return String.fromCharCode(97 + (b - 0x80)); // A-Z
    if (b >= 0xa0 && b <= 0xb9) return String.fromCharCode(97 + (b - 0xa0)); // a-z
    if (b >= 0xf6 && b <= 0xff) return String.fromCharCode(48 + (b - 0xf6)); // 0-9
    return ' ';
  }
  function screenText() {
    var em = window.__emulator;
    if (!em || !em.module || em.e == null) return null;
    var m = em.module;
    if (typeof m._emulator_read_mem !== 'function') return null;
    // Only while in a battle -- that's where the quiz lives. Avoids matching
    // shape/colour words that happen to appear in the overworld.
    if ((m._emulator_read_mem(em.e, 0xd057) & 0xff) === 0) return null;
    // Read ONLY the question lines (tilemap rows 7-8). The answers live on rows
    // 9+, so this both ignores them and never reveals the answer (e.g. "Sun is
    // a?" whose answer is "star").
    var s = '';
    for (var i = 140; i < 180; i++) s += dec(m._emulator_read_mem(em.e, 0xc3a0 + i) & 0xff);
    return s;
  }
  var SHAPES = [['triangle', 3], ['rectangle', 'rect'], ['square', 4],
    ['pentagon', 5], ['hexagon', 6], ['octagon', 8], ['diamond', 'diamond'],
    ['circle', 'circle'], ['oval', 'oval'], ['star', 'star']];
  var COLORS = { red: '#e23b3b', orange: '#f3922b', yellow: '#f4d534',
    green: '#3fa950', blue: '#2f6fd6', purple: '#8a3fc0', pink: '#ef82b6',
    brown: '#8a5a2b', black: '#222', white: '#fafafa', gray: '#9aa0a6',
    grey: '#9aa0a6' };
  function shapeSVG(kind) {
    var poly = { 3: '50,8 92,88 8,88', 4: '14,14 86,14 86,86 14,86',
      rect: '6,26 94,26 94,74 6,74', 5: '50,6 92,38 76,92 24,92 8,38',
      6: '28,7 72,7 95,50 72,93 28,93 5,50',
      8: '34,6 66,6 92,30 92,66 66,92 34,92 8,66 8,30',
      diamond: '50,6 92,50 50,94 8,50' };
    if (kind === 'circle') return '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" fill="#dbeafe" stroke="#1b65c4" stroke-width="8"/></svg>';
    if (kind === 'oval') return '<svg viewBox="0 0 100 100"><ellipse cx="50" cy="50" rx="45" ry="30" fill="#dbeafe" stroke="#1b65c4" stroke-width="8"/></svg>';
    if (kind === 'star') return '<svg viewBox="0 0 100 100"><polygon points="50,5 61,38 96,38 68,59 79,94 50,72 21,94 32,59 4,38 39,38" fill="#f7d44b" stroke="#c79a16" stroke-width="5" stroke-linejoin="round"/></svg>';
    return '<svg viewBox="0 0 100 100"><polygon points="' + poly[kind] + '" fill="#dbeafe" stroke="#1b65c4" stroke-width="8" stroke-linejoin="round"/></svg>';
  }
  function has(txt, word) { return new RegExp('\\b' + word + '\\b').test(txt); }
  function detect(txt) {
    if (/\b(rhyme|rhymes|spell|spelled|letter)\b/.test(txt)) return null; // word puzzles, not shapes
    if (/\b(mix|mixed|makes|make|made|plus|combine|combined|together|and)\b/.test(txt)) {
      var found = [];
      for (var k in COLORS) { var p = txt.search(new RegExp('\\b' + k + '\\b'));
        if (p >= 0) found.push([k, p]); }
      found.sort(function (a, b) { return a[1] - b[1]; });
      if (found.length >= 2) return { type: 'color', a: found[0][0], b: found[1][0] };
    }
    for (var i = 0; i < SHAPES.length; i++)
      if (has(txt, SHAPES[i][0])) return { type: 'shape', kind: SHAPES[i][1] };
    return null;
  }
  function render(d) {
    if (d.type === 'shape') { el.innerHTML = '<div class="vaCard">' + shapeSVG(d.kind) + '</div>'; return; }
    el.innerHTML = '<div class="vaCard"><span class="swatch" style="background:' + COLORS[d.a]
      + '"></span><span class="op">+</span><span class="swatch" style="background:' + COLORS[d.b] + '"></span></div>';
  }
  function place() {
    var c = document.getElementById('mainCanvas'); if (!c || !el) return;
    var r = c.getBoundingClientRect(), sx = r.width / 160, sy = r.height / 144;
    el.style.left = (r.left + GB.x * sx) + 'px';
    el.style.top = (r.top + GB.y * sy) + 'px';
    el.style.width = (GB.w * sx) + 'px';
    el.style.height = (GB.h * sy) + 'px';
  }
  var lastKey = '';
  function tick() {
    if (!el) el = document.getElementById('visualAid');
    if (!el) return;
    var d = null;
    try { var t = screenText(); d = t ? detect(t) : null; } catch (e) { d = null; }
    var key = d ? JSON.stringify(d) : '';
    if (key !== lastKey) { lastKey = key; if (d) render(d); }
    if (d) { place(); el.classList.add('show'); } else el.classList.remove('show');
  }
  setInterval(tick, 250);
  window.addEventListener('resize', place);
  window.addEventListener('scroll', place, true);
  window.__visualAid = { tick: tick, detect: detect };
})();
"""


# Parent "Report Card": a player-side learning tracker. It reads the live quiz
# state from RAM -- the answer streak (up = a correct answer, reset to 0 = a
# miss), the question's subject id, the grade (from badge count), and the
# question text -- and logs each answer to the device (localStorage). A
# "Report Card" button in the menu shows per-subject and per-grade accuracy, the
# toughest questions, and recent activity. Entirely in the browser layer; the
# ROM is untouched.
PROGRESS_JS = r"""
(function () {
  'use strict';
  var KEY = 'pq_report_v1';
  var SUBJ = ['English', 'Science', 'Gen. Knowledge', 'Shapes & Colors', 'Math'];
  function blank() { return { subj: {}, grade: {}, q: {}, correct: 0, wrong: 0, best: 0, recent: [] }; }
  var st; try { st = JSON.parse(localStorage.getItem(KEY)) || blank(); } catch (e) { st = blank(); }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} }
  function rdfn() {
    var em = window.__emulator;
    if (!em || !em.module || em.e == null || typeof em.module._emulator_read_mem !== 'function') return null;
    return function (a) { return em.module._emulator_read_mem(em.e, a) & 0xff; };
  }
  function dec(b) {
    if (b === 0x7f) return ' ';
    if (b >= 0x80 && b <= 0x99) return String.fromCharCode(65 + b - 0x80);
    if (b >= 0xa0 && b <= 0xb9) return String.fromCharCode(97 + b - 0xa0);
    if (b >= 0xf6 && b <= 0xff) return String.fromCharCode(48 + b - 0xf6);
    return ({ 0xe6: '?', 0xe7: '!', 0xe8: '.' })[b] || '';
  }
  function popcount(x) { var n = 0; while (x) { n += x & 1; x >>= 1; } return n; }
  function readQ(rd) { var s = ''; for (var i = 0; i < 18; i++) { var b = rd(0xda92 + i); if (b === 0x50) break; s += dec(b); } return s.trim(); } // wQuizQStr
  function readAns(rd) { var s = ''; for (var i = 0; i < 16; i++) { var b = rd(0xdaa6 + i); if (b === 0x50) break; s += dec(b); } return s.trim(); } // wQuizA0 = correct answer
  function record(subj, grade, q, ok, ans) {
    st.subj[subj] = st.subj[subj] || { c: 0, w: 0 };
    st.grade[grade] = st.grade[grade] || { c: 0, w: 0 };
    if (ok) { st.subj[subj].c++; st.grade[grade].c++; st.correct++; }
    else { st.subj[subj].w++; st.grade[grade].w++; st.wrong++; }
    if (q && q.length >= 2) {
      var r = st.q[q] || { c: 0, w: 0 };
      r.s = subj; r.g = grade; if (ans) r.a = ans;          // remember subject/grade/answer for drill-down
      if (ok) r.c++; else r.w++;
      st.q[q] = r;
    }
    st.recent.unshift({ s: subj, g: grade, ok: ok, t: Date.now() });
    if (st.recent.length > 40) st.recent.pop();
    save();
  }
  var lastStreak = null;
  function poll() {
    var rd = rdfn(); if (!rd) return;
    var streak = rd(0xdef0);                       // wQuizStreak (now first-try mastery)
    if (lastStreak === null) { lastStreak = streak; return; }
    if (streak > st.best) st.best = streak;
    if (streak > lastStreak || (streak === 0 && lastStreak > 0)) {
      var ok = streak > lastStreak;                 // streak up = first-try correct
      var subj = rd(0xdef4); if (subj > 4) subj = 4; // wQuizLastSubject
      var grade = Math.min(5, (popcount(rd(0xd356)) >> 1) + 1); // wObtainedBadges -> grade
      record(subj, grade, readQ(rd), ok, readAns(rd));
    }
    lastStreak = streak;
  }
  setInterval(poll, 200);

  // ---- Report Card UI ----
  function pct(o) { var t = o.c + o.w; return t ? Math.round(100 * o.c / t) : 0; }
  function bar(o, label) {
    var t = o.c + o.w;
    return '<div class="pgRow"><span class="pgLbl">' + label + '</span>'
      + '<span class="pgBar"><i style="width:' + pct(o) + '%"></i></span>'
      + '<span class="pgPct">' + pct(o) + '% <small>(' + t + ')</small></span></div>';
  }
  var TIPS = [
    'Read together daily. Practise opposites & plurals with picture cards and simple games.',
    'Watch short nature clips and talk about animals, weather, and the body.',
    'Drill calendar & time facts — days, months, hours, and reading a clock.',
    'Use shape blocks and mix paint colours so shapes & colour-mixing feel real.',
    'Five minutes a day of number bonds and times tables with counters or fingers.'
  ];
  function clsOf(p) { return p >= 80 ? 'good' : p >= 50 ? 'mid' : 'low'; }
  function statTile(label, val, klass) {
    return '<div class="pgTile"><div class="pgTileVal ' + (klass || '') + '">' + val + '</div><div class="pgTileLbl">' + label + '</div></div>';
  }
  function missedList(pred) {
    return Object.keys(st.q).map(function (k) { return [k, st.q[k]]; })
      .filter(function (x) { return x[1].w > 0 && pred(x[1]); })
      .sort(function (a, b) { return b[1].w - a[1].w; });
  }
  function qLine(x, showCount) {
    return '<div class="pgQ"><span class="pgQt">' + x[0] + '</span>'
      + (x[1].a ? '<span class="pgA">' + x[1].a + '</span>' : '')
      + (showCount ? '<span class="pgM">&times;' + x[1].w + '</span>' : '') + '</div>';
  }
  function group(key, o, label, list) {
    var p = pct(o), k = clsOf(p);
    var d = list.length ? list.map(function (x) { return qLine(x, true); }).join('') : '<div class="pgNone">No misses here &mdash; nice!</div>';
    return '<div class="pgItem"><div class="pgRow pgClick" data-k="' + key + '">'
      + '<span class="pgChev">&#8250;</span><span class="pgLbl">' + label + '</span>'
      + '<span class="pgBar ' + k + '"><i style="width:' + p + '%"></i></span>'
      + '<span class="pgPct ' + k + '">' + p + '%</span><span class="pgN">' + (o.c + o.w) + '</span></div>'
      + '<div class="pgDetailWrap" id="d-' + key + '">' + d + '</div></div>';
  }
  function render() {
    var tot = st.correct + st.wrong, h = '', s, g;
    if (!tot) return '<div class="pgEmpty"><div class="pgEmoji">&#128202;</div>'
      + '<p class="pgEmptyT">No answers yet</p>'
      + '<p class="pgDim">Play a few quiz battles, then come back &mdash; you\'ll see which subjects, grades and questions your child finds tricky, plus tips to help.</p></div>';
    var acc = Math.round(100 * st.correct / tot);
    h += '<div class="pgStats">' + statTile('Answered', tot, '') + statTile('First&#8209;try', acc + '%', clsOf(acc)) + statTile('Best streak', st.best, '') + '</div>';
    h += '<div class="pgSec">By subject<span>tap to see misses</span></div>';
    for (s = 0; s < 5; s++) if (st.subj[s]) h += group('s' + s, st.subj[s], SUBJ[s], missedList((function (sv) { return function (q) { return q.s === sv; }; })(s)));
    h += '<div class="pgSec">By grade<span>tap to see misses</span></div>';
    for (g = 1; g <= 5; g++) if (st.grade[g]) h += group('g' + g, st.grade[g], 'Grade ' + g, missedList((function (gv) { return function (q) { return q.g === gv; }; })(g)));
    var weak = -1, wp = 101;
    for (s = 0; s < 5; s++) { var o = st.subj[s]; if (o && (o.c + o.w) >= 3) { var p = pct(o); if (p < wp) { wp = p; weak = s; } } }
    h += '<div class="pgSec">How to help</div>';
    if (weak >= 0) {
      h += '<div class="pgPlan"><div class="pgPlanHd"><span>Focus area</span><b>' + SUBJ[weak] + '</b><span class="pgPct ' + clsOf(wp) + '">' + wp + '%</span></div>'
        + '<div class="pgPlanTip">' + TIPS[weak] + '</div>';
      var ml = missedList((function (sv) { return function (q) { return q.s === sv; }; })(weak)).slice(0, 5);
      if (ml.length) { h += '<div class="pgPlanSub">Review these together</div>' + ml.map(function (x) { return qLine(x, false); }).join(''); }
      h += '</div>';
    } else h += '<div class="pgNone">Keep playing &mdash; after a few more questions I\'ll point out what to focus on.</div>';
    return h;
  }
  function build() {
    if (document.getElementById('pqReport')) return;
    var m = document.createElement('div'); m.id = 'pqReport';
    m.innerHTML = '<div id="pqReportCard"><div id="pqReportHead"><span>&#128202; Report Card</span>'
      + '<button id="pqReportClose" title="Close">&#10005;</button></div>'
      + '<div id="pqReportBody"></div>'
      + '<div id="pqReportFoot"><button id="pqReportReset">Reset progress</button></div></div>';
    document.body.appendChild(m);
    m.addEventListener('click', function (e) { if (e.target === m) hide(); });
    document.getElementById('pqReportClose').addEventListener('click', hide);
    document.getElementById('pqReportReset').addEventListener('click', function () {
      if (confirm('Clear all recorded progress?')) { st = blank(); save(); document.getElementById('pqReportBody').innerHTML = render(); }
    });
    // tap a subject/grade row to expand its missed questions
    document.getElementById('pqReportBody').addEventListener('click', function (e) {
      var row = e.target.closest && e.target.closest('.pgClick'); if (!row) return;
      row.classList.toggle('open');
    });
    // a button in the menu sheet (falls back to the top toolbar)
    var host = document.getElementById('menu_body') || document.getElementById('toolbar');
    if (host) {
      var card = document.createElement('section'); card.className = 'card';
      card.innerHTML = '<h3>Progress</h3><button id="pqReportOpen" class="pqOpenBtn">&#128202; Report Card</button>';
      host.insertBefore(card, host.firstChild);
      document.getElementById('pqReportOpen').addEventListener('click', show);
    }
  }
  function show() { var b = document.getElementById('pqReportBody'); if (b) b.innerHTML = render(); document.getElementById('pqReport').classList.add('show'); }
  function hide() { var r = document.getElementById('pqReport'); if (r) r.classList.remove('show'); }
  if (document.readyState !== 'loading') build(); else document.addEventListener('DOMContentLoaded', build);
  window.__report = { stats: function () { return st; }, render: render, poll: poll, record: record, reset: function () { st = blank(); save(); } };
})();
"""


# High-quality read-aloud. Speaks the quiz QUESTION and ANSWER CHOICES decoded
# straight from the game's RAM (the real on-screen text), using the best natural
# voice the device offers (male/female selectable). It sanitizes first -- math
# symbols become words ("3 x 4" -> "3 times 4"), exclamation marks and stray
# symbols are dropped (never says "exclamation mark"), a few abbreviations are
# expanded -- so it sounds like a friendly teacher, not a robot reading
# punctuation or emojis. The music ducks while it speaks. Built for early readers
# (grade 1-2) who can play by ear.
READALOUD_JS = r"""
(function () {
  var synth = window.speechSynthesis || null;
  // RAM addresses (pokered.sym): the quiz strings + state the engine writes.
  var A_Q = 0xda92, A_ANS0 = 0xdaa6, A_STRIDE = 0x14;
  var A_NUM = 0xdee7, A_ROT = 0xdeea, A_INBATTLE = 0xd057;

  // Reverse Game Boy charmap (tile code -> character) for the chars quiz text uses.
  var CMAP = {};
  CMAP[0x7f] = ' '; CMAP[0x9c] = ':'; CMAP[0xe3] = '-';
  CMAP[0xe6] = '?'; CMAP[0xe7] = '!'; CMAP[0xe8] = '.'; CMAP[0xf4] = ','; CMAP[0xf3] = '/';
  for (var i = 0; i < 26; i++) { CMAP[0x80 + i] = String.fromCharCode(65 + i); CMAP[0xa0 + i] = String.fromCharCode(97 + i); }
  for (var d = 0; d < 10; d++) CMAP[0xf6 + d] = String(d);

  function rd(a) {
    var em = window.__emulator;
    if (!em || !em.module || em.e == null || typeof em.module._emulator_read_mem !== 'function') return -1;
    return em.module._emulator_read_mem(em.e, a) & 0xff;
  }
  function decodeAt(addr) {            // read a '@'-terminated GB string -> JS text
    var s = '';
    for (var i = 0; i < 19; i++) {
      var b = rd(addr + i);
      if (b < 0 || b === 0x50) break;  // 0x50 = '@' terminator
      var c = CMAP[b];
      if (c === undefined) return '';  // non-text byte -> stale/box data, not a real string
      s += c;
    }
    return s;
  }

  // Turn quiz text into something a voice says naturally.
  var ABBR = { deg: 'degrees', hr: 'hours', hrs: 'hours', min: 'minutes', mins: 'minutes',
               yr: 'year', sept: 'September', feb: 'February', sat: 'Saturday', sun: 'Sunday' };
  function speakable(t) {
    if (!t) return '';
    t = t.replace(/(\d)\s*x\s*(\d)/gi, '$1 times $2');      // 3 x 4 -> 3 times 4
    t = t.replace(/(\d)\s*-\s*(\d)/g, '$1 minus $2');       // 8 - 3 -> 8 minus 3
    t = t.replace(/(\d)(\s*)\/(\s*)(\d)/g, function (m, a, s1, s2, b) {
      return (s1 || s2) ? (a + ' divided by ' + b) : (a + ' over ' + b);  // spaced=divide, tight=fraction
    });
    t = t.replace(/\+/g, ' plus ');
    t = t.replace(/=/g, ' equals ');
    t = t.replace(/!/g, '');                                // never read exclamation marks
    t = t.replace(/[^A-Za-z0-9 ?.,]/g, ' ');                // drop stray symbols
    t = t.replace(/[A-Za-z]+/g, function (w) { var k = w.toLowerCase(); return ABBR[k] || w; });
    return t.replace(/\s+/g, ' ').trim();
  }

  // Full spoken prompt: question, then the choices in on-screen (rotated) order.
  function buildPrompt() {
    var n = rd(A_NUM);
    if (n < 2 || n > 6) return '';
    if (rd(A_INBATTLE) === 0) return '';                   // the quiz only shows in battle
    var q = decodeAt(A_Q);
    if (q.replace(/[^A-Za-z]/g, '').length < 2) return '';  // not a real question
    var rot = rd(A_ROT); if (rot < 0) rot = 0;
    var opts = [];
    for (var s = 0; s < n; s++) {
      var o = speakable(decodeAt(A_ANS0 + ((s + rot) % n) * A_STRIDE));
      if (o) opts.push(o);
    }
    var qs = speakable(q);
    if (!opts.length) return qs;
    var list = opts.length > 1 ? opts.slice(0, -1).join(', ') + ', or ' + opts[opts.length - 1] : opts[0];
    return qs + ' Is it: ' + list + '?';
  }

  // ---- voice selection (quality + gender) ----
  var gender = 'female';
  try { var gv = localStorage.getItem('pq_voice'); if (gv === 'male' || gv === 'female') gender = gv; } catch (e) {}
  var FEMALE = /\b(aria|jenny|libby|sonia|emma|ava|natasha|samantha|zira|susan|hazel|heera|neerja|salli|joanna|kendra|female|woman|girl)\b/i;
  var MALE = /\b(guy|ryan|david|mark|george|james|brian|matthew|ravi|prabhat|fred|daniel|male|man|boy)\b/i;
  var btnRead = document.getElementById('btnRead');
  var btnVoice = document.getElementById('btnVoice');
  var btnAgain = document.getElementById('btnReadAgain');
  function enVoices() { return (synth ? synth.getVoices() : []).filter(function (v) { return /^en(-|_|$)/i.test(v.lang); }); }
  function score(v) {
    var n = v.name.toLowerCase(), s = 0;
    if (/natural|neural|premium|enhanced|wavenet|online|siri/.test(n)) s += 100;
    if (/google/.test(n)) s += 60;
    if (/microsoft/.test(n)) s += 25;
    if (v.localService === false) s += 12;
    var l = v.lang.toLowerCase();
    if (/en[-_]us/.test(l)) s += 15; else if (/en[-_](gb|in|au)/.test(l)) s += 10;
    return s;
  }
  var voice = null;
  function pickVoice() {
    var vs = enVoices();
    if (!vs.length) { voice = null; return; }
    var want = (gender === 'male') ? MALE : FEMALE;
    var pool = vs.filter(function (v) { return want.test(v.name); });
    if (!pool.length) pool = vs;
    pool.sort(function (a, b) { return score(b) - score(a); });
    voice = pool[0];
    if (btnVoice && voice) btnVoice.textContent = '🎤 ' + voice.name.replace(/Microsoft |Google /, '').slice(0, 14);
  }
  if (synth && 'onvoiceschanged' in synth) synth.onvoiceschanged = pickVoice;

  function say(text, mood) {
    if (!synth || !text) return;
    try { synth.cancel(); } catch (e) {}
    var u = new SpeechSynthesisUtterance(text);
    if (voice) u.voice = voice;
    u.lang = (voice && voice.lang) || 'en-US';
    u.rate = 0.96; u.pitch = 1.06; u.volume = 1.0;         // warm, slightly slow for a child
    if (mood === 'happy') { u.rate = 1.0; u.pitch = 1.22; }
    else if (mood === 'soft') { u.rate = 0.92; u.pitch = 1.0; }
    u.onstart = function () { if (window.__musicDuck) window.__musicDuck(true); };
    u.onend = u.onerror = function () { if (window.__musicDuck) window.__musicDuck(false); };
    synth.speak(u);
  }

  // ---- controls ----
  var on = true;
  try { if (localStorage.getItem('pq_read') === '0') on = false; } catch (e) {}
  function syncBtn() { if (btnRead) { btnRead.textContent = on ? '🗣 Read: On' : '🔇 Read: Off'; btnRead.classList.toggle('on', on); } }
  if (btnRead) btnRead.addEventListener('click', function () {
    on = !on; try { localStorage.setItem('pq_read', on ? '1' : '0'); } catch (e) {}
    if (!on) { try { synth.cancel(); } catch (e) {} if (window.__musicDuck) window.__musicDuck(false); }
    syncBtn();
  });
  if (btnVoice) btnVoice.addEventListener('click', function () {
    gender = (gender === 'female') ? 'male' : 'female';
    try { localStorage.setItem('pq_voice', gender); } catch (e) {}
    pickVoice();
    say(gender === 'male' ? 'Hi! I will read for you.' : 'Hello! I will read for you.');
  });
  if (btnAgain) btnAgain.addEventListener('click', function () { var p = buildPrompt(); if (p) say(p); });

  // ---- poll for a new question and read it once ----
  var lastQ = '';
  function poll() {
    if (!on || !synth) return;
    if (rd(A_INBATTLE) === 0) { lastQ = ''; return; }      // left battle -> allow re-reading later
    var n = rd(A_NUM); if (n < 2 || n > 6) return;
    var q = decodeAt(A_Q);
    if (q.replace(/[^A-Za-z]/g, '').length < 2) return;
    if (q === lastQ) return;                               // already read this question
    lastQ = q;
    var p = buildPrompt();
    if (p) say(p);
  }

  // Voices load asynchronously; retry a few times, then poll for questions.
  var tries = 0, warm = setInterval(function () { pickVoice(); if (voice || tries++ > 20) clearInterval(warm); }, 200);
  pickVoice(); syncBtn();
  if (synth) setInterval(poll, 300);

  // Inspection hook for the headless text-pipeline test.
  window.__readaloud = { decodeAt: decodeAt, speakable: speakable, buildPrompt: buildPrompt, pickVoice: pickVoice };
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
        MUSIC_JS,
        SOUND_JS,
        PAUSE_JS,
        MENU_JS,
        FS_JS,
        VISUAL_JS,
        PROGRESS_JS,
        READALOUD_JS,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print("Wrote %s (%.2f MB)" % (args.out, size_mb))
    print("ROM: %s  |  WASM: %s" % (args.rom, binjgb_wasm))
    print("Open it in any browser -- no internet needed.")


if __name__ == "__main__":
    main()
