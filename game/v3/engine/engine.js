// =============================================================================
// Quiz Quest v3 -- LOGIC CORE (pure, deterministic, no pictures).
// Walking + real collision on the authentic map, and quiz BATTLES that only
// start in tall grass (never randomly while you walk paths/town). Reads a Game
// Pack + the question bank; no graphics, so the audit can run it thousands of
// times per second. All randomness flows through state.seed (reproducible).
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
  return {
    seed: (seed >>> 0) || 1,
    mode: "overworld",                 // overworld | battle
    cx: pack.start[0], cy: pack.start[1], facing: "down",
    steps: 0, battlesWon: 0, battlesSeen: 0, streak: 0, lastSubject: -1,
    battle: null,
  };
}

const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

function pickQuestion(state) {
  let pool = QUESTIONS.filter(q => q.grade === 1);
  if (!pool.length) pool = QUESTIONS;
  let q = pool[randInt(state, pool.length)];
  for (let i = 0; i < 8 && q.subject === state.lastSubject; i++) q = pool[randInt(state, pool.length)];
  state.lastSubject = q.subject;
  const opts = q.answers.slice();
  for (let i = opts.length - 1; i > 0; i--) { const j = randInt(state, i + 1); const t = opts[i]; opts[i] = opts[j]; opts[j] = t; }
  return { text: q.text, options: opts, correct: opts.indexOf(q.correct),
           correctText: q.correct, hint: q.hint, clock: q.clock, attempts: 0 };
}

function startBattle(state, pack) {
  const names = pack.creatureNames && pack.creatureNames.length ? pack.creatureNames : ["wild one"];
  const species = names[randInt(state, names.length)];
  state.mode = "battle"; state.battlesSeen++;
  state.battle = { species, hp: 2, maxHp: 2, phase: "intro", asked: null, result: null };
}

export function step(state, pack, input) {
  const events = [];
  state.steps++;
  if (state.mode === "overworld") {
    if (input.type === "move") {
      state.facing = input.dir;
      const [dx, dy] = DIRS[input.dir];
      const nx = state.cx + dx, ny = state.cy + dy;
      const inb = nx >= 0 && ny >= 0 && nx < pack.cw && ny < pack.ch;
      if (inb && pack.walk[ny][nx]) {
        state.cx = nx; state.cy = ny;
        // ONLY tall grass can trigger a wild encounter -- never plain walking
        if (pack.grass[ny][nx] && nextRand(state) < (pack.encounterRate || 0.18)) {
          startBattle(state, pack); events.push({ t: "encounter", species: state.battle.species });
        }
      }
    }
    return { state, events };
  }
  // ---- battle ----
  const b = state.battle;
  if (b.phase === "intro") {
    if (input.type === "confirm") { b.phase = "quiz"; b.asked = pickQuestion(state); }
  } else if (b.phase === "quiz") {
    if (input.type === "answer") {
      const a = b.asked; a.attempts++;
      if (input.index === a.correct) {
        b.hp--; state.streak++;
        events.push({ t: "answer", correct: true });
        if (b.hp <= 0) { state.battlesWon++; b.phase = "result"; b.result = { win: true }; events.push({ t: "win" }); }
        else b.asked = pickQuestion(state);          // creature still up -> next question
      } else if (a.attempts < 2) {
        events.push({ t: "retry" });                  // gentle: hint + one retry
      } else {
        state.streak = 0; b.phase = "result"; b.result = { win: false, correctText: a.correctText };
        events.push({ t: "answer", correct: false });
      }
    } else if (input.type === "run") {
      b.phase = "result"; b.result = { fled: true };
    }
  } else if (b.phase === "result") {
    if (input.type === "confirm") { state.mode = "overworld"; state.battle = null; }
  }
  return { state, events };
}

export function availableInputs(state, pack) {
  if (state.mode === "overworld") return ["up", "down", "left", "right"].map(d => ({ type: "move", dir: d }));
  const b = state.battle;
  if (b.phase === "quiz") return b.asked.options.map((_, i) => ({ type: "answer", index: i })).concat([{ type: "run" }]);
  return [{ type: "confirm" }];               // intro / result
}

export function saveGame(state) {
  const json = JSON.stringify(state);
  let sum = 0; for (let i = 0; i < json.length; i++) sum = (sum * 31 + json.charCodeAt(i)) >>> 0;
  return JSON.stringify({ v: 3, sum, data: json });
}
export function loadGame(str, pack, fallbackSeed) {
  try {
    const w = JSON.parse(str);
    if (!w || w.v !== 3 || typeof w.data !== "string") throw 0;
    let sum = 0; for (let i = 0; i < w.data.length; i++) sum = (sum * 31 + w.data.charCodeAt(i)) >>> 0;
    if (sum !== w.sum) throw 0;
    const s = JSON.parse(w.data);
    if (!s || typeof s.cx !== "number") throw 0;
    return s;
  } catch (e) { return newGame(pack, fallbackSeed || 1); }
}
