// =============================================================================
// Quiz Quest v2 -- BROWSER FRONT-END (rendering + input + read-aloud).
// Contains NO game rules: it only draws the GameState the logic core produces
// and forwards the child's input into step(). Full colour, scalable, touch +
// keyboard, with read-aloud for early readers.
// =============================================================================
import {
  newGame, step, availableInputs, saveGame, loadGame,
  SPECIES, MAP, MOVES, STARTERS,
} from "../core/engine.js";

const SAVE_KEY = "quizquest_v2_save";
const TILE = 40;                       // logical px per tile (canvas is scaled)
let state, ui = {}, lastQuizText = "", readAloud = true;

// ---------- boot -------------------------------------------------------------
function boot() {
  buildDom();
  // restore a save if present, else a fresh game seeded from the clock
  let saved = null; try { saved = localStorage.getItem(SAVE_KEY); } catch (e) {}
  state = saved ? loadGame(saved, (Date.now() >>> 0) || 1) : newGame((Date.now() >>> 0) || 1);
  bindKeys();
  requestAnimationFrame(loop);
  syncUi();
}

function persist() { try { localStorage.setItem(SAVE_KEY, saveGame(state)); } catch (e) {} }

// drive one input through the core, then refresh UI + save
function send(input) {
  try { step(state, input); } catch (e) { /* global guard also catches */ console.error(e); }
  persist();
  syncUi();
}

// ---------- DOM scaffold -----------------------------------------------------
function buildDom() {
  document.body.innerHTML =
    '<div id="qq">' +
    '  <div id="topbar"><span class="logo">⭐ Quiz Quest</span>' +
    '    <span class="grow"></span>' +
    '    <button id="btnRead" class="tb">🔊 Read aloud</button>' +
    '    <button id="btnReset" class="tb" title="Start over">↻</button></div>' +
    '  <div id="stage"><canvas id="cv" width="400" height="400"></canvas>' +
    '    <div id="overlay"></div></div>' +
    '  <div id="pad"></div>' +
    '</div>';
  ui.cv = document.getElementById("cv");
  ui.ctx = ui.cv.getContext("2d");
  ui.ctx.imageSmoothingEnabled = false;
  ui.overlay = document.getElementById("overlay");
  ui.pad = document.getElementById("pad");
  document.getElementById("btnRead").onclick = (e) => {
    readAloud = !readAloud; e.target.classList.toggle("off", !readAloud);
    if (!readAloud) stopSpeak();
  };
  document.getElementById("btnReset").onclick = () => {
    if (confirm("Start a new adventure? (your progress will reset)")) { state = newGame((Date.now() >>> 0) || 1); persist(); syncUi(); }
  };
  buildPad();
}

// on-screen controls for touch devices
function buildPad() {
  ui.pad.innerHTML =
    '<div class="dpad">' +
    '<button data-mv="up" class="d u">▲</button>' +
    '<button data-mv="left" class="d l">◀</button>' +
    '<button data-mv="right" class="d r">▶</button>' +
    '<button data-mv="down" class="d dn">▼</button></div>' +
    '<div class="ab"><button id="btnA" class="rb">A</button><button id="btnB" class="rb b">B</button></div>';
  ui.pad.querySelectorAll("[data-mv]").forEach(b =>
    b.addEventListener("click", () => onDir(b.getAttribute("data-mv"))));
  document.getElementById("btnA").onclick = () => onA();
  document.getElementById("btnB").onclick = () => onB();
}

// ---------- input ------------------------------------------------------------
function onDir(dir) { if (state.mode === "overworld") send({ type: "move", dir }); }
function onA() {
  if (state.mode === "overworld") send({ type: "interact" });
  else if (state.mode === "dialog") send({ type: "confirm" });
  else if (state.mode === "battle") {
    const b = state.battle;
    if (b.phase === "intro" || b.phase === "done") send({ type: "confirm" });
    else if (b.phase === "menu") send({ type: "fight" });
  }
}
function onB() {
  if (state.mode === "battle" && state.battle.phase === "menu") send({ type: "run" });
  else if (state.mode === "dialog") send({ type: "confirm" });
}
function bindKeys() {
  window.addEventListener("keydown", (e) => {
    const k = e.key.toLowerCase();
    if (["arrowup", "w"].includes(k)) { onDir("up"); e.preventDefault(); }
    else if (["arrowdown", "s"].includes(k)) { onDir("down"); e.preventDefault(); }
    else if (["arrowleft", "a"].includes(k)) { onDir("left"); e.preventDefault(); }
    else if (["arrowright", "d"].includes(k)) { onDir("right"); e.preventDefault(); }
    else if (["z", "enter", " "].includes(k)) { onA(); e.preventDefault(); }
    else if (["x", "backspace"].includes(k)) { onB(); e.preventDefault(); }
    else if (state.mode === "battle" && state.battle.phase === "quiz" && /^[1-6]$/.test(k)) {
      const i = +k - 1; if (i < state.battle.asked.options.length) send({ type: "answer", index: i });
    }
  });
}

