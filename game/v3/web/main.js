// =============================================================================
// Quiz Quest v3 -- FRONT-END (eyes + hands). Real walking animation, smooth
// camera, ledge hops, and a battle screen (both creatures + HP bars + hit
// flashes). Keyboard + touch + read-aloud. No rules here.
// =============================================================================
import { newGame, step, availableInputs, saveGame, loadGame } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

const SAVE_KEY = "quizquest3_save_r2", GB_W = 160, GB_H = 144, SCALE = 4, WALK_SPD = 2;
const validPos = s => s && s.cx >= 0 && s.cy >= 0 && s.cx < PACK.cw && s.cy < PACK.ch && PACK.walk[s.cy] && PACK.walk[s.cy][s.cx] === 1;
const FACE = { down: 0, up: 1, left: 2, right: 2 }, WALKR = { down: 3, up: 4, left: 5, right: 5 };
let state, ctx, mapCanvas, tilesetImg, spriteImg, creatureImgs = {}, playerCreImg, overlay;
let rx = 0, ry = 0, anim = 0, hopFrom = null, stepParity = false, readAloud = true, lastSpoken = "";
let flashEnemy = 0, flashMon = 0;

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
  if (!validPos(state)) state = newGame(PACK, now());
  rx = state.cx * 16; ry = state.cy * 16;

  let need = 3 + Object.keys(PACK.creatures || {}).length, got = 0;
  const done = () => { if (++got === need) { composeMap(); bindKeys(); requestAnimationFrame(loop); sync(); } };
  tilesetImg = new Image(); tilesetImg.onload = done; tilesetImg.src = PACK.tilesetURL;
  spriteImg = new Image(); spriteImg.onload = done; spriteImg.src = PACK.spriteURL;
  playerCreImg = new Image(); playerCreImg.onload = done; playerCreImg.src = PACK.playerCreatureURL;
  for (const k in (PACK.creatures || {})) { const im = new Image(); im.onload = done; im.src = PACK.creatures[k]; creatureImgs[k] = im; }
}
const now = () => (Date.now() >>> 0) || 1;
const persist = () => { try { localStorage.setItem(SAVE_KEY, saveGame(state)); } catch (e) {} };
const moving = () => rx !== state.cx * 16 || ry !== state.cy * 16;
function send(input) {
  const before = [state.cx, state.cy];
  let res; try { res = step(state, PACK, input); } catch (e) { console.error(e); res = { events: [] }; }
  if (input.type === "move" && (state.cx !== before[0] || state.cy !== before[1])) stepParity = !stepParity; // alternate feet each step
  for (const e of res.events || []) {
    if (e.t === "hop") hopFrom = before;
    if (e.t === "playerHit") flashEnemy = 10;
    if (e.t === "enemyHit" || e.t === "miss") flashMon = 10;
  }
  persist(); sync();
}

function composeMap() {
  const T = PACK.tile, B = PACK.block, per = PACK.tilesPerRow;
  mapCanvas = document.createElement("canvas"); mapCanvas.width = PACK.w * B * T; mapCanvas.height = PACK.h * B * T;
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
  if (state.mode === "battle") { if (state.battle.phase !== "quiz") send({ type: "confirm" }); }
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
  anim++; if (flashEnemy > 0) flashEnemy--; if (flashMon > 0) flashMon--;
  const tx = state.cx * 16, ty = state.cy * 16;
  if (rx < tx) rx = Math.min(tx, rx + WALK_SPD); else if (rx > tx) rx = Math.max(tx, rx - WALK_SPD);
  if (ry < ty) ry = Math.min(ty, ry + WALK_SPD); else if (ry > ty) ry = Math.max(ty, ry - WALK_SPD);
  if (!moving()) hopFrom = null;
  if (state.mode === "battle") drawBattle(); else drawWorld();
  requestAnimationFrame(loop);
}

