// =============================================================================
// Quiz Quest v3 -- LOGIC CORE (pure, deterministic, no pictures).
// The "brain": walking + collision on the real map, and the quiz. It reads a
// Game Pack (the town/map data) and the question bank, but knows nothing about
// graphics, so the audit harness can run it thousands of times per second.
// All randomness goes through state.seed, so every playthrough is reproducible.
// =============================================================================
import { QUESTIONS } from "./questions.js";
export { QUESTIONS };

export function nextRand(state) {              // mulberry32
  let t = (state.seed = (state.seed + 0x6D2B79F5) >>> 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
export function randInt(state, n) { return Math.floor(nextRand(state) * n); }

export function newGame(pack, seed) {
  return {
    seed: (seed >>> 0) || 1,
    mode: "overworld",            // overworld | quiz | result
    cx: pack.start[0], cy: pack.start[1], facing: "down",
    steps: 0, quizzesWon: 0, quizzesSeen: 0,
    streak: 0, lastSubject: -1,
    asked: null, result: null,
  };
}

const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

function pickQuestion(state) {
  // slice: grade 1, just cycle subjects so it's not repetitive
  let pool = QUESTIONS.filter(q => q.grade === 1);
  if (!pool.length) pool = QUESTIONS;
  let q = pool[randInt(state, pool.length)];
  for (let i = 0; i < 8 && q.subject === state.lastSubject; i++) q = pool[randInt(state, pool.length)];
  state.lastSubject = q.subject;
  // shuffle the options deterministically; remember where the correct one is
  const opts = q.answers.slice();
  for (let i = opts.length - 1; i > 0; i--) { const j = randInt(state, i + 1); const t = opts[i]; opts[i] = opts[j]; opts[j] = t; }
  return { text: q.text, options: opts, correct: opts.indexOf(q.correct),
           correctText: q.correct, hint: q.hint, clock: q.clock, attempts: 0 };
}

export function step(state, pack, input) {
  const events = [];
  state.steps++;
  if (state.mode === "overworld" && input.type === "move") {
    state.facing = input.dir;
    const [dx, dy] = DIRS[input.dir];
    const nx = state.cx + dx, ny = state.cy + dy;
    const inb = nx >= 0 && ny >= 0 && nx < pack.cw && ny < pack.ch;
    if (inb && pack.walk[ny][nx]) {
      state.cx = nx; state.cy = ny;
      if (nextRand(state) < 0.20) {              // tall-grass-style random encounter
        state.mode = "quiz"; state.asked = pickQuestion(state); state.quizzesSeen++;
        events.push({ t: "encounter", q: state.asked.text });
      }
    } // else: blocked -> just turned to face that way
  } else if (state.mode === "quiz" && input.type === "answer") {
    const a = state.asked; a.attempts++;
    if (input.index === a.correct) {
      state.streak++; state.quizzesWon++;
      state.mode = "result"; state.result = { win: true, firstTry: a.attempts === 1 };
      events.push({ t: "answer", correct: true });
    } else if (a.attempts < 2) {
      events.push({ t: "retry" });                // gentle: hint + one more try
    } else {
      state.streak = 0;
      state.mode = "result"; state.result = { win: false, correctText: a.correctText };
      events.push({ t: "answer", correct: false });
    }
  } else if (state.mode === "result" && input.type === "confirm") {
    state.mode = "overworld"; state.asked = null; state.result = null;
  }
  return { state, events };
}

export function availableInputs(state, pack) {
  if (state.mode === "overworld") return ["up", "down", "left", "right"].map(d => ({ type: "move", dir: d }));
  if (state.mode === "quiz") return state.asked.options.map((_, i) => ({ type: "answer", index: i }));
  return [{ type: "confirm" }];
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
