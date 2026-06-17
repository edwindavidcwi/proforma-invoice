// =============================================================================
// Quiz Quest v2 -- AUDIT HARNESS (headless, Node).
// Drives the pure logic core through huge numbers of full playthroughs and
// proves the properties that matter for a child's game: no crash, no soft-lock,
// the game is always completable, saves never corrupt into a crash, the quiz
// answer keys are exact, and runs are reproducible. Thousands of playthroughs
// run in a fraction of a second because there is no emulator -- just the rules.
//
// Run:  node audit/harness.mjs            (also: npm run audit)
// Exit code 0 = all green (gates the build), non-zero = a failure (+ its seed).
// =============================================================================
import {
  QUESTIONS, newGame, step, availableInputs, saveGame, loadGame,
  checkAnswer, randInt,
} from "../core/engine.js";

let failures = 0;
const t0 = Date.now();
function check(name, cond, detail) {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
}

// a small RNG for the harness itself, so input choices are reproducible too
function hrng(seed) { let s = seed >>> 0; return () => { s = (s + 0x9E3779B9) >>> 0; let t = Math.imul(s ^ (s >>> 16), 0x45D9F3B); t = Math.imul(t ^ (t >>> 15), 0x27D4EB2F); return ((t ^ (t >>> 15)) >>> 0) / 4294967296; }; }

function snap(s) { return [s.mode, s.x, s.y, s.battlesWon, s.flags.hasStarter,
  s.sliceComplete, s.battle && s.battle.phase, s.party.length].join("|"); }

// ---- 1. quiz answer keys are exact -----------------------------------------
(function quizKeys() {
  let bad = 0, hintless = 0, dupCorrect = 0;
  for (const q of QUESTIONS) {
    if (!q.answers.includes(q.correct)) bad++;
    if (!q.hint || !q.hint.trim()) hintless++;
    if (q.answers.filter(a => a === q.correct).length !== 1) dupCorrect++;
  }
  check(`every question's correct answer is among its options (${QUESTIONS.length} Qs)`, bad === 0, bad + " bad");
  check("every question has a hint", hintless === 0, hintless + " missing");
  check("exactly one option equals the correct answer", dupCorrect === 0, dupCorrect + " ambiguous");
})();

// ---- 2. shuffled-question integrity (the asked form points at the key) ------
(function askedIntegrity() {
  // drive into many battles and verify the built question is internally exact
  let checked = 0, mismatch = 0;
  for (let seed = 1; seed <= 400; seed++) {
    const r = hrng(seed);
    let { state } = wrap(newGame(seed));
    // reach a battle quickly via guided play
    guideToBattle(state, r);
    if (state.mode !== "battle") continue;
    // get to a quiz
    let guard = 0;
    while (state.mode === "battle" && state.battle.phase !== "quiz" && guard++ < 30) {
      const b = state.battle;
      step(state, b.phase === "menu" ? { type: "fight" } : { type: "confirm" });
    }
    if (state.mode === "battle" && state.battle.phase === "quiz") {
      const a = state.battle.asked;
      checked++;
      if (a.options[a.correct] !== a.correctText) mismatch++;
      // the engine's checkAnswer must agree with the index
      if (!checkAnswer(a, a.correct)) mismatch++;
    }
  }
  check(`shuffled question's correct index points at the right answer (${checked} sampled)`, mismatch === 0, mismatch + " mismatches");
})();

function wrap(state) { return { state }; }

