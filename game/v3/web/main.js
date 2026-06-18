// =============================================================================
// Quiz Quest v3 -- BROWSER FRONT-END (the "eyes and hands").
// Draws the real town (composed from the Game Pack's authentic tiles) with a
// camera that follows the hero, takes keyboard + touch input, and shows the
// quiz. It holds NO rules -- it just shows the brain's state and forwards input.
// =============================================================================
import { newGame, step, availableInputs, saveGame, loadGame } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

const SAVE_KEY = "quizquest3_save";
const GB_W = 160, GB_H = 144, SCALE = 4;
let state, ctx, mapCanvas, tilesetImg, spriteImg, overlay, readAloud = true, lastSpoken = "";

function boot() {
  document.body.innerHTML =
    '<div id="qq"><div id="bar"><span class="logo">⭐ Quiz Quest</span><span class="grow"></span>' +
    '<button id="btnRead" class="tb">🔊 Read aloud</button><button id="btnReset" class="tb">↻</button></div>' +
    '<div id="stage"><canvas id="cv" width="' + (GB_W * SCALE) + '" height="' + (GB_H * SCALE) + '"></canvas>' +
    '<div id="ov"></div></div>' +
    '<div id="pad"><div class="dpad"><button class="d u" data-mv="up">▲</button>' +
    '<button class="d l" data-mv="left">◀</button><button class="d r" data-mv="right">▶</button>' +
    '<button class="d dn" data-mv="down">▼</button></div>' +
    '<div class="ab"><button id="bA" class="rb">A</button></div></div></div>';
  const cv = document.getElementById("cv"); ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = false;
  overlay = document.getElementById("ov");
  document.getElementById("btnRead").onclick = e => { readAloud = !readAloud; e.target.classList.toggle("off", !readAloud); if (!readAloud) stopSpeak(); };
  document.getElementById("btnReset").onclick = () => { if (confirm("Start over?")) { state = newGame(PACK, now()); persist(); sync(); } };
  document.querySelectorAll("[data-mv]").forEach(b => b.onclick = () => onMove(b.getAttribute("data-mv")));
  document.getElementById("bA").onclick = onA;

  let saved = null; try { saved = localStorage.getItem(SAVE_KEY); } catch (e) {}
  state = saved ? loadGame(saved, PACK, now()) : newGame(PACK, now());

  // load the real art, compose the map once, then start
  let loaded = 0; const done = () => { if (++loaded === 2) { composeMap(); bindKeys(); requestAnimationFrame(loop); sync(); } };
  tilesetImg = new Image(); tilesetImg.onload = done; tilesetImg.src = PACK.tilesetURL;
  spriteImg = new Image(); spriteImg.onload = done; spriteImg.src = PACK.spriteURL;
}
function now() { return (Date.now() >>> 0) || 1; }
function persist() { try { localStorage.setItem(SAVE_KEY, saveGame(state)); } catch (e) {} }
function send(input) { try { step(state, PACK, input); } catch (e) { console.error(e); } persist(); sync(); }

// compose the whole town once into an offscreen canvas (real tiles)
function composeMap() {
  const T = PACK.tile, B = PACK.block, per = PACK.tilesPerRow;
  mapCanvas = document.createElement("canvas");
  mapCanvas.width = PACK.w * B * T; mapCanvas.height = PACK.h * B * T;
  const mc = mapCanvas.getContext("2d"); mc.imageSmoothingEnabled = false;
  for (let my = 0; my < PACK.h; my++) for (let mx = 0; mx < PACK.w; mx++) {
    const bt = PACK.blocks[PACK.map[my * PACK.w + mx]];
    for (let ty = 0; ty < B; ty++) for (let tx = 0; tx < B; tx++) {
      const id = bt[ty * B + tx];
      mc.drawImage(tilesetImg, (id % per) * T, ((id / per) | 0) * T, T, T,
        (mx * B + tx) * T, (my * B + ty) * T, T, T);
    }
  }
}

