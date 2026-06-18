// =============================================================================
// Quiz Quest v3 -- BROWSER FRONT-END (eyes + hands). Draws the real map with a
// smooth-scrolling camera, animates walking (no teleporting), shows wild-grass
// battles with the creature sprite + the quiz, takes keyboard + touch, reads
// aloud. No rules live here -- it just shows the brain's state.
// =============================================================================
import { newGame, step, availableInputs, saveGame, loadGame } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

const SAVE_KEY = "quizquest3_save", GB_W = 160, GB_H = 144, SCALE = 4, WALK_SPD = 2;
let state, ctx, mapCanvas, tilesetImg, spriteImg, creatureImgs = {}, overlay;
let rx = 0, ry = 0, readAloud = true, lastSpoken = "";

function boot() {
  document.body.innerHTML =
    '<div id="qq"><div id="bar"><span class="logo">⭐ Quiz Quest</span><span class="grow"></span>' +
    '<button id="btnRead" class="tb">🔊 Read aloud</button><button id="btnReset" class="tb">↻</button></div>' +
    '<div id="stage"><canvas id="cv" width="' + GB_W * SCALE + '" height="' + GB_H * SCALE + '"></canvas><div id="ov"></div></div>' +
    '<div id="pad"><div class="dpad"><button class="d u" data-mv="up">▲</button><button class="d l" data-mv="left">◀</button>' +
    '<button class="d r" data-mv="right">▶</button><button class="d dn" data-mv="down">▼</button></div>' +
    '<div class="ab"><button id="bA" class="rb">A</button></div></div></div>';
  ctx = document.getElementById("cv").getContext("2d"); ctx.imageSmoothingEnabled = false;
  overlay = document.getElementById("ov");
  document.getElementById("btnRead").onclick = e => { readAloud = !readAloud; e.target.classList.toggle("off", !readAloud); if (!readAloud) stop(); };
  document.getElementById("btnReset").onclick = () => { if (confirm("Start over?")) { state = newGame(PACK, now()); rx = state.cx * 16; ry = state.cy * 16; persist(); sync(); } };
  document.querySelectorAll("[data-mv]").forEach(b => b.onclick = () => onMove(b.getAttribute("data-mv")));
  document.getElementById("bA").onclick = onA;

  let saved = null; try { saved = localStorage.getItem(SAVE_KEY); } catch (e) {}
  state = saved ? loadGame(saved, PACK, now()) : newGame(PACK, now());
  rx = state.cx * 16; ry = state.cy * 16;

  let need = 2 + Object.keys(PACK.creatures || {}).length, got = 0;
  const done = () => { if (++got === need) { composeMap(); bindKeys(); requestAnimationFrame(loop); sync(); } };
  tilesetImg = new Image(); tilesetImg.onload = done; tilesetImg.src = PACK.tilesetURL;
  spriteImg = new Image(); spriteImg.onload = done; spriteImg.src = PACK.spriteURL;
  for (const k in (PACK.creatures || {})) { const im = new Image(); im.onload = done; im.src = PACK.creatures[k]; creatureImgs[k] = im; }
}
const now = () => (Date.now() >>> 0) || 1;
const persist = () => { try { localStorage.setItem(SAVE_KEY, saveGame(state)); } catch (e) {} };
const moving = () => rx !== state.cx * 16 || ry !== state.cy * 16;
function send(input) { try { step(state, PACK, input); } catch (e) { console.error(e); } persist(); sync(); }

function composeMap() {
  const T = PACK.tile, B = PACK.block, per = PACK.tilesPerRow;
  mapCanvas = document.createElement("canvas");
  mapCanvas.width = PACK.w * B * T; mapCanvas.height = PACK.h * B * T;
  const mc = mapCanvas.getContext("2d"); mc.imageSmoothingEnabled = false;
  for (let my = 0; my < PACK.h; my++) for (let mx = 0; mx < PACK.w; mx++) {
    const bt = PACK.blocks[PACK.map[my * PACK.w + mx]];
    for (let ty = 0; ty < B; ty++) for (let tx = 0; tx < B; tx++) {
      const id = bt[ty * B + tx];
      mc.drawImage(tilesetImg, (id % per) * T, ((id / per) | 0) * T, T, T, (mx * B + tx) * T, (my * B + ty) * T, T, T);
    }
  }
}

function onMove(dir) { if (state.mode === "overworld" && !moving()) send({ type: "move", dir }); }
function onA() {
  if (state.mode === "battle") { const b = state.battle; if (b.phase !== "quiz") send({ type: "confirm" }); }
  else if (state.mode === "overworld" && !moving()) send({ type: "move", dir: state.facing });
}
function bindKeys() {
  addEventListener("keydown", e => {
    const k = e.key.toLowerCase();
    if (["arrowup", "w"].includes(k)) { onMove("up"); e.preventDefault(); }
    else if (["arrowdown", "s"].includes(k)) { onMove("down"); e.preventDefault(); }
    else if (["arrowleft", "a"].includes(k)) { onMove("left"); e.preventDefault(); }
    else if (["arrowright", "d"].includes(k)) { onMove("right"); e.preventDefault(); }
    else if (["z", "enter", " "].includes(k)) { onA(); e.preventDefault(); }
    else if (state.mode === "battle" && state.battle.phase === "quiz" && /^[1-6]$/.test(k)) {
      const i = +k - 1; if (i < state.battle.asked.options.length) send({ type: "answer", index: i });
    }
  });
}

