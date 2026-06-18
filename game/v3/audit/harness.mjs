// Quiz Quest v3 -- AUDIT HARNESS (headless). Plays the brain thousands of times
// with random + adversarial inputs through the FULL battle menu (fight/move/
// bag/party/run/catch) and checks: no crash, no soft-lock, battles only in
// grass, win/lose/catch all reachable, answer keys exact, saves safe, reproducible.
import { QUESTIONS, newGame, step, availableInputs, saveGame, loadGame } from "../engine/engine.js";
import { PACK } from "../pack/pallet.pack.js";

let fails = 0; const t0 = Date.now();
const check = (n, c, d) => { console.log(`${c ? "PASS" : "FAIL"}  ${n}${d ? "  (" + d + ")" : ""}`); if (!c) fails++; };
function hrng(s) { s >>>= 0; return () => { s = (s + 0x9E3779B9) >>> 0; let t = Math.imul(s ^ (s >>> 16), 0x45D9F3B); t = Math.imul(t ^ (t >>> 15), 0x27D4EB2F); return ((t ^ (t >>> 15)) >>> 0) / 4294967296; }; }
const phase = s => s.mode === "battle" ? s.battle.phase : "overworld";

check("start walkable & not grass", PACK.walk[PACK.start[1]][PACK.start[0]] === 1 && PACK.grass[PACK.start[1]][PACK.start[0]] === 0);
let g = 0; for (const r of PACK.grass) for (const c of r) g += c;
check("has grass to battle in", g > 10, g + " cells");
check("creatures + party + wild embedded", PACK.party.length > 0 && PACK.wild.length > 0 && Object.keys(PACK.creatures).length >= 2);
let bad = 0; for (const q of QUESTIONS) if (!q.answers.includes(q.correct) || !q.hint) bad++;
check("question keys exact", bad === 0, bad + " bad");

// policies that navigate the whole battle menu
function chooseAnswer(s, correct) { const a = s.battle.asked; return { type: "answer", index: correct ? a.correct : (a.correct + 1) % a.options.length }; }
function nav(s, ins, r, opts) {
  const ph = phase(s);
  if (ph === "overworld") return ins[Math.floor(r() * ins.length)];
  if (ph === "intro" || ph === "result") return { type: "confirm" };
  if (ph === "menu") return opts.menu || { type: "menu", choice: "fight" };
  if (ph === "moves") return { type: "move", index: 0 };
  if (ph === "bag") return opts.bag || { type: "back" };
  if (ph === "party") { const sw = ins.find(i => i.type === "switch"); return sw || ins[0]; }
  if (ph === "quiz") return chooseAnswer(s, opts.correct);
  if (ph === "catch") return chooseAnswer(s, opts.correct !== false);
  return ins[0];
}
const pRandom = (s, ins, r) => ins[Math.floor(r() * ins.length)];
const pRight = (s, ins, r) => nav(s, ins, r, { correct: true });
const pWrong = (s, ins, r) => nav(s, ins, r, { correct: false });
const pCatch = (s, ins, r) => nav(s, ins, r, { correct: true, menu: { type: "menu", choice: "bag" }, bag: { type: "item", which: "ball" } });

function fuzz(label, policy, runs, stepsEach) {
  let crash = null, lock = null, off = null, sawBattle = 0, won = 0, lost = 0, caught = 0;
  for (let seed = 1; seed <= runs; seed++) {
    const r = hrng(seed * 2654435761 >>> 0); let st = newGame(PACK, seed);
    for (let i = 0; i < stepsEach; i++) {
      const ins = availableInputs(st, PACK); if (!ins.length) { lock = lock || { seed, i, ph: phase(st) }; break; }
      const wasOver = st.mode === "overworld";
      try { step(st, PACK, policy(st, ins, r)); } catch (e) { crash = crash || { seed, i, msg: String(e && e.message || e) }; break; }
      if (wasOver && st.mode === "battle" && PACK.grass[st.cy][st.cx] !== 1) off = off || { seed, i };
      if (st.mode === "battle") { sawBattle = 1; const res = st.battle.result; if (res) { if (res.win) won = 1; if (res.lose) lost = 1; if (res.caught) caught = 1; } }
    }
  }
  check(`[${label}] no crash`, !crash, crash && `seed ${crash.seed} (${crash.msg})`);
  check(`[${label}] no soft-lock`, !lock, lock && `seed ${lock.seed} phase ${lock.ph}`);
  check(`[${label}] battles only start in grass`, !off, off && `seed ${off.seed}`);
  return { sawBattle, won, lost, caught };
}

console.log("\n-- fuzz playthroughs (full battle menu) --");
const a = fuzz("random", pRandom, 3000, 1800);
const w = fuzz("always-right (fight)", pRight, 1500, 1800);
const l = fuzz("always-wrong (struggling)", pWrong, 1500, 1800);
const c = fuzz("catch (ball + right)", pCatch, 1500, 2000);
check("random walking reaches grass battles", a.sawBattle === 1);
check("answering right WINS battles", w.won === 1);
check("always-wrong LOSES gracefully (no crash/lock)", l.lost === 1);
check("Poke Ball + 5 correct CATCHES a creature", c.caught === 1);

// shuffled question correct index
let mm = 0, ck = 0;
for (let seed = 1; seed <= 600; seed++) { let st = newGame(PACK, seed); const r = hrng(seed);
  for (let i = 0; i < 1500 && phase(st) !== "quiz"; i++) step(st, PACK, pRight(st, availableInputs(st, PACK), r));
  if (phase(st) === "quiz") { ck++; if (st.battle.asked.options[st.battle.asked.correct] !== st.battle.asked.correctText) mm++; } }
check(`shuffled question correct index right (${ck} sampled)`, mm === 0, mm + " mismatches");

// save / load
let smm = 0;
for (let seed = 1; seed <= 400; seed++) { let st = newGame(PACK, seed); const r = hrng(seed + 5);
  for (let i = 0; i < 120; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r));
  if (JSON.stringify(loadGame(saveGame(st), PACK, seed)) !== JSON.stringify(st)) smm++; }
check("save -> load round-trips exactly", smm === 0, smm + " mismatches");
let safe = true; for (const b of ["", "{", "null", "x", '{"v":4,"sum":0,"data":"x"}']) { try { if (typeof loadGame(b, PACK, 1).cx !== "number") safe = false; } catch (e) { safe = false; } }
check("corrupt save loads safely", safe);

// reproducible
const run = seed => { let st = newGame(PACK, seed); const r = hrng(seed); for (let i = 0; i < 1000; i++) step(st, PACK, pRandom(st, availableInputs(st, PACK), r)); return JSON.stringify(st); };
let diff = 0; for (let seed = 1; seed <= 150; seed++) if (run(seed) !== run(seed)) diff++;
check("same seeds -> identical outcome", diff === 0, diff + " non-deterministic");

console.log(`\n(${((Date.now() - t0) / 1000).toFixed(2)}s)  ${fails === 0 ? "ALL v3 AUDIT CHECKS PASSED" : fails + " CHECK(S) FAILED"}`);
process.exit(fails === 0 ? 0 : 1);