function onMove(dir) { if (state.mode === "overworld") send({ type: "move", dir }); }
function onA() {
  if (state.mode === "result") send({ type: "confirm" });
  else if (state.mode === "overworld") send({ type: "move", dir: state.facing });
}
function bindKeys() {
  addEventListener("keydown", e => {
    const k = e.key.toLowerCase();
    if (["arrowup", "w"].includes(k)) { onMove("up"); e.preventDefault(); }
    else if (["arrowdown", "s"].includes(k)) { onMove("down"); e.preventDefault(); }
    else if (["arrowleft", "a"].includes(k)) { onMove("left"); e.preventDefault(); }
    else if (["arrowright", "d"].includes(k)) { onMove("right"); e.preventDefault(); }
    else if (["z", "enter", " "].includes(k)) { onA(); e.preventDefault(); }
    else if (state.mode === "quiz" && /^[1-6]$/.test(k)) { const i = +k - 1; if (i < state.asked.options.length) send({ type: "answer", index: i }); }
  });
}

function loop() { draw(); requestAnimationFrame(loop); }
function draw() {
  if (!mapCanvas) return;
  const px = state.cx * 16, py = state.cy * 16;
  let camX = px + 8 - GB_W / 2, camY = py + 8 - GB_H / 2;
  camX = Math.max(0, Math.min(camX, mapCanvas.width - GB_W));
  camY = Math.max(0, Math.min(camY, mapCanvas.height - GB_H));
  ctx.fillStyle = "#9bbc0f"; ctx.fillRect(0, 0, GB_W * SCALE, GB_H * SCALE);
  ctx.drawImage(mapCanvas, camX, camY, GB_W, GB_H, 0, 0, GB_W * SCALE, GB_H * SCALE);
  // player (real sprite, frame 0), drawn at its map position relative to camera
  ctx.drawImage(spriteImg, 0, 0, 16, 16, (px - camX) * SCALE, (py - camY) * SCALE, 16 * SCALE, 16 * SCALE);
}

function sync() {
  let h = "";
  if (state.mode === "quiz") {
    const a = state.asked, clk = a.clock ? ` <span class="clk">🕐 ${a.clock} o'clock</span>` : "";
    h = '<div class="box"><p class="q">' + esc(a.text) + clk + '</p><div class="opts">' +
      a.options.map((o, i) => `<button class="opt" data-ans="${i}">${esc(o)}</button>`).join("") +
      '</div>' + (a.attempts > 0 ? '<p class="hint">💡 ' + esc(a.hint) + '</p>' : '') + '</div>';
  } else if (state.mode === "result") {
    const r = state.result;
    const msg = r.win ? (r.firstTry ? "🌟 Correct! Great job!" : "✅ Correct! Well done!")
                      : ("❌ The answer was " + esc(r.correctText) + ". Keep going!");
    h = '<div class="box"><p>' + msg + '</p><button class="opt go" id="bGo">OK ▶</button></div>';
  }
  overlay.innerHTML = h;
  overlay.querySelectorAll("[data-ans]").forEach(b => b.onclick = () => send({ type: "answer", index: +b.getAttribute("data-ans") }));
  const go = document.getElementById("bGo"); if (go) go.onclick = () => send({ type: "confirm" });
  maybeSpeak();
}
function esc(s) { return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

function maybeSpeak() {
  if (!readAloud || state.mode !== "quiz") { lastSpoken = ""; return; }
  const a = state.asked, key = a.text + "|" + a.attempts; if (key === lastSpoken) return; lastSpoken = key;
  speak(a.text + ". The choices are: " + a.options.join(", ") + (a.attempts > 0 ? ". Hint: " + a.hint : ""));
}
function speak(t) { try { const s = speechSynthesis; if (!s) return; s.cancel(); const u = new SpeechSynthesisUtterance(t.replace(/[*_#~`]/g, "")); u.rate = .95; u.pitch = 1.05; s.speak(u); } catch (e) {} }
function stopSpeak() { try { speechSynthesis && speechSynthesis.cancel(); } catch (e) {} }

if (document.readyState !== "loading") boot(); else addEventListener("DOMContentLoaded", boot);
