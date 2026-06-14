// Outcome-logic audit (patch-based, deterministic).
//
// The joypad can't be driven in the headless hijack (the CPU parks in the VBlank
// vector), so instead we neutralise the two routines that WAIT for input by
// patching them to `ret` in the emulator's ROM copy -- HandleMenuInput (the menu
// wait) and PrintText (the result/hint text wait) -- and pin Random to a constant
// so we control the answer:
//   Random==0 -> question index 0, rotation 0 -> correct answer in slot 0, and
//               the menu cursor is 0 (QuizDrawScreen resets it) => CORRECT.
//   Random==1 -> rotation 1 -> correct answer in slot 2, cursor 0 => WRONG.
// Then the real QuizPlayerAttack / QuizEnemyDefense outcome code runs to the end
// and we read its effects (wMoveMissed, wDamage).
//
// Usage: node audit_outcome.js [rom]
const fs = require("fs"), path = require("path");
const Binjgb = require(path.join(__dirname, "vendor", "binjgb.js"));
const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const SYM = ROM.replace(/\.gb[c]?$/, ".sym");
const TPF = 70224;

const sym = {};
for (const line of fs.readFileSync(SYM, "utf8").split("\n")) {
  const m = line.trim().match(/^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$/);
  if (m) sym[m[3]] = { bank: parseInt(m[1], 16), addr: parseInt(m[2], 16) };
}
const A = n => sym[n].addr;
const QPA = sym.QuizPlayerAttack, QED = sym.QuizEnemyDefense;
const HMI = A("HandleMenuInput"), PT = A("PrintText"), RND = A("Random");

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM); const size = (rom.length + 0x7fff) & ~0x7fff;
  let fails = 0;
  const check = (n, c, d) => { console.log(`${c ? "PASS" : "FAIL"}  ${n}${d ? "  (" + d + ")" : ""}`); if (!c) fails++; };

  // run a hook with Random pinned to `rndConst`; `setup(wr)` seeds battle vars.
  function runHook(hook, rndConst, setup) {
    const rp = module._malloc(size); module.HEAPU8.fill(0, rp, rp + size); module.HEAPU8.set(rom, rp);
    const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
    const rd = a => module._emulator_read_mem(e, a), wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
    const run = n => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, module._emulator_get_ticks_f64(e) + TPF); };
    run(440);
    // patch ROM in emulator RAM (home bank: file offset == address)
    module.HEAPU8[rp + HMI] = 0xc9;                                  // HandleMenuInput -> ret
    module.HEAPU8[rp + PT]  = 0xc9;                                  // PrintText -> ret
    module.HEAPU8[rp + RND] = 0x3e; module.HEAPU8[rp + RND + 1] = rndConst; module.HEAPU8[rp + RND + 2] = 0xc9; // Random -> ld a,N : ret
    if (setup) setup(wr);
    wr(0x2000, hook.bank); wr(A("hLoadedROMBank"), hook.bank); wr(A("wObtainedBadges"), 0);
    module._emulator_set_PC(e, hook.addr);
    run(220);
    const out = { missed: rd(A("wMoveMissed")), dmg: (rd(A("wDamage")) << 8) | rd(A("wDamage") + 1),
                  cs: rd(A("wQuizCorrectIndex")) };
    module._emulator_delete(e); module._free(rp);
    return out;
  }

  // 1) correct attack -> HIT.  Seed wMoveMissed with a sentinel so we know it ran.
  let o = runHook(QPA, 0, wr => wr(A("wMoveMissed"), 0xff));
  check("correct attack -> HIT (wMoveMissed=0)", o.missed === 0 && o.cs === 0, `wMoveMissed=${o.missed}, correctSlot=${o.cs}`);

  // 2) wrong attack -> MISS
  o = runHook(QPA, 1, wr => wr(A("wMoveMissed"), 0xff));
  check("wrong attack -> MISS (wMoveMissed=1)", o.missed === 1 && o.cs === 2, `wMoveMissed=${o.missed}, correctSlot=${o.cs}`);

  // 3) correct defence -> damage HALVED (100 -> 50)
  o = runHook(QED, 0, wr => { wr(A("wEnemyMovePower"), 40); wr(A("wDamage"), 0); wr(A("wDamage") + 1, 100); });
  check("correct defence -> HALF damage (100->50)", o.dmg === 50, `wDamage=${o.dmg}`);

  // 4) wrong defence -> NORMAL damage (stays 100; old code would DOUBLE to 200)
  o = runHook(QED, 1, wr => { wr(A("wEnemyMovePower"), 40); wr(A("wDamage"), 0); wr(A("wDamage") + 1, 100); });
  check("wrong defence -> NORMAL damage (100, not doubled)", o.dmg === 100, `wDamage=${o.dmg}`);

  console.log(`\n${fails === 0 ? "ALL OUTCOME CHECKS PASSED" : fails + " OUTCOME CHECK(S) FAILED"}`);
  process.exit(fails === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