// ---------- render loop ------------------------------------------------------
function loop() { draw(); requestAnimationFrame(loop); }

const TILECOL = { "#": "#2f5d3a", ".": "#cde4b0", ",": "#7fc05a", "~": "#4aa6e0", "H": "#caa472", "P": "#cde4b0", "G": "#cde4b0", "S": "#cde4b0" };
function draw() {
  const ctx = ui.ctx;
  if (state.mode === "battle") { drawBattle(ctx); return; }
  // overworld
  for (let y = 0; y < MAP.h; y++) for (let x = 0; x < MAP.w; x++) {
    const t = MAP.rows[y][x];
    ctx.fillStyle = TILECOL[t] || "#cde4b0";
    ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
    if (t === ",") { ctx.fillStyle = "#6aa748"; for (let i = 0; i < 3; i++) ctx.fillRect(x * TILE + 6 + i * 11, y * TILE + 24, 4, 12); }
    if (t === "#") { ctx.fillStyle = "#234a2c"; ctx.fillRect(x * TILE + 6, y * TILE + 6, TILE - 12, TILE - 12); ctx.fillStyle = "#3a6e44"; ctx.beginPath(); ctx.arc(x * TILE + TILE / 2, y * TILE + 16, 13, 0, 7); ctx.fill(); }
    if (t === "H") { ctx.fillStyle = "#9b2d2d"; ctx.fillRect(x * TILE + 4, y * TILE + 2, TILE - 8, 12); ctx.fillStyle = "#3a2a22"; ctx.fillRect(x * TILE + TILE / 2 - 5, y * TILE + 20, 10, TILE - 22); }
    if (t === "G") { ctx.fillStyle = "#7a4d00"; ctx.fillRect(x * TILE + TILE / 2 - 2, y * TILE + 16, 4, 18); ctx.fillStyle = "#ffd23f"; ctx.fillRect(x * TILE + 8, y * TILE + 6, TILE - 16, 14); ctx.fillStyle = "#5a4410"; ctx.font = "9px sans-serif"; ctx.fillText("GOAL", x * TILE + 9, y * TILE + 16); }
    if (t === "P") drawPerson(ctx, x * TILE, y * TILE, "#6d28d9", "#f4d9b0");
  }
  drawPerson(ctx, state.x * TILE, state.y * TILE, "#2563eb", "#f4d9b0", state.facing);
}
function drawPerson(ctx, px, py, body, skin, facing) {
  ctx.fillStyle = body; ctx.fillRect(px + 12, py + 16, 16, 16);
  ctx.fillStyle = skin; ctx.beginPath(); ctx.arc(px + 20, py + 12, 8, 0, 7); ctx.fill();
  ctx.fillStyle = "#222";
  if (facing === "left") ctx.fillRect(px + 14, py + 11, 2, 2);
  else if (facing === "right") ctx.fillRect(px + 24, py + 11, 2, 2);
  else { ctx.fillRect(px + 16, py + 11, 2, 2); ctx.fillRect(px + 22, py + 11, 2, 2); }
}
function drawCreature(ctx, cx, cy, size, color, flip) {
  ctx.save(); ctx.translate(cx, cy); if (flip) ctx.scale(-1, 1);
  ctx.fillStyle = color; ctx.beginPath(); ctx.arc(0, 0, size, 0, 7); ctx.fill();
  ctx.fillStyle = color; ctx.beginPath(); ctx.arc(-size * 0.55, -size * 0.8, size * 0.35, 0, 7); ctx.arc(size * 0.55, -size * 0.8, size * 0.35, 0, 7); ctx.fill(); // ears
  ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(-size * 0.35, -size * 0.1, size * 0.22, 0, 7); ctx.arc(size * 0.35, -size * 0.1, size * 0.22, 0, 7); ctx.fill();
  ctx.fillStyle = "#222"; ctx.beginPath(); ctx.arc(-size * 0.32, -size * 0.08, size * 0.1, 0, 7); ctx.arc(size * 0.38, -size * 0.08, size * 0.1, 0, 7); ctx.fill();
  ctx.fillStyle = "rgba(0,0,0,.18)"; ctx.beginPath(); ctx.arc(0, size * 0.35, size * 0.28, 0, 7); ctx.fill();
  ctx.restore();
}
function drawBattle(ctx) {
  const b = state.battle, me = state.party.find(m => m.hp > 0) || state.party[0];
  const g = ctx.createLinearGradient(0, 0, 0, 400); g.addColorStop(0, "#bfe3ff"); g.addColorStop(1, "#dff3c8"); ctx.fillStyle = g; ctx.fillRect(0, 0, 400, 400);
  ctx.fillStyle = "#9ed06a"; ctx.beginPath(); ctx.ellipse(300, 150, 80, 22, 0, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.ellipse(110, 300, 95, 26, 0, 0, 7); ctx.fill();
  drawCreature(ctx, 300, 130, 34, SPECIES[b.enemy.species].color, false);
  if (me) drawCreature(ctx, 110, 280, 40, SPECIES[me.species].color, true);
  hpBar(ctx, 30, 30, b.enemy);
  if (me) hpBar(ctx, 220, 200, me);
}
function hpBar(ctx, x, y, mon) {
  ctx.fillStyle = "#fff"; ctx.fillRect(x, y, 150, 38); ctx.strokeStyle = "#456"; ctx.strokeRect(x, y, 150, 38);
  ctx.fillStyle = "#243"; ctx.font = "bold 13px sans-serif"; ctx.fillText(`${mon.name}  Lv${mon.level}`, x + 6, y + 15);
  ctx.fillStyle = "#ccc"; ctx.fillRect(x + 6, y + 22, 138, 8);
  const frac = Math.max(0, mon.hp / mon.maxHp);
  ctx.fillStyle = frac > 0.5 ? "#3fb96b" : frac > 0.2 ? "#f2b134" : "#ef6b62";
  ctx.fillRect(x + 6, y + 22, 138 * frac, 8);
}

// ---------- overlay (dialog / starter / battle menus / quiz) -----------------
function syncUi() {
  const o = ui.overlay; let html = "";
  if (state.mode === "dialog") {
    const d = state.dialog;
    if (d.effect && d.effect.kind === "chooseStarter") {
      html = '<div class="box"><p>' + esc(d.lines[0]) + '</p><div class="opts">' +
        STARTERS.map((s, i) => `<button class="opt" data-starter="${i}" style="border-color:${SPECIES[s].color}">${esc(SPECIES[s].name)}<small>${SPECIES[s].type}</small></button>`).join("") +
        '</div></div>';
    } else {
      html = '<div class="box"><p>' + esc(d.lines[d.idx]) + '</p><button class="opt next">OK ▶</button></div>';
    }
  } else if (state.mode === "battle") {
    const b = state.battle;
    if (b.phase === "intro") html = msgBox(`A wild ${b.enemy.name} appeared!`, "OK ▶");
    else if (b.phase === "done") html = msgBox(b.log[b.log.length - 1] || "", "OK ▶");
    else if (b.phase === "menu") html = '<div class="box"><p>What will you do?</p><div class="opts"><button class="opt" id="oFight">⚔ FIGHT</button><button class="opt" id="oRun">🏃 RUN</button></div></div>';
    else if (b.phase === "quiz") {
      const a = b.asked;
      const clk = a.clock ? ` <span class="clk">🕐 ${a.clock} o'clock</span>` : "";
      html = '<div class="box quiz"><p class="q">' + esc(a.text) + clk + '</p><div class="opts grid">' +
        a.options.map((op, i) => `<button class="opt ans" data-ans="${i}">${esc(op)}</button>`).join("") +
        '</div>' + (a.attempts > 0 ? '<p class="hint">💡 ' + esc(a.hint) + '</p>' : '') + '</div>';
    }
  }
  o.innerHTML = html;
  // wire overlay buttons
  o.querySelectorAll("[data-starter]").forEach(btn => btn.onclick = () => send({ type: "starter", index: +btn.getAttribute("data-starter") }));
  o.querySelectorAll("[data-ans]").forEach(btn => btn.onclick = () => send({ type: "answer", index: +btn.getAttribute("data-ans") }));
  const nx = o.querySelector(".next"); if (nx) nx.onclick = () => onA();
  const f = o.querySelector("#oFight"); if (f) f.onclick = () => send({ type: "fight" });
  const r = o.querySelector("#oRun"); if (r) r.onclick = () => send({ type: "run" });
  const mb = o.querySelector(".msgbtn"); if (mb) mb.onclick = () => onA();
  maybeSpeak();
}
function msgBox(text, btn) { return '<div class="box"><p>' + esc(text) + '</p><button class="opt msgbtn">' + btn + '</button></div>'; }
function esc(s) { return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

// ---------- read-aloud -------------------------------------------------------
function maybeSpeak() {
  if (!readAloud || state.mode !== "battle" || !state.battle || state.battle.phase !== "quiz") { lastQuizText = ""; return; }
  const a = state.battle.asked, key = a.text + "|" + a.attempts;
  if (key === lastQuizText) return; lastQuizText = key;
  const opts = a.options.join(", ");
  speak(a.text + ". The choices are: " + opts + (a.attempts > 0 ? ". Hint: " + a.hint : ""));
}
function speak(text) {
  try {
    const synth = window.speechSynthesis; if (!synth) return; synth.cancel();
    const u = new SpeechSynthesisUtterance(sanitize(text));
    u.rate = 0.95; u.pitch = 1.05; synth.speak(u);
  } catch (e) {}
}
function stopSpeak() { try { window.speechSynthesis && window.speechSynthesis.cancel(); } catch (e) {} }
function sanitize(t) { return t.replace(/[*_#~`]/g, "").replace(/\s+/g, " ").trim(); }

if (document.readyState !== "loading") boot(); else document.addEventListener("DOMContentLoaded", boot);
