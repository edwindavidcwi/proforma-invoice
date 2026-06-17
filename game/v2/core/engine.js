// =============================================================================
// Quiz Quest v2 -- LOGIC CORE (pure, deterministic, no DOM/canvas).
// The same module powers the playable game (browser) and the audit harness
// (Node). All randomness flows through a seedable RNG stored in the state, so
// every playthrough is reproducible from its seed. step(state, input) is the
// single entry point; it mutates+returns the state and a list of events.
//
// Content (creatures, world, names) is ORIGINAL -- faithful in *mechanics* to
// the classic monster-RPG, but our own world ("Sunny Town", "Sprigling", ...).
// =============================================================================
import { QUESTIONS } from "./questions.js";
export { QUESTIONS };

// ---- seedable RNG (mulberry32): state.seed is a uint32 we advance ----------
export function nextRand(state) {
  let t = (state.seed = (state.seed + 0x6D2B79F5) >>> 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
export function randInt(state, n) { return Math.floor(nextRand(state) * n); }

// ---- elemental type chart (generic elements; not copyrighted) --------------
export const TYPES = ["Normal", "Leaf", "Flame", "Aqua", "Spark", "Stone"];
// multiplier of attacker-type vs defender-type (2 = strong, 0.5 = weak)
const STRONG = { Flame: "Leaf", Leaf: "Aqua", Aqua: "Flame", Spark: "Aqua", Stone: "Flame" };
const WEAK = { Flame: "Aqua", Leaf: "Flame", Aqua: "Leaf", Spark: "Stone", Stone: "Aqua" };
export function typeMult(atk, def) {
  if (STRONG[atk] === def) return 2;
  if (WEAK[atk] === def) return 0.5;
  return 1;
}

// ---- moves -----------------------------------------------------------------
export const MOVES = {
  Tackle: { name: "Tackle", type: "Normal", power: 7 },
  Leafcut: { name: "Leafcut", type: "Leaf", power: 9 },
  Ember: { name: "Ember", type: "Flame", power: 9 },
  Bubble: { name: "Bubble", type: "Aqua", power: 9 },
  Zap: { name: "Zap", type: "Spark", power: 9 },
  Pebble: { name: "Pebble", type: "Stone", power: 9 },
};

// ---- creatures (original) --------------------------------------------------
// hp/atk/def are simple flat stats for the slice; levels scale them lightly.
export const SPECIES = {
  Sprigling: { name: "Sprigling", type: "Leaf",  hp: 22, atk: 7, def: 6, moves: ["Tackle", "Leafcut"], color: "#3fb96b" },
  Flarepup:  { name: "Flarepup",  type: "Flame", hp: 21, atk: 8, def: 5, moves: ["Tackle", "Ember"],   color: "#f0663a" },
  Dripling:  { name: "Dripling",  type: "Aqua",  hp: 23, atk: 7, def: 6, moves: ["Tackle", "Bubble"],  color: "#3a9bf0" },
  Sparkit:   { name: "Sparkit",   type: "Spark", hp: 18, atk: 7, def: 5, moves: ["Tackle", "Zap"],     color: "#f0c64a" },
  Pebbo:     { name: "Pebbo",     type: "Stone", hp: 24, atk: 6, def: 8, moves: ["Tackle", "Pebble"],  color: "#b08a5a" },
  Buggle:    { name: "Buggle",    type: "Leaf",  hp: 17, atk: 6, def: 5, moves: ["Tackle"],            color: "#9bbf3a" },
};
export const STARTERS = ["Sprigling", "Flarepup", "Dripling"];
const WILD = ["Sparkit", "Pebbo", "Buggle"];

export function makeMon(state, species, level) {
  const s = SPECIES[species];
  const lv = level || 5;
  const maxHp = s.hp + (lv - 5) * 3;
  return { species, name: s.name, type: s.type, level: lv,
    maxHp, hp: maxHp, atk: s.atk + (lv - 5), def: s.def + ((lv - 5) >> 1), moves: s.moves.slice() };
}

// ---- world map (single grid for the slice) ---------------------------------
// Legend: . path  , grass(tall=encounters)  # wall/tree  ~ water  P professor
//         G goal sign  S start  H house
const MAP_ROWS = [
  "##########",
  "#..H...P.#",
  "#..S.....#",
  "#........#",
  "#.,,,,,,.#",
  "#.,,,,,,.#",
  "#.,,,,,,.#",
  "#.,,,,,,.#",
  "#...G....#",
  "##########",
];
export const MAP = { w: 10, h: 10, rows: MAP_ROWS };
function tileAt(x, y) {
  if (y < 0 || y >= MAP.h || x < 0 || x >= MAP.w) return "#";
  return MAP.rows[y][x];
}
function isWall(x, y) { const t = tileAt(x, y); return t === "#" || t === "~" || t === "H"; }
function isProfessor(x, y) { return tileAt(x, y) === "P"; }
function isGrass(x, y) { return tileAt(x, y) === ","; }
function isGoal(x, y) { return tileAt(x, y) === "G"; }
function startPos() {
  for (let y = 0; y < MAP.h; y++) { const x = MAP.rows[y].indexOf("S"); if (x >= 0) return { x, y }; }
  return { x: 1, y: 1 };
}

// ---- new game --------------------------------------------------------------
export function newGame(seed) {
  const sp = startPos();
  return {
    seed: (seed >>> 0) || 1,
    mode: "overworld",              // overworld | dialog | battle
    x: sp.x, y: sp.y, facing: "down",
    party: [],                      // creatures
    flags: { hasStarter: false },
    badges: 0,
    battlesWon: 0,
    sliceComplete: false,
    quiz: { streak: 0, missRun: 0, lastSubject: -1 },
    dialog: null,                   // { lines:[...], idx, effect }
    battle: null,                   // see startBattle
    steps: 0,
  };
}

// ---- quiz selection + checking ---------------------------------------------
function gradeFor(state) {
  let g = Math.min(5, ((state.badges >> 1) + 1));
  if (state.quiz.streak >= 4) g = Math.min(5, g + 1);
  else if (state.quiz.missRun >= 3) g = Math.max(1, g - 1);
  return g;
}
function pickQuestion(state) {
  const g = gradeFor(state);
  // candidates at this grade; avoid repeating the previous subject when possible
  let pool = QUESTIONS.filter(q => q.grade === g);
  if (!pool.length) pool = QUESTIONS;
  for (let tries = 0; tries < 16; tries++) {
    const q = pool[randInt(state, pool.length)];
    if (q.subjectId === undefined) q.subjectId = q.subject; // stable
    if (q.subject !== state.quiz.lastSubject || tries > 8) {
      state.quiz.lastSubject = q.subject;
      return buildAsked(state, q);
    }
  }
  return buildAsked(state, pool[0]);
}
function buildAsked(state, q) {
  // shuffle answer order deterministically; remember where the correct one is
  const opts = q.answers.slice();
  for (let i = opts.length - 1; i > 0; i--) { const j = randInt(state, i + 1); const t = opts[i]; opts[i] = opts[j]; opts[j] = t; }
  return { text: q.text, options: opts, correctText: q.correct,
    correct: opts.indexOf(q.correct), hint: q.hint, clock: q.clock,
    grade: q.grade, subject: q.subject, attempts: 0 };
}
export function checkAnswer(asked, index) { return index === asked.correct; }

// ---- battle ----------------------------------------------------------------
function wildEncounter(state) {
  const species = WILD[randInt(state, WILD.length)];
  const level = 4 + randInt(state, 3);
  return makeMon(state, species, level);
}
function startBattle(state, enemy) {
  state.mode = "battle";
  state.battle = {
    enemy, phase: "intro", // intro | menu | quiz | resolve | done
    asked: null, pendingMove: null, log: [], result: null,
  };
}
function activeMon(state) { return state.party.find(m => m.hp > 0) || state.party[0]; }
function dealDamage(attacker, defender, move, mult) {
  const base = move.power + attacker.atk - Math.floor(defender.def / 2);
  let dmg = Math.max(1, Math.round(base * mult));
  defender.hp = Math.max(0, defender.hp - dmg);
  return dmg;
}
function enemyTurn(state) {
  const b = state.battle, me = activeMon(state);
  if (me.hp <= 0) return;
  const mv = MOVES[b.enemy.moves[randInt(state, b.enemy.moves.length)]];
  const mult = typeMult(mv.type, me.type);
  const dmg = dealDamage(b.enemy, me, mv, mult);
  b.log.push(`Enemy ${b.enemy.name} used ${mv.name}! (-${dmg})`);
}
function afterTurns(state, events) {
  const b = state.battle, me = activeMon(state);
  if (b.enemy.hp <= 0) {
    state.battlesWon++;
    state.quiz.streak++; // a clean win nudges difficulty up over time
    b.phase = "done"; b.result = "win"; b.log.push(`${b.enemy.name} fainted! You win!`);
    events.push({ t: "win" });
  } else if (me.hp <= 0) {
    b.phase = "done"; b.result = "lose"; b.log.push(`${me.name} fainted...`);
    events.push({ t: "lose" });
  } else {
    b.phase = "menu";
  }
}
function endBattle(state) {
  const b = state.battle;
  // kid-friendly: full heal after every battle, win or lose; no penalty.
  for (const m of state.party) m.hp = m.maxHp;
  if (b.result === "lose") { const sp = startPos(); state.x = sp.x; state.y = sp.y; }
  if (state.flags.hasStarter && state.battlesWon >= 1) state.sliceComplete = true;
  state.mode = "overworld"; state.battle = null;
}

// ---- dialog ----------------------------------------------------------------
function openDialog(state, lines, effect) { state.mode = "dialog"; state.dialog = { lines, idx: 0, effect: effect || null }; }

// =============================================================================
// step(state, input) -> { state, events }   -- the single reducer
// input: {type:'move',dir} | {type:'interact'} | {type:'confirm'} |
//        {type:'answer',index} | {type:'run'} | {type:'fight'} | {type:'starter',index}
// =============================================================================
export function step(state, input) {
  const events = [];
  state.steps++;
  try {
    if (state.mode === "overworld") stepOverworld(state, input, events);
    else if (state.mode === "dialog") stepDialog(state, input, events);
    else if (state.mode === "battle") stepBattle(state, input, events);
  } catch (e) {
    events.push({ t: "error", msg: String(e && e.message || e) });
    throw e; // the harness records the seed; the game's outer guard catches it
  }
  return { state, events };
}

const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
function stepOverworld(state, input, events) {
  if (input.type === "move") {
    state.facing = input.dir;
    const [dx, dy] = DIRS[input.dir];
    const nx = state.x + dx, ny = state.y + dy;
    if (isWall(nx, ny) || isProfessor(nx, ny)) return; // blocked
    state.x = nx; state.y = ny;
    if (isGoal(nx, ny)) events.push({ t: "atGoal" });
    if (isGrass(nx, ny) && state.flags.hasStarter) {
      // chance of a wild encounter when walking in tall grass
      if (nextRand(state) < 0.28) { startBattle(state, wildEncounter(state)); events.push({ t: "encounter" }); }
    }
    return;
  }
  if (input.type === "interact") {
    const [dx, dy] = DIRS[state.facing];
    if (isProfessor(state.x + dx, state.y + dy)) {
      if (!state.flags.hasStarter) {
        openDialog(state,
          ["PROF: Welcome! Pick a partner to begin your quest.",
           "(Choose your starter!)"],
          { kind: "chooseStarter" });
      } else {
        openDialog(state, ["PROF: Find tall grass and win a battle. Answer well!"], null);
      }
    }
    return;
  }
}

function stepDialog(state, input, events) {
  const d = state.dialog;
  // a starter-choice dialog waits for {type:'starter',index}
  if (d.effect && d.effect.kind === "chooseStarter") {
    if (input.type === "starter") {
      const sp = STARTERS[input.index % STARTERS.length];
      state.party = [makeMon(state, sp, 5)];
      state.flags.hasStarter = true;
      events.push({ t: "gotStarter", species: sp });
      state.mode = "overworld"; state.dialog = null;
    }
    return; // ignore other inputs until a starter is chosen
  }
  if (input.type === "confirm" || input.type === "interact") {
    d.idx++;
    if (d.idx >= d.lines.length) { state.mode = "overworld"; state.dialog = null; }
  }
}

function stepBattle(state, input, events) {
  const b = state.battle;
  if (b.phase === "intro") { if (input.type === "confirm" || input.type === "interact") b.phase = "menu"; return; }
  if (b.phase === "done") { if (input.type === "confirm" || input.type === "interact") endBattle(state); return; }
  if (b.phase === "menu") {
    if (input.type === "run") { // kid-friendly: fleeing always works
      b.result = "flee"; b.phase = "done"; b.log.push("Got away safely!");
      // fleeing isn't a loss; close immediately on next confirm
      return;
    }
    if (input.type === "fight") {
      // use the active mon's strongest-typed move (slice keeps move-choice simple)
      const me = activeMon(state);
      b.pendingMove = me.moves[me.moves.length - 1];
      b.asked = pickQuestion(state);
      b.phase = "quiz";
      events.push({ t: "ask", q: b.asked.text });
    }
    return;
  }
  if (b.phase === "quiz") {
    if (input.type !== "answer") return;
    const ok = checkAnswer(b.asked, input.index);
    b.asked.attempts++;
    const me = activeMon(state);
    if (ok) {
      const mv = MOVES[b.pendingMove];
      const mult = typeMult(mv.type, b.enemy.type);
      const dmg = dealDamage(me, b.enemy, mv, mult);
      b.log.push(`${me.name} used ${mv.name}! (-${dmg})`);
      if (b.asked.attempts === 1) { state.quiz.missRun = 0; } // first-try mastery
      events.push({ t: "answer", correct: true });
      // enemy retaliates if still standing, then resolve
      if (b.enemy.hp > 0) enemyTurn(state);
      b.asked = null; b.phase = "resolve"; afterTurns(state, events);
    } else {
      events.push({ t: "answer", correct: false });
      if (b.asked.attempts < 2) {
        b.log.push(`Not quite -- hint: ${b.asked.hint}. Try again!`);
        // gentle: a hint + one retry, no turn lost yet
      } else {
        // second miss: the move misses, enemy attacks, difficulty eases
        state.quiz.streak = 0; state.quiz.missRun++;
        b.log.push(`The move missed! (answer was ${b.asked.correctText})`);
        enemyTurn(state);
        b.asked = null; b.phase = "resolve"; afterTurns(state, events);
      }
    }
    return;
  }
}

// ---- what inputs are valid right now (drives the harness + soft-lock check) -
export function availableInputs(state) {
  if (state.mode === "overworld") {
    const ins = [{ type: "interact" }];
    for (const dir of ["up", "down", "left", "right"]) ins.push({ type: "move", dir });
    return ins;
  }
  if (state.mode === "dialog") {
    if (state.dialog.effect && state.dialog.effect.kind === "chooseStarter")
      return STARTERS.map((_, i) => ({ type: "starter", index: i }));
    return [{ type: "confirm" }];
  }
  if (state.mode === "battle") {
    const b = state.battle;
    if (b.phase === "intro" || b.phase === "done") return [{ type: "confirm" }];
    if (b.phase === "menu") return [{ type: "fight" }, { type: "run" }];
    if (b.phase === "quiz") return b.asked.options.map((_, i) => ({ type: "answer", index: i }));
  }
  return [{ type: "confirm" }];
}

// ---- save / load with integrity --------------------------------------------
export function saveGame(state) {
  const json = JSON.stringify(state);
  let sum = 0; for (let i = 0; i < json.length; i++) sum = (sum * 31 + json.charCodeAt(i)) >>> 0;
  return JSON.stringify({ v: 2, sum, data: json });
}
export function loadGame(str, fallbackSeed) {
  try {
    const wrap = JSON.parse(str);
    if (!wrap || wrap.v !== 2 || typeof wrap.data !== "string") throw 0;
    let sum = 0; for (let i = 0; i < wrap.data.length; i++) sum = (sum * 31 + wrap.data.charCodeAt(i)) >>> 0;
    if (sum !== wrap.sum) throw 0;            // corrupt -> start fresh
    const s = JSON.parse(wrap.data);
    if (!s || typeof s.x !== "number" || !Array.isArray(s.party)) throw 0;
    return s;
  } catch (e) {
    return newGame(fallbackSeed || 1);        // never crash on a bad save
  }
}