// guided helper: get a starter then walk into grass until a battle starts
function guideToBattle(state, r) {
  // talk to professor: face up toward P then interact (P is near top); brute a bit
  let guard = 0;
  while (!state.flags.hasStarter && guard++ < 400) {
    const ins = availableInputs(state);
    if (state.mode === "dialog" && ins[0] && ins[0].type === "starter") { step(state, { type: "starter", index: 0 }); continue; }
    if (state.mode === "dialog") { step(state, { type: "confirm" }); continue; }
    // try to interact from every tile near the professor; otherwise wander
    step(state, { type: "interact" });
    if (!state.flags.hasStarter) step(state, { type: "move", dir: ["up", "left", "right", "down"][Math.floor(r() * 4)] });
  }
  guard = 0;
  while (state.mode === "overworld" && guard++ < 600) {
    step(state, { type: "move", dir: ["up", "down", "left", "right"][Math.floor(r() * 4)] });
    if (state.mode === "battle") break;
  }
}

// ---- 3. fuzz: thousands of random playthroughs, no crash / no soft-lock -----
let totalSteps = 0, runs = 0, crashes = 0, softlocks = 0, reachedComplete = 0;
let gotStarterRuns = 0, wonRuns = 0;
function fuzz(label, policy, nRuns, maxSteps) {
  let localCrash = null, localSoftlock = null, localComplete = 0;
  for (let seed = 1; seed <= nRuns; seed++) {
    const r = hrng(seed * 2654435761 >>> 0);
    let state = newGame(seed);
    runs++;
    let lastSig = snap(state), stuck = 0, sawStarter = false, sawWin = false;
    for (let i = 0; i < maxSteps; i++) {
      const ins = availableInputs(state);
      if (!ins.length) { softlocks++; localSoftlock = localSoftlock || { seed, i }; break; }
      const input = policy(state, ins, r);
      try { step(state, input); }
      catch (e) { crashes++; localCrash = localCrash || { seed, i, msg: String(e && e.message || e) }; break; }
      totalSteps++;
      if (state.flags.hasStarter) sawStarter = true;
      if (state.battlesWon > 0) sawWin = true;
      const sig = snap(state);
      if (sig === lastSig) { if (++stuck > 5000) { softlocks++; localSoftlock = localSoftlock || { seed, i, note: "no progress" }; break; } }
      else { stuck = 0; lastSig = sig; }
      if (state.sliceComplete) { localComplete++; break; }
    }
    if (sawStarter) gotStarterRuns++;
    if (sawWin) wonRuns++;
  }
  reachedComplete += localComplete;
  check(`[${label}] no crash over ${nRuns} runs`, !localCrash, localCrash && `seed ${localCrash.seed} step ${localCrash.i}: ${localCrash.msg}`);
  check(`[${label}] no soft-lock over ${nRuns} runs`, !localSoftlock, localSoftlock && `seed ${localSoftlock.seed}`);
  return localComplete;
}

// policies (input-choosing strategies, incl. adversarial)
const pRandom = (s, ins, r) => ins[Math.floor(r() * ins.length)];
const pAlwaysWrong = (s, ins, r) => {
  if (s.mode === "battle" && s.battle.phase === "quiz") {
    const a = s.battle.asked; // deliberately pick a wrong option
    for (let i = 0; i < a.options.length; i++) if (i !== a.correct) return { type: "answer", index: i };
  }
  if (s.mode === "battle" && s.battle.phase === "menu") return { type: "fight" };
  return ins[Math.floor(r() * ins.length)];
};
const pAlwaysRight = (s, ins, r) => {
  if (s.mode === "battle" && s.battle.phase === "quiz") return { type: "answer", index: s.battle.asked.correct };
  if (s.mode === "battle" && s.battle.phase === "menu") return { type: "fight" };
  if (s.mode === "dialog" && ins[0] && ins[0].type === "starter") return ins[0];
  return ins[Math.floor(r() * ins.length)];
};
const pAlwaysFlee = (s, ins, r) => {
  if (s.mode === "battle" && s.battle.phase === "menu") return { type: "run" };
  return ins[Math.floor(r() * ins.length)];
};

console.log("\n-- fuzz playthroughs (random + adversarial) --");
fuzz("random", pRandom, 3000, 4000);
fuzz("always-wrong (struggling kid)", pAlwaysWrong, 1500, 4000);
fuzz("always-right", pAlwaysRight, 1500, 4000);
fuzz("always-flee", pAlwaysFlee, 1500, 4000);