function loop() {
  // ease the drawn position toward the grid target -> smooth walking
  const tx = state.cx * 16, ty = state.cy * 16;
  if (rx < tx) rx = Math.min(tx, rx + WALK_SPD); else if (rx > tx) rx = Math.max(tx, rx - WALK_SPD);
  if (ry < ty) ry = Math.min(ty, ry + WALK_SPD); else if (ry > ty) ry = Math.max(ty, ry - WALK_SPD);
  if (state.mode === "battle") drawBattle(); else drawWorld();
  requestAnimationFrame(loop);
}

function drawWorld() {
  if (!mapCanvas) return;
  let camX = rx + 8 - GB_W / 2, camY = ry + 8 - GB_H / 2;
  camX = Math.max(0, Math.min(camX, mapCanvas.width - GB_W));
  camY = Math.max(0, Math.min(camY, mapCanvas.height - GB_H));
  ctx.fillStyle = "#e0f8d0"; ctx.fillRect(0, 0, GB_W * SCALE, GB_H * SCALE);
  ctx.drawImage(mapCanvas, camX, camY, GB_W, GB_H, 0, 0, GB_W * SCALE, GB_H * SCALE);
  ctx.drawImage(spriteImg, 0, 0, 16, 16, (rx - camX) * SCALE, (ry - camY) * SCALE, 16 * SCALE, 16 * SCALE);
}
function drawBattle() {
  const g = ctx.createLinearGradient(0, 0, 0, GB_H * SCALE);
  g.addColorStop(0, "#bfe6ff"); g.addColorStop(1, "#dff3c8");
  ctx.fillStyle = g; ctx.fillRect(0, 0, GB_W * SCALE, GB_H * SCALE);
  ctx.fillStyle = "rgba(80,140,60,.45)";
  ctx.beginPath(); ctx.ellipse(GB_W * SCALE * 0.66, GB_H * SCALE * 0.42, 120, 28, 0, 0, 7); ctx.fill();
  const im = creatureImgs[state.battle.species];
  if (im) ctx.drawImage(im, GB_W * SCALE * 0.66 - 80, GB_H * SCALE * 0.42 - 110, 160, 160);
}

function sync() {
  let h = "";
  if (state.mode === "battle") {
    const b = state.battle, nm = cap(b.species);
    if (b.phase === "intro") h = box(`A wild ${nm} appeared!`, "Battle! ▶", "go");
    else if (b.phase === "result") {
      const r = b.result;
      const msg = r.win ? `🌟 You beat the wild ${nm}! Great answering!` :
                  r.fled ? "You got away safely." : `The ${nm} ran off. The answer was ${esc(r.correctText)}.`;
      h = box(msg, "OK ▶", "go");
    } else { // quiz
      const a = b.asked, clk = a.clock ? ` <span class="clk">🕐 ${a.clock} o'clock</span>` : "";
      h = '<div class="box"><p class="q">' + esc(a.text) + clk + '</p><div class="opts">' +
        a.options.map((o, i) => `<button class="opt" data-ans="${i}">${esc(o)}</button>`).join("") +
        '</div>' + (a.attempts > 0 ? '<p class="hint">💡 ' + esc(a.hint) + '</p>' : '') +
        '<button class="run" id="bRun">Run away</button></div>';
    }
  }
  overlay.innerHTML = h;
  overlay.querySelectorAll("[data-ans]").forEach(x => x.onclick = () => send({ type: "answer", index: +x.getAttribute("data-ans") }));
  const go = document.getElementById("bGo"); if (go) go.onclick = () => send({ type: "confirm" });
  const run = document.getElementById("bRun"); if (run) run.onclick = () => send({ type: "run" });
  maybeSpeak();
}
const box = (msg, btn) => '<div class="box"><p>' + msg + '</p><button class="opt go" id="bGo">' + btn + '</button></div>';
const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);

function maybeSpeak() {
  if (!readAloud || state.mode !== "battle" || state.battle.phase !== "quiz") { lastSpoken = ""; return; }
  const a = state.battle.asked, key = a.text + "|" + a.attempts; if (key === lastSpoken) return; lastSpoken = key;
  speak(a.text + ". The choices are: " + a.options.join(", ") + (a.attempts > 0 ? ". Hint: " + a.hint : ""));
}
function speak(t) { try { const s = speechSynthesis; if (!s) return; s.cancel(); const u = new SpeechSynthesisUtterance(t.replace(/[*_#~`]/g, "")); u.rate = .95; u.pitch = 1.05; s.speak(u); } catch (e) {} }
function stop() { try { speechSynthesis && speechSynthesis.cancel(); } catch (e) {} }

if (document.readyState !== "loading") boot(); else addEventListener("DOMContentLoaded", boot);
