// =============================================================================
// Quiz Quest v3 -- FRONT-END. Walking animation + smooth camera + ledge hops,
// and a full battle UI: FIGHT (pick a move) / BAG / POKEMON (party list) / RUN,
// with attack animations (lunge + flash + HP-bar drain). Keyboard + touch +
// read-aloud. No rules here.
// =============================================================================
import { newGame, step, availableInputs, saveGame, loadGame, CDEF } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

const SAVE_KEY = "quizquest3_save_b1", GB_W = 160, GB_H = 144, SCALE = 4, WALK_SPD = 2;
const validPos = s => s && s.cx >= 0 && s.cy >= 0 && s.cx < PACK.cw && s.cy < PACK.ch && PACK.walk[s.cy] && PACK.walk[s.cy][s.cx] === 1;
const FACE = { down: 0, up: 1, left: 2, right: 2 }, WALKR = { down: 3, up: 4, left: 5, right: 5 };
let state, ctx, mapCanvas, tilesetImg, spriteImg, creatureImgs = {}, overlay;
let rx = 0, ry = 0, anim = 0, hopFrom = null, stepParity = false, readAloud = true, lastSpoken = "";
let deHp = 0, dmHp = 0, lunge = 0, lungeSide = "", flash = 0, flashSide = "";

function boot() {
  document.body.innerHTML =
    '<div id="qq"><div id="bar"><span class="logo">⭐ Quiz Quest</span><span class="grow"></span>' +
    '<button id="btnRead" class="tb">🔊 Read aloud</button><button id="btnReset" class="tb">↻</button></div>' +
    '<div id="stage"><canvas id="cv" width="' + GB_W * SCALE + '" height="' + GB_H * SCALE + '"></canvas><div id="ov"></div></div>' +
    '<div id="pad"><div class="dpad"><button class="d u" data-mv="up">▲</button><button class="d l" data-mv="left">◀</button>' +
    '<button class="d r" data-mv="right">▶</button><button class="d dn" data-mv="down">▼</button></div>' +
    '<div class="ab"><button id="bA" class="rb">A</button><button id="bB" class="rb bb">B</button></div></div></div>';
  ctx = document.getElementById("cv").getContext("2d"); ctx.imageSmoothingEnabled = false;
  overlay = document.getElementById("ov");
  document.getElementById("btnRead").onclick = e => { readAloud = !readAloud; e.target.classList.toggle("off", !readAloud); if (!readAloud) stop(); };
  document.getElementById("btnReset").onclick = () => { if (confirm("Start over?")) { state = newGame(PACK, now()); rx = state.cx * 16; ry = state.cy * 16; persist(); sync(); } };
  document.querySelectorAll("[data-mv]").forEach(b => b.onclick = () => onMove(b.getAttribute("data-mv")));
  document.getElementById("bA").onclick = onA; document.getElementById("bB").onclick = onB;

  let saved = null; try { saved = localStorage.getItem(SAVE_KEY); } catch (e) {}
  state = saved ? loadGame(saved, PACK, now()) : newGame(PACK, now());
  if (!validPos(state)) state = newGame(PACK, now());
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
const activeMon = () => state.battle && state.party[state.battle.partyIdx];
function send(input) {
  const before = [state.cx, state.cy];
  let res; try { res = step(state, PACK, input); } catch (e) { console.error(e); res = { events: [] }; }
  if (input.type === "move" && (state.cx !== before[0] || state.cy !== before[1])) stepParity = !stepParity;
  for (const e of res.events || []) {
    if (e.t === "hop") hopFrom = before;
    if (e.t === "encounter") { deHp = state.battle.enemy.maxHp; dmHp = activeMon().hp; }   // start bars full
    if (e.t === "switch") dmHp = activeMon().hp;                                            // show the new mon's HP
    if (e.t === "playerHit") { lunge = 12; lungeSide = "mon"; flash = 12; flashSide = "enemy"; }
    if (e.t === "enemyHit" || e.t === "miss") { lunge = 12; lungeSide = "enemy"; flash = 12; flashSide = "mon"; }
  }
  persist(); sync();
}

function composeMap() {
  const T = PACK.tile, B = PACK.block, per = PACK.tilesPerRow;
  mapCanvas = document.createElement("canvas"); mapCanvas.width = PACK.w * B * T; mapCanvas.height = PACK.h * B * T;
  const mc = mapCanvas.getContext("2d"); mc.imageSmoothingEnabled = false;
  for (let my = 0; my < PACK.h; my++) for (let mx = 0; mx < PACK.w; mx++) {
    const bt = PACK.blocks[PACK.map[my * PACK.w + mx]];
    for (let ty = 0; ty < B; ty++) for (let tx = 0; tx < B; tx++) { const id = bt[ty * B + tx]; mc.drawImage(tilesetImg, (id % per) * T, ((id / per) | 0) * T, T, T, (mx * B + tx) * T, (my * B + ty) * T, T, T); }
  }
}

function onMove(dir) { if (state.mode === "overworld" && !moving()) send({ type: "move", dir }); }
function onA() {
  if (state.mode === "overworld") { if (!moving()) send({ type: "move", dir: state.facing }); return; }
  const ph = state.battle.phase;
  if (ph === "intro" || ph === "result") send({ type: "confirm" });
}
function onB() {  // back, in sub-menus
  if (state.mode === "battle") { const ph = state.battle.phase; if (ph === "moves" || ph === "bag" || (ph === "party" && !state.battle.forced)) send({ type: "back" }); }
}
function bindKeys() {
  addEventListener("keydown", e => {
    const k = e.key.toLowerCase();
    if (["arrowup", "w"].includes(k)) { onMove("up"); e.preventDefault(); }
    else if (["arrowdown", "s"].includes(k)) { onMove("down"); e.preventDefault(); }
    else if (["arrowleft", "a"].includes(k)) { onMove("left"); e.preventDefault(); }
    else if (["arrowright", "d"].includes(k)) { onMove("right"); e.preventDefault(); }
    else if (["z", "enter", " "].includes(k)) { onA(); e.preventDefault(); }
    else if (["x", "backspace"].includes(k)) { onB(); e.preventDefault(); }
    else if (state.mode === "battle" && (state.battle.phase === "quiz" || state.battle.phase === "catch") && /^[1-6]$/.test(k)) {
      const i = +k - 1; if (i < state.battle.asked.options.length) send({ type: "answer", index: i });
    }
  });
}

function loop() {
  anim++; if (flash > 0) flash--; if (lunge > 0) lunge--;
  const tx = state.cx * 16, ty = state.cy * 16;
  if (rx < tx) rx = Math.min(tx, rx + WALK_SPD); else if (rx > tx) rx = Math.max(tx, rx - WALK_SPD);
  if (ry < ty) ry = Math.min(ty, ry + WALK_SPD); else if (ry > ty) ry = Math.max(ty, ry - WALK_SPD);
  if (!moving()) hopFrom = null;
  if (state.mode === "battle") {                      // ease HP bars toward real values
    const b = state.battle, me = activeMon();
    deHp += Math.sign(b.enemy.hp - deHp) * Math.min(1, Math.abs(b.enemy.hp - deHp));
    dmHp += Math.sign(me.hp - dmHp) * Math.min(1, Math.abs(me.hp - dmHp));
    drawBattle();
  } else drawWorld();
  requestAnimationFrame(loop);
}

function drawPlayer(sx, sy) {
  const f = state.facing, row = moving() ? WALKR[f] : FACE[f];
  let mirror = (f === "right"); if (moving() && (f === "down" || f === "up") && stepParity) mirror = !mirror;
  ctx.save();
  if (mirror) { ctx.translate(sx + 16 * SCALE, sy); ctx.scale(-1, 1); ctx.drawImage(spriteImg, 0, row * 16, 16, 16, 0, 0, 16 * SCALE, 16 * SCALE); }
  else ctx.drawImage(spriteImg, 0, row * 16, 16, 16, sx, sy, 16 * SCALE, 16 * SCALE);
  ctx.restore();
}
function drawWorld() {
  if (!mapCanvas) return;
  let arc = 0;
  if (hopFrom) { const total = (Math.abs(state.cx * 16 - hopFrom[0] * 16) + Math.abs(state.cy * 16 - hopFrom[1] * 16)) || 32; const d = total - (Math.abs(state.cx * 16 - rx) + Math.abs(state.cy * 16 - ry)); arc = -Math.sin(Math.PI * (d / total)) * 14; }
  let camX = Math.max(0, Math.min(rx + 8 - GB_W / 2, mapCanvas.width - GB_W)), camY = Math.max(0, Math.min(ry + 8 - GB_H / 2, mapCanvas.height - GB_H));
  ctx.fillStyle = "#e0f8d0"; ctx.fillRect(0, 0, GB_W * SCALE, GB_H * SCALE);
  ctx.drawImage(mapCanvas, camX, camY, GB_W, GB_H, 0, 0, GB_W * SCALE, GB_H * SCALE);
  drawPlayer((rx - camX) * SCALE, (ry - camY + arc) * SCALE);
}
function drawBattle() {
  const b = state.battle, me = activeMon(), W = GB_W * SCALE, H = GB_H * SCALE;
  const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "#bfe6ff"); g.addColorStop(1, "#dff3c8");
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "rgba(80,140,60,.4)"; ctx.beginPath(); ctx.ellipse(W * .70, H * .40, 110, 24, 0, 0, 7); ctx.fill(); ctx.beginPath(); ctx.ellipse(W * .28, H * .74, 120, 26, 0, 0, 7); ctx.fill();
  const lx = lunge > 0 ? (lunge / 12) * 18 : 0;        // lunge offset
  const eOff = lungeSide === "enemy" ? -lx : 0, mOff = lungeSide === "mon" ? lx : 0;
  const en = creatureImgs[b.enemy.species]; if (en && !(flashSide === "enemy" && flash % 4 < 2)) ctx.drawImage(en, W * .70 - 70 + eOff, H * .40 - 95 - eOff * .5, 150, 150);
  const pm = creatureImgs[me.species]; if (pm && !(flashSide === "mon" && flash % 4 < 2)) ctx.drawImage(pm, W * .28 - 80 + mOff, H * .74 - 120 - mOff * .5, 150, 150);
  hpBox(8, 8, b.enemy.name, deHp, b.enemy.maxHp);
  hpBox(W - 196, H * .50, me.name + "  " + Math.max(0, Math.round(dmHp)) + "/" + me.maxHp, dmHp, me.maxHp);
  if (b.log) { ctx.fillStyle = "rgba(0,0,0,.5)"; ctx.fillRect(0, H - 26, W, 26); ctx.fillStyle = "#fff"; ctx.font = "bold 14px system-ui"; ctx.fillText(b.log, 10, H - 8); }
}
function hpBox(x, y, label, hp, maxHp) {
  ctx.fillStyle = "#fff"; ctx.strokeStyle = "#456"; ctx.fillRect(x, y, 188, 40); ctx.strokeRect(x, y, 188, 40);
  ctx.fillStyle = "#243"; ctx.font = "bold 13px system-ui"; ctx.fillText(label, x + 8, y + 16);
  ctx.fillStyle = "#ccc"; ctx.fillRect(x + 8, y + 24, 172, 9);
  const f = Math.max(0, hp / maxHp); ctx.fillStyle = f > .5 ? "#43c06a" : f > .2 ? "#f2b134" : "#ef6b62"; ctx.fillRect(x + 8, y + 24, 172 * f, 9);
}