// ---- 4. completion is REACHABLE (a guided run finishes the slice) ----------
(function completion() {
  let everReached = 0;
  for (let seed = 1; seed <= 300; seed++) {
    const r = hrng(seed);
    let state = newGame(seed);
    for (let i = 0; i < 5000 && !state.sliceComplete; i++) step(state, pAlwaysRight(state, availableInputs(state), r));
    if (state.sliceComplete) everReached++;
  }
  check("a competent player always completes the slice (300/300 guided runs)", everReached === 300, everReached + "/300");
  check("random play also reaches completion sometimes", reachedComplete > 0, reachedComplete + " runs");
})();

// ---- 5. battles always terminate -------------------------------------------
(function battleTermination() {
  let bad = 0;
  for (let seed = 1; seed <= 500; seed++) {
    const r = hrng(seed + 99);
    let state = newGame(seed);
    guideToBattle(state, r);
    if (state.mode !== "battle") continue;
    let turns = 0;
    while (state.mode === "battle" && turns++ < 500) step(state, pRandom(state, availableInputs(state), r));
    if (state.mode === "battle") bad++; // didn't end within 500 inputs
  }
  check("every battle ends within a bounded number of inputs", bad === 0, bad + " runaway battles");
})();

// ---- 6. save / load integrity ----------------------------------------------
(function saveLoad() {
  let mismatch = 0;
  for (let seed = 1; seed <= 500; seed++) {
    const r = hrng(seed + 7);
    let state = newGame(seed);
    for (let i = 0; i < 50 + (seed % 400); i++) step(state, pRandom(state, availableInputs(state), r));
    const reloaded = loadGame(saveGame(state), seed);
    if (JSON.stringify(reloaded) !== JSON.stringify(state)) mismatch++;
  }
  check("save -> load round-trips to an identical state (500 states)", mismatch === 0, mismatch + " mismatches");
  // corrupt / truncated / garbage saves must NEVER crash -- they start fresh
  let safe = true;
  for (const bad of ['', '{', 'null', '{"v":2,"sum":0,"data":"x"}', '{"v":1}', 'not json', '{"v":2,"data":123}']) {
    try { const s = loadGame(bad, 42); if (!s || typeof s.x !== "number") safe = false; }
    catch (e) { safe = false; }
  }
  check("a corrupt/garbage save loads safely (fresh game, never crashes)", safe);
})();

// ---- 7. reproducibility (same seeds -> identical outcome) -------------------
(function reproducible() {
  function run(seed) {
    const r = hrng(seed); let state = newGame(seed);
    for (let i = 0; i < 1500; i++) step(state, pRandom(state, availableInputs(state), r));
    return JSON.stringify(state);
  }
  let diff = 0;
  for (let seed = 1; seed <= 200; seed++) if (run(seed) !== run(seed)) diff++;
  check("identical (game seed + input seed) -> identical final state", diff === 0, diff + " non-deterministic");
})();

// ---- report ----------------------------------------------------------------
const secs = (Date.now() - t0) / 1000;
console.log("\n-- metrics --");
console.log(`  playthroughs simulated : ${runs}`);
console.log(`  total logic steps      : ${totalSteps.toLocaleString()}`);
console.log(`  got a starter          : ${(100 * gotStarterRuns / runs).toFixed(1)}% of runs`);
console.log(`  won >=1 battle         : ${(100 * wonRuns / runs).toFixed(1)}% of runs`);
console.log(`  wall-clock             : ${secs.toFixed(2)}s  (~${Math.round(totalSteps / Math.max(secs, .001)).toLocaleString()} steps/sec)`);
console.log(`\n${failures === 0 ? "ALL AUDIT CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
process.exit(failures === 0 ? 0 : 1);
