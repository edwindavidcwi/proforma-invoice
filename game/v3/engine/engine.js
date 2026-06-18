// =============================================================================
// Quiz Quest v3 -- LOGIC CORE (pure, deterministic). Walking + collision +
// ledge hops, and a full battle: a real menu (FIGHT -> pick a move, BAG,
// POKEMON list to switch, RUN), the quiz powers your move, the enemy attacks
// back, HP, fainting/switching, catching. Encounters only in tall grass.
// =============================================================================
import { QUESTIONS } from "./questions.js";
export { QUESTIONS };

export function nextRand(s) { let t = (s.seed = (s.seed + 0x6D2B79F5) >>> 0); t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
export function randInt(s, n) { return Math.floor(nextRand(s) * n); }

// creature definitions (original stats/moves; sprites come from the Game Pack)
export const CDEF = {
  charmander: { name: "Charmander", hp: 19, atk: 6, moves: [{ name: "Scratch", power: 6 }, { name: "Ember", power: 10 }] },
  squirtle:   { name: "Squirtle",   hp: 20, atk: 6, moves: [{ name: "Tackle", power: 6 }, { name: "Bubble", power: 10 }] },
  rattata:    { name: "Rattata",    hp: 12, atk: 4, moves: [{ name: "Tackle", power: 5 }] },
  pidgey:     { name: "Pidgey",     hp: 13, atk: 4, moves: [{ name: "Gust", power: 5 }] },
};
function makeMon(species) {
  const d = CDEF[species] || CDEF.rattata;
  return { species, name: d.name, hp: d.hp, maxHp: d.hp, atk: d.atk, moves: d.moves.map(m => ({ ...m })) };
}

export function newGame(pack, seed) {
  return { seed: (seed >>> 0) || 1, mode: "overworld", cx: pack.start[0], cy: pack.start[1], facing: "down",
    steps: 0, battlesWon: 0, battlesSeen: 0, streak: 0, lastSubject: -1,
    party: (pack.party || ["charmander"]).map(makeMon), potions: 3, battle: null };
}

const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
const LEDGE_FOR = { down: 1, left: 2, right: 3 };

function pickQuestion(state) {
  let pool = QUESTIONS.filter(q => q.grade === 1); if (!pool.length) pool = QUESTIONS;
  let q = pool[randInt(state, pool.length)];
  for (let i = 0; i < 8 && q.subject === state.lastSubject; i++) q = pool[randInt(state, pool.length)];
  state.lastSubject = q.subject;
  const opts = q.answers.slice();
  for (let i = opts.length - 1; i > 0; i--) { const j = randInt(state, i + 1); const t = opts[i]; opts[i] = opts[j]; opts[j] = t; }
  return { text: q.text, options: opts, correct: opts.indexOf(q.correct), correctText: q.correct, hint: q.hint, clock: q.clock, attempts: 0 };
}
const active = state => state.party[state.battle.partyIdx];
const anyAlive = state => state.party.some(m => m.hp > 0);

function startBattle(state, pack) {
  const wild = (pack.wild && pack.wild.length) ? pack.wild : ["rattata"];
  const enemy = makeMon(wild[randInt(state, wild.length)]);
  let idx = state.party.findIndex(m => m.hp > 0); if (idx < 0) idx = 0;
  state.mode = "battle"; state.battlesSeen++;
  state.battle = { enemy, partyIdx: idx, phase: "intro", asked: null, move: null, log: "", result: null, catchCount: 0, returnTo: "menu" };
}

// enemy takes its turn; returns true if the battle continues (else result set)
function enemyTurn(state, ev) {
  const b = state.battle, me = active(state);
  if (me.hp <= 0) return true;
  const mv = b.enemy.moves[randInt(state, b.enemy.moves.length)];
  const dmg = mv.power + b.enemy.atk + randInt(state, 3); me.hp = Math.max(0, me.hp - dmg);
  b.log = `Wild ${b.enemy.name} used ${mv.name}! (-${dmg})`; ev.push({ t: "enemyHit", dmg });
  if (me.hp <= 0) {
    ev.push({ t: "faint", who: "mon" });
    if (anyAlive(state)) { b.phase = "party"; b.forced = true; b.log = `${me.name} fainted! Choose another.`; }
    else { b.phase = "result"; b.result = { lose: true }; }
    return false;
  }
  return true;
}

export function step(state, pack, input) {
  const ev = []; state.steps++;
  if (state.mode === "overworld") return overworld(state, pack, input, ev), { state, events: ev };
  const b = state.battle, me = active(state);
  switch (b.phase) {
    case "intro": if (input.type === "confirm") b.phase = "menu"; break;
    case "menu":
      if (input.type === "menu") {
        if (input.choice === "fight") b.phase = "moves";
        else if (input.choice === "bag") b.phase = "bag";
        else if (input.choice === "party") { b.phase = "party"; b.forced = false; }
        else if (input.choice === "run") { b.phase = "result"; b.result = { fled: true }; }
      } break;
    case "moves":
      if (input.type === "back") b.phase = "menu";
      else if (input.type === "move") { b.move = me.moves[input.index]; b.asked = pickQuestion(state); b.returnTo = "fight"; b.phase = "quiz"; }
      break;
    case "bag":
      if (input.type === "back") b.phase = "menu";
      else if (input.type === "item") {
        if (input.which === "potion" && state.potions > 0 && me.hp < me.maxHp) {
          state.potions--; const heal = Math.min(me.maxHp - me.hp, 12); me.hp += heal;
          b.log = `Used a Potion! (+${heal})`; ev.push({ t: "heal" }); enemyTurn(state, ev); if (b.phase === "bag") b.phase = "menu";
        } else if (input.which === "ball") { b.phase = "catch"; b.catchCount = 0; b.asked = pickQuestion(state); }
      } break;
    case "party":
      if (input.type === "back" && !b.forced) b.phase = "menu";
      else if (input.type === "switch" && state.party[input.index] && state.party[input.index].hp > 0) {
        const wasForced = b.forced; b.partyIdx = input.index; b.forced = false;
        b.log = `Go, ${state.party[input.index].name}!`; ev.push({ t: "switch" });
        if (!wasForced) enemyTurn(state, ev);   // a manual switch costs your turn
        if (b.phase === "party") b.phase = "menu";
      } break;
    case "quiz": {
      if (input.type !== "answer") break;
      const a = b.asked; a.attempts++;
      if (input.index === a.correct) {
        const dmg = b.move.power + me.atk + randInt(state, 3); b.enemy.hp = Math.max(0, b.enemy.hp - dmg);
        b.log = `${me.name} used ${b.move.name}! (-${dmg})`; state.streak++; ev.push({ t: "playerHit", dmg });
        if (b.enemy.hp <= 0) { state.battlesWon++; b.phase = "result"; b.result = { win: true }; ev.push({ t: "win" }); }
        else if (enemyTurn(state, ev)) b.phase = "menu";
      } else if (a.attempts < 2) { ev.push({ t: "retry" }); }
      else { state.streak = 0; b.log = `Missed! (it was ${a.correctText})`; ev.push({ t: "miss" }); if (enemyTurn(state, ev)) b.phase = "menu"; }
      break;
    }
    case "catch": {
      if (input.type !== "answer") break;
      const a = b.asked;
      if (input.index === a.correct) {
        b.catchCount++;
        if (b.catchCount >= 5) {                       // 5 in a row -> caught
          b.phase = "result"; b.result = { caught: true };
          if (state.party.length < 6) state.party.push(makeMon(b.enemy.species));
          ev.push({ t: "caught" });
        } else b.asked = pickQuestion(state);
      } else { b.log = `It broke free! (it was ${a.correctText})`; ev.push({ t: "catchFail" }); if (enemyTurn(state, ev)) b.phase = "menu"; }
      break;
    }
    case "result": if (input.type === "confirm") { for (const m of state.party) m.hp = m.maxHp; state.mode = "overworld"; state.battle = null; } break;
  }
  return { state, events: ev };
}

function overworld(state, pack, input, ev) {
  if (input.type !== "move") return;
  state.facing = input.dir;
  const [dx, dy] = DIRS[input.dir], nx = state.cx + dx, ny = state.cy + dy;
  const inb = (x, y) => x >= 0 && y >= 0 && x < pack.cw && y < pack.ch;
  if (inb(nx, ny) && pack.walk[ny][nx]) { state.cx = nx; state.cy = ny; grassCheck(state, pack, ev); }
  else if (inb(nx, ny) && pack.ledge[ny][nx] === LEDGE_FOR[input.dir]) {
    const lx = nx + dx, ly = ny + dy;
    if (inb(lx, ly) && pack.walk[ly][lx]) { state.cx = lx; state.cy = ly; ev.push({ t: "hop", dir: input.dir }); grassCheck(state, pack, ev); }
  }
}
function grassCheck(state, pack, ev) {
  if (pack.grass[state.cy][state.cx] && nextRand(state) < (pack.encounterRate || 0.18)) { startBattle(state, pack); ev.push({ t: "encounter" }); }
}

export function availableInputs(state, pack) {
  if (state.mode === "overworld") return ["up", "down", "left", "right"].map(d => ({ type: "move", dir: d }));
  const b = state.battle, me = active(state);
  switch (b.phase) {
    case "menu": return [{ type: "menu", choice: "fight" }, { type: "menu", choice: "bag" }, { type: "menu", choice: "party" }, { type: "menu", choice: "run" }];
    case "moves": return me.moves.map((_, i) => ({ type: "move", index: i })).concat([{ type: "back" }]);
    case "bag": return [{ type: "item", which: "potion" }, { type: "item", which: "ball" }, { type: "back" }];
    case "party": { const ins = state.party.map((m, i) => (m.hp > 0 && i !== b.partyIdx) ? { type: "switch", index: i } : null).filter(Boolean); if (!b.forced) ins.push({ type: "back" }); return ins.length ? ins : [{ type: "back" }]; }
    case "quiz": case "catch": return b.asked.options.map((_, i) => ({ type: "answer", index: i }));
    default: return [{ type: "confirm" }];   // intro / result
  }
}

export function saveGame(state) { const j = JSON.stringify(state); let s = 0; for (let i = 0; i < j.length; i++) s = (s * 31 + j.charCodeAt(i)) >>> 0; return JSON.stringify({ v: 4, sum: s, data: j }); }
export function loadGame(str, pack, fb) {
  try { const w = JSON.parse(str); if (!w || w.v !== 4 || typeof w.data !== "string") throw 0;
    let s = 0; for (let i = 0; i < w.data.length; i++) s = (s * 31 + w.data.charCodeAt(i)) >>> 0; if (s !== w.sum) throw 0;
    const o = JSON.parse(w.data); if (!o || typeof o.cx !== "number" || !Array.isArray(o.party)) throw 0; return o;
  } catch (e) { return newGame(pack, fb || 1); }
}