function drawPlayer(sx, sy) {
  const f = state.facing;
  // while moving, always show the WALK pose (so it's never a static glide);
  // when stopped, the standing pose.
  const row = moving() ? WALKR[f] : FACE[f];
  // right faces left-frame mirrored; for down/up, mirror on alternate steps so
  // the feet visibly swap as you walk.
  let mirror = (f === "right");
  if (moving() && (f === "down" || f === "up") && stepParity) mirror = !mirror;
  ctx.save();
  if (mirror) { ctx.translate(sx + 16 * SCALE, sy); ctx.scale(-1, 1); ctx.drawImage(spriteImg, 0, row * 16, 16, 16, 0, 0, 16 * SCALE, 16 * SCALE); }
  else ctx.drawImage(spriteImg, 0, row * 16, 16, 16, sx, sy, 16 * SCALE, 16 * SCALE);
  ctx.restore();
}
function drawWorld() {
  if (!mapCanvas) return;
  // hop arc: lift the sprite as it jumps a ledge
  let arc = 0;
  if (hopFrom) { const total = (Math.abs(state.cx * 16 - hopFrom[0] * 16) + Math.abs(state.cy * 16 - hopFrom[1] * 16)) || 32;
    const doneDist = total - (Math.abs(state.cx * 16 - rx) + Math.abs(state.cy * 16 - ry)); arc = -Math.sin(Math.PI * (doneDist / total)) * 14; }
  let camX = rx + 8 - GB_W / 2, camY = ry + 8 - GB_H / 2;
  camX = Math.max(0, Math.min(camX, mapCanvas.width - GB_W)); camY = Math.max(0, Math.min(camY, mapCanvas.height - GB_H));
  ctx.fillStyle = "#e0f8d0"; ctx.fillRect(0, 0, GB_W * SCALE, GB_H * SCALE);
  ctx.drawImage(mapCanvas, camX, camY, GB_W, GB_H, 0, 0, GB_W * SCALE, GB_H * SCALE);
  drawPlayer((rx - camX) * SCALE, (ry - camY + arc) * SCALE);
}
function drawBattle() {
  const b = state.battle, W = GB_W * SCALE, H = GB_H * SCALE;
  const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "#bfe6ff"); g.addColorStop(1, "#dff3c8");
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "rgba(80,140,60,.4)"; ctx.beginPath(); ctx.ellipse(W * .70, H * .40, 110, 24, 0, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.ellipse(W * .28, H * .74, 120, 26, 0, 0, 7); ctx.fill();
  const enemy = creatureImgs[b.enemy.species];
  if (enemy && flashEnemy % 4 < 2) ctx.drawImage(enemy, W * .70 - 70, H * .40 - 95, 150, 150);
  if (playerCreImg && flashMon % 4 < 2) ctx.drawImage(playerCreImg, W * .28 - 80, H * .74 - 120, 150, 150);
  hpBox(8, 8, cap(b.enemy.species), b.enemy);
  hpBox(W - 196, H * .50, b.mon.species, b.mon);
  if (b.log) { ctx.fillStyle = "rgba(0,0,0,.5)"; ctx.fillRect(0, H - 26, W, 26); ctx.fillStyle = "#fff"; ctx.font = "bold 14px system-ui"; ctx.fillText(b.log, 10, H - 8); }
}
function hpBox(x, y, name, mon) {
  ctx.fillStyle = "#fff"; ctx.strokeStyle = "#456"; ctx.fillRect(x, y, 188, 40); ctx.strokeRect(x, y, 188, 40);
  ctx.fillStyle = "#243"; ctx.font = "bold 14px system-ui"; ctx.fillText(name, x + 8, y + 17);
  ctx.fillStyle = "#ccc"; ctx.fillRect(x + 8, y + 24, 172, 9);
  const f = Math.max(0, mon.hp / mon.maxHp);
  ctx.fillStyle = f > .5 ? "#43c06a" : f > .2 ? "#f2b134" : "#ef6b62"; ctx.fillRect(x + 8, y + 24, 172 * f, 9);
}

function sync() {
  let h = "";
  if (state.mode === "battle") {
    const b = state.battle, nm = cap(b.enemy.species);
    if (b.phase === "intro") h = box(`A wild ${nm} appeared!`, "Battle! ▶");
    else if (b.phase === "result") {
      const r = b.result;
      const msg = r.win ? `🌟 You beat the wild ${nm}! Great answering!` : r.lose ? `${cap(b.mon.species)} is worn out. Healed up — try again!` : r.fled ? "You got away safely." : "";
      h = box(msg, "OK ▶");
    } else {
      const a = b.asked, clk = a.clock ? ` <span class="clk">🕐 ${a.clock} o'clock</span>` : "";
      h = '<div class="box">' + (b.log ? '<p class="log">' + esc(b.log) + '</p>' : '') +
        '<p class="q">' + esc(a.text) + clk + '</p><div class="opts">' +
        a.options.map((o, i) => `<button class="opt" data-ans="${i}">${esc(o)}</button>`).join("") + '</div>' +
        (a.attempts > 0 ? '<p class="hint">💡 ' + esc(a.hint) + '</p>' : '') + '<button class="run" id="bRun">Run away</button></div>';
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
