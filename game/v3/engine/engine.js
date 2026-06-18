// =============================================================================
// Quiz Quest v3 -- LOGIC CORE (pure, deterministic, no pictures).
// Walking + collision + one-way ledge hops on the real map, and turn-based
// quiz BATTLES (answer right -> your creature attacks; the enemy attacks back;
// HP; faint = win/lose; full heal after). Encounters only in tall grass.
// =============================================================================
import { QUESTIONS } from "./questions.js";
export { QUESTIONS };

export function nextRand(state) {
  let t = (state.seed = (state.seed + 0x6D2B79F5) >>> 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
export function randInt(state, n) { return Math.floor(nextRand(state) * n); }

export function newGame(pack, seed) {
  return { seed: (seed >>> 0) || 1, mode: "overworld",
    cx: pack.start[0], cy: pack.start[1], facing: "down",
    steps: 0, battlesWon: 0, battlesSeen: 0, streak: 0, lastSubject: -1, battle: null };
}

const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
const LEDGE_FOR = { down: 1, left: 2, right: 3 };   // which ledge code each dir hops

function pickQuestion(state) {
  let pool = QUESTIONS.filter(q => q.grade === 1); if (!pool.length) pool = QUESTIONS;
  let q = pool[randInt(state, pool.length)];
  for (let i = 0; i < 8 && q.subject === state.lastSubject; i++) q = pool[randInt(state, pool.length)];
  state.lastSubject = q.subject;
  const opts = q.answers.slice();
  for (let i = opts.length - 1; i > 0; i--) { const j = randInt(state, i + 1); const t = opts[i]; opts[i] = opts[j]; opts[j] = t; }
  return { text: q.text, options: opts, correct: opts.indexOf(q.correct), correctText: q.correct, hint: q.hint, clock: q.clock, attempts: 0 };
}

function startBattle(state, pack) {
  const names = pack.creatureNames && pack.creatureNames.length ? pack.creatureNames : ["wild"];
  const enemy = { species: names[randInt(state, names.length)], hp: 14, maxHp: 14, atk: 4 };
  const mon = { species: pack.playerCreature || "Buddy", hp: 18, maxHp: 18, atk: 5 };
  state.mode = "battle"; state.battlesSeen++;
  state.battle = { enemy, mon, phase: "intro", asked: null, log: "", result: null };
}
function enemyTurn(state, ev) {
  const b = state.battle, dmg = b.enemy.atk + randInt(state, 3);
  b.mon.hp = Math.max(0, b.mon.hp - dmg); b.log = `Wild ${b.enemy.species} hit back! (-${dmg})`;
  ev.push({ t: "enemyHit", dmg });
}

export function step(state, pack, input) {
  const ev = []; state.steps++;
  if (state.mode === "overworld") {
    if (input.type === "move") {
      state.facing = input.dir;
      const [dx, dy] = DIRS[input.dir], nx = state.cx + dx, ny = state.cy + dy;
      const inb = (x, y) => x >= 0 && y >= 0 && x < pack.cw && y < pack.ch;
      if (inb(nx, ny) && pack.walk[ny][nx]) { state.cx = nx; state.cy = ny; grassCheck(state, pack, ev); }
      else if (inb(nx, ny) && pack.ledge[ny][nx] === LEDGE_FOR[input.dir]) {     // one-way hop
        const lx = nx + dx, ly = ny + dy;
        if (inb(lx, ly) && pack.walk[ly][lx]) { state.cx = lx; state.cy = ly; ev.push({ t: "hop", dir: input.dir }); grassCheck(state, pack, ev); }
      }
    }
    return { state, events: ev };
  }
  const b = state.battle;
  if (b.phase === "intro") { if (input.type === "confirm") { b.phase = "quiz"; b.asked = pickQuestion(state); } }
  else if (b.phase === "quiz") {
    if (input.type === "run") { b.phase = "result"; b.result = { fled: true }; }
    else if (input.type === "answer") {
      const a = b.asked; a.attempts++;
      if (input.index === a.correct) {
        const dmg = b.mon.atk + randInt(state, 4); b.enemy.hp = Math.max(0, b.enemy.hp - dmg);
        b.log = `${b.mon.species} attacked! (-${dmg})`; state.streak++; ev.push({ t: "playerHit", dmg });
        if (b.enemy.hp <= 0) { state.battlesWon++; b.phase = "result"; b.result = { win: true }; ev.push({ t: "win" }); }
        else { enemyTurn(state, ev); if (b.mon.hp <= 0) { b.phase = "result"; b.result = { lose: true }; } else b.asked = pickQuestion(state); }
      } else if (a.attempts < 2) { ev.push({ t: "retry" }); }   // gentle: hint + one retry, no enemy turn
      else {
        state.streak = 0; b.log = `Missed! (it was ${a.correctText})`; ev.push({ t: "miss" });
        enemyTurn(state, ev); if (b.mon.hp <= 0) { b.phase = "result"; b.result = { lose: true }; } else b.asked = pickQuestion(state);
      }
    }
  } else if (b.phase === "result") { if (input.type === "confirm") { state.mode = "overworld"; state.battle = null; } }
  return { state, events: ev };
}

function grassCheck(state, pack, ev) {
  if (pack.grass[state.cy][state.cx] && nextRand(state) < (pack.encounterRate || 0.18)) {
    startBattle(state, pack); ev.push({ t: "encounter", species: state.battle.enemy.species });
  }
}

export function availableInputs(state, pack) {
  if (state.mode === "overworld") return ["up", "down", "left", "right"].map(d => ({ type: "move", dir: d }));
  const b = state.battle;
  if (b.phase === "quiz") return b.asked.options.map((_, i) => ({ type: "answer", index: i })).concat([{ type: "run" }]);
  return [{ type: "confirm" }];
}

export function saveGame(state) {
  const json = JSON.stringify(state);
  let sum = 0; for (let i = 0; i < json.length; i++) sum = (sum * 31 + json.charCodeAt(i)) >>> 0;
  return JSON.stringify({ v: 3, sum, data: json });
}
export function loadGame(str, pack, fb) {
  try {
    const w = JSON.parse(str); if (!w || w.v !== 3 || typeof w.data !== "string") throw 0;
    let sum = 0; for (let i = 0; i < w.data.length; i++) sum = (sum * 31 + w.data.charCodeAt(i)) >>> 0;
    if (sum !== w.sum) throw 0;
    const s = JSON.parse(w.data); if (!s || typeof s.cx !== "number") throw 0; return s;
  } catch (e) { return newGame(pack, fb || 1); }
}
