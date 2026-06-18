// Quiz Quest v3 -- AUDIT HARNESS (headless). Plays the brain thousands of times
// with random + adversarial inputs and checks the things that matter for a kid:
// no crash, no soft-lock, quizzes are reachable, answer keys are exact, saves
// round-trip and corrupt saves never crash, runs are reproducible.
//   node audit/harness.mjs
import { QUESTIONS, newGame, step, availableInputs, saveGame, loadGame } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

let fails = 0; const t0 = Date.now();
const check = (n, c, d) => { console.log(`${c ? "PASS" : "FAIL"}  ${n}${d ? "  (" + d + ")" : ""}`); if (!c) fails++; };
function hrng(s) { s >>>= 0; return () => { s = (s + 0x9E3779B9) >>> 0; let t = Math.imul(s ^ (s >>> 16), 0x45D9F3B); t = Math.imul(t ^ (t >>> 15), 0x27D4EB2F); return ((t ^ (t >>> 15)) >>> 0) / 4294967296; }; }

// 1. the map pack is sane
check("map pack: start cell is walkable", PACK.walk[PACK.start[1]][PACK.start[0]] === 1);
let walkable = 0; for (const row of PACK.walk) for (const c of row) walkable += c;
check("map pack: there are walkable cells to explore", walkable > 10, walkable + " cells");
check("map pack: real art embedded (tileset + sprite)", PACK.tilesetURL.startsWith("data:image/png") && PACK.spriteURL.startsWith("data:image/png"));

// 2. question keys exact
let bad = 0; for (const q of QUESTIONS) if (!q.answers.includes(q.correct) || !q.hint) bad++;
check("every question has its correct answer + a hint", bad === 0, bad + " bad");

// 3. fuzz: thousands of random + adversarial playthroughs
function fuzz(label, policy, runs, stepsEach) {
  let crash = null, lock = null, sawQuiz = 0, sawWin = 0;
  for (let seed = 1; seed <= runs; seed++) {
    const r = hrng(seed * 2654435761 >>> 0);
    let st = newGame(PACK, seed);
    for (let i = 0; i < stepsEach; i++) {
      const ins = availableInputs(st, PACK);
      if (!ins.length) { lock = lock || { seed, i }; break; }
      try { step(st, PACK, policy(st, ins, r)); }
      catch (e) { crash = crash || { seed, i, msg: String(e && e.message || e) }; break; }
      if (st.mode === "quiz") sawQuiz = 1;
      if (st.quizzesWon > 0) sawWin = 1;
    }
  }
  check(`[${label}] no crash over ${runs} runs`, !crash, crash && `seed ${crash.seed}: ${crash.msg}`);
  check(`[${label}] no soft-lock over ${runs} runs`, !lock, lock && `seed ${lock.seed}`);
  return { sawQuiz, sawWin };
}
const pRandom = (s, ins, r) => ins[Math.floor(r() * ins.length)];
const pWrong = (s, ins, r) => (s.mode === "quiz")
  ? { type: "answer", index: (s.asked.correct + 1) % s.asked.options.length } : ins[Math.floor(r() * ins.length)];
const pRight = (s, ins, r) => (s.mode === "quiz") ? { type: "answer", index: s.asked.correct } : ins[Math.floor(r() * ins.length)];

console.log("\n-- fuzz playthroughs --");
const a = fuzz("random", pRandom, 3000, 1500);
fuzz("always-wrong (struggling kid)", pWrong, 1500, 1500);
const c = fuzz("always-right", pRight, 1500, 1500);
check("random walking reaches quiz encounters", a.sawQuiz === 1);
check("answering right wins quizzes", c.sawWin === 1);

// 4. the shuffled question's correct index really points at the right answer
let mm = 0, checked = 0;
for (let seed = 1; seed <= 400; seed++) {
  let st = newGame(PACK, seed); const r = hrng(seed);
  for (let i = 0; i < 800 && st.mode !== "quiz"; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r));
  if (st.mode === "quiz") { checked++; if (st.asked.options[st.asked.correct] !== st.asked.correctText) mm++; }
}
check(`shuffled question's correct index is right (${checked} sampled)`, mm === 0, mm + " mismatches");

// 5. save / load
let smm = 0;
for (let seed = 1; seed <= 400; seed++) {
  let st = newGame(PACK, seed); const r = hrng(seed + 5);
  for (let i = 0; i < 60; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r));
  if (JSON.stringify(loadGame(saveGame(st), PACK, seed)) !== JSON.stringify(st)) smm++;
}
check("save -> load round-trips exactly (400 states)", smm === 0, smm + " mismatches");
let safe = true;
for (const b of ["", "{", "null", "not json", '{"v":3,"sum":0,"data":"x"}']) { try { if (typeof loadGame(b, PACK, 1).cx !== "number") safe = false; } catch (e) { safe = false; } }
check("a corrupt save loads safely (fresh game, never crashes)", safe);

// 6. reproducible
function run(seed) { let st = newGame(PACK, seed); const r = hrng(seed); for (let i = 0; i < 800; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r)); return JSON.stringify(st); }
let diff = 0; for (let seed = 1; seed <= 200; seed++) if (run(seed) !== run(seed)) diff++;
check("same seeds -> identical outcome (reproducible)", diff === 0, diff + " non-deterministic");

console.log(`\n(${((Date.now() - t0) / 1000).toFixed(2)}s)  ${fails === 0 ? "ALL v3 AUDIT CHECKS PASSED" : fails + " CHECK(S) FAILED"}`);
process.exit(fails === 0 ? 0 : 1);
