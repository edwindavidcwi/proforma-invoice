// Quiz Quest v3 -- AUDIT HARNESS (headless). Plays the brain thousands of times
// with random + adversarial inputs and checks: no crash, no soft-lock, battles
// happen ONLY in tall grass, quizzes reachable, answer keys exact, saves safe,
// reproducible.   node audit/harness.mjs
import { QUESTIONS, newGame, step, availableInputs, saveGame, loadGame } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

let fails = 0; const t0 = Date.now();
const check = (n, c, d) => { console.log(`${c ? "PASS" : "FAIL"}  ${n}${d ? "  (" + d + ")" : ""}`); if (!c) fails++; };
function hrng(s) { s >>>= 0; return () => { s = (s + 0x9E3779B9) >>> 0; let t = Math.imul(s ^ (s >>> 16), 0x45D9F3B); t = Math.imul(t ^ (t >>> 15), 0x27D4EB2F); return ((t ^ (t >>> 15)) >>> 0) / 4294967296; }; }
const inQuiz = s => s.mode === "battle" && s.battle.phase === "quiz";

check("map pack: start cell walkable & NOT grass", PACK.walk[PACK.start[1]][PACK.start[0]] === 1 && PACK.grass[PACK.start[1]][PACK.start[0]] === 0);
let g = 0; for (const r of PACK.grass) for (const c of r) g += c;
check("map pack: has tall-grass cells to battle in", g > 10, g + " grass cells");
check("map pack: real art + creatures embedded", PACK.tilesetURL.startsWith("data:image/png") && PACK.creatureNames.length > 0);

let bad = 0; for (const q of QUESTIONS) if (!q.answers.includes(q.correct) || !q.hint) bad++;
check("every question has its correct answer + a hint", bad === 0, bad + " bad");

// fuzz, and verify every encounter starts ON a grass cell
function fuzz(label, policy, runs, stepsEach) {
  let crash = null, lock = null, sawBattle = 0, sawWin = 0, offGrass = null;
  for (let seed = 1; seed <= runs; seed++) {
    const r = hrng(seed * 2654435761 >>> 0); let st = newGame(PACK, seed);
    for (let i = 0; i < stepsEach; i++) {
      const ins = availableInputs(st, PACK); if (!ins.length) { lock = lock || { seed, i }; break; }
      const wasOver = st.mode === "overworld";
      try { step(st, PACK, policy(st, ins, r)); }
      catch (e) { crash = crash || { seed, i, msg: String(e && e.message || e) }; break; }
      if (wasOver && st.mode === "battle" && PACK.grass[st.cy][st.cx] !== 1) offGrass = offGrass || { seed, i };
      if (st.mode === "battle") sawBattle = 1;
      if (st.battlesWon > 0) sawWin = 1;
    }
  }
  check(`[${label}] no crash over ${runs} runs`, !crash, crash && `seed ${crash.seed}: ${crash.msg}`);
  check(`[${label}] no soft-lock over ${runs} runs`, !lock, lock && `seed ${lock.seed}`);
  check(`[${label}] every battle started in grass (never plain walking)`, !offGrass, offGrass && `seed ${offGrass.seed}`);
  return { sawBattle, sawWin };
}
const pRandom = (s, ins, r) => ins[Math.floor(r() * ins.length)];
const pWrong = (s, ins, r) => inQuiz(s) ? { type: "answer", index: (s.battle.asked.correct + 1) % s.battle.asked.options.length } : ins[Math.floor(r() * ins.length)];
const pRight = (s, ins, r) => inQuiz(s) ? { type: "answer", index: s.battle.asked.correct } : (s.mode === "battle" ? { type: "confirm" } : ins[Math.floor(r() * ins.length)]);

console.log("\n-- fuzz playthroughs --");
const a = fuzz("random", pRandom, 3000, 1500);
fuzz("always-wrong (struggling kid)", pWrong, 1500, 1500);
const c = fuzz("always-right", pRight, 1500, 1500);
check("random walking reaches grass battles", a.sawBattle === 1);
check("answering right wins battles", c.sawWin === 1);

// shuffled question's correct index is right
let mm = 0, checked = 0;
for (let seed = 1; seed <= 600; seed++) {
  let st = newGame(PACK, seed); const r = hrng(seed);
  for (let i = 0; i < 1200 && !inQuiz(st); i++) { const ins = availableInputs(st, PACK); step(st, PACK, st.mode === "battle" ? { type: "confirm" } : pRandom(st, ins, r)); }
  if (inQuiz(st)) { checked++; if (st.battle.asked.options[st.battle.asked.correct] !== st.battle.asked.correctText) mm++; }
}
check(`shuffled question's correct index is right (${checked} sampled)`, mm === 0, mm + " mismatches");

// save / load
let smm = 0;
for (let seed = 1; seed <= 400; seed++) {
  let st = newGame(PACK, seed); const r = hrng(seed + 5);
  for (let i = 0; i < 80; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r));
  if (JSON.stringify(loadGame(saveGame(st), PACK, seed)) !== JSON.stringify(st)) smm++;
}
check("save -> load round-trips exactly", smm === 0, smm + " mismatches");
let safe = true;
for (const b of ["", "{", "null", "not json", '{"v":3,"sum":0,"data":"x"}']) { try { if (typeof loadGame(b, PACK, 1).cx !== "number") safe = false; } catch (e) { safe = false; } }
check("a corrupt save loads safely (fresh game, never crashes)", safe);

// reproducible
function run(seed) { let st = newGame(PACK, seed); const r = hrng(seed); for (let i = 0; i < 900; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r)); return JSON.stringify(st); }
let diff = 0; for (let seed = 1; seed <= 200; seed++) if (run(seed) !== run(seed)) diff++;
check("same seeds -> identical outcome (reproducible)", diff === 0, diff + " non-deterministic");

console.log(`\n(${((Date.now() - t0) / 1000).toFixed(2)}s)  ${fails === 0 ? "ALL v3 AUDIT CHECKS PASSED" : fails + " CHECK(S) FAILED"}`);
process.exit(fails === 0 ? 0 : 1);