function sync() {
  let h = "";
  if (state.mode === "battle") {
    const b = state.battle, me = activeMon(), en = b.enemy.name;
    if (b.phase === "intro") h = box(`A wild ${en} appeared!`, "Go! ▶");
    else if (b.phase === "result") { const r = b.result; h = box(r.win ? `🌟 You beat the wild ${en}!` : r.caught ? `🎉 Gotcha! ${en} was caught!` : r.lose ? `${me.name} is worn out — all healed up, try again!` : "Got away safely.", "OK ▶"); }
    else if (b.phase === "menu") h = '<div class="box"><p class="log">' + (b.log ? esc(b.log) : `What will ${me.name} do?`) + '</p><div class="opts">' +
      btn("menu", "choice", "fight", "⚔ FIGHT") + btn("menu", "choice", "bag", "🎒 BAG") + btn("menu", "choice", "party", "🐾 POKéMON") + btn("menu", "choice", "run", "🏃 RUN") + '</div></div>';
    else if (b.phase === "moves") h = '<div class="box"><p>Pick a move:</p><div class="opts">' + me.moves.map((m, i) => `<button class="opt" data-k="move" data-i="${i}">${esc(m.name)}<small>power ${m.power}</small></button>`).join("") + '</div>' + backBtn() + '</div>';
    else if (b.phase === "bag") h = '<div class="box"><p>Bag:</p><div class="opts">' + `<button class="opt" data-k="item" data-w="potion">🧪 Potion <small>x${state.potions}</small></button>` + `<button class="opt" data-k="item" data-w="ball">🔴 Poké Ball</button>` + '</div>' + backBtn() + '</div>';
    else if (b.phase === "party") h = '<div class="box"><p>Your team:</p><div class="opts">' + state.party.map((m, i) => `<button class="opt" data-k="switch" data-i="${i}" ${(m.hp <= 0 || i === b.partyIdx) ? "disabled" : ""}>${esc(m.name)}<small>${m.hp > 0 ? "HP " + Math.round(m.hp) + "/" + m.maxHp : "fainted"}${i === b.partyIdx ? " (out)" : ""}</small></button>`).join("") + '</div>' + (b.forced ? "" : backBtn()) + '</div>';
    else { const a = b.asked, clk = a.clock ? ` <span class="clk">🕐 ${a.clock} o'clock</span>` : ""; const tag = b.phase === "catch" ? `<p class="log">Catch challenge — ${b.catchCount}/5 right!</p>` : (b.log ? '<p class="log">' + esc(b.log) + '</p>' : "");
      h = '<div class="box">' + tag + '<p class="q">' + esc(a.text) + clk + '</p><div class="opts">' + a.options.map((o, i) => `<button class="opt" data-k="answer" data-i="${i}">${esc(o)}</button>`).join("") + '</div>' + (a.attempts > 0 ? '<p class="hint">💡 ' + esc(a.hint) + '</p>' : "") + '</div>'; }
  }
  overlay.innerHTML = h; wire();
  maybeSpeak();
}
const btn = (k, attr, val, label) => `<button class="opt" data-k="${k}" data-${attr}="${val}">${label}</button>`;
const backBtn = () => '<button class="run" data-k="back">◀ Back</button>';
function wire() {
  overlay.querySelectorAll("[data-k]").forEach(el => el.onclick = () => {
    const k = el.dataset.k;
    if (k === "menu") send({ type: "menu", choice: el.dataset.choice });
    else if (k === "move") send({ type: "move", index: +el.dataset.i });
    else if (k === "item") send({ type: "item", which: el.dataset.w });
    else if (k === "switch") send({ type: "switch", index: +el.dataset.i });
    else if (k === "answer") send({ type: "answer", index: +el.dataset.i });
    else if (k === "back") send({ type: "back" });
  });
  const go = overlay.querySelector(".go"); if (go) go.onclick = () => send({ type: "confirm" });
}
const box = (msg, b) => '<div class="box"><p>' + msg + '</p><button class="opt go">' + b + '</button></div>';
const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function maybeSpeak() {
  const b = state.battle;
  if (!readAloud || !b || (b.phase !== "quiz" && b.phase !== "catch")) { lastSpoken = ""; return; }
  const a = b.asked, key = a.text + "|" + a.attempts; if (key === lastSpoken) return; lastSpoken = key;
  speak(a.text + ". The choices are: " + a.options.join(", ") + (a.attempts > 0 ? ". Hint: " + a.hint : ""));
}
function speak(t) { try { const s = speechSynthesis; if (!s) return; s.cancel(); const u = new SpeechSynthesisUtterance(t.replace(/[*_#~`]/g, "")); u.rate = .95; u.pitch = 1.05; s.speak(u); } catch (e) {} }
function stop() { try { speechSynthesis && speechSynthesis.cancel(); } catch (e) {} }

if (document.readyState !== "loading") boot(); else addEventListener("DOMContentLoaded", boot);
