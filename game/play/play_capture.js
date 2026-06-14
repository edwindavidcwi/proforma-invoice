// Headless QA harness: "plays" the Quiz Battle without a screen.
//
// It boots the ROM, then jumps straight into the real QuizPlayerAttack battle
// hook with a chosen badge count (=> grade), so the cross-bank question loader
// (QuizLoadQuestion) runs for real. It then reads the screen tile map -- the
// buffer the game draws visible text into -- and prints the question + answers,
// proving the question rendered correctly from its ROM bank.
//
// Usage:  node play_capture.js [path/to/pokered.gbc]
// Symbol addresses are read from pokered.sym next to the ROM, so it never needs
// hand-edited addresses.
const fs = require("fs"), path = require("path");
const Binjgb = require(path.join(__dirname, "vendor", "binjgb.js"));

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const SYM = ROM.replace(/\.gb[c]?$/, ".sym");
const TPF = 70224;

// ---- read symbol addresses (bank:addr name) ----
const sym = {};
for (const line of fs.readFileSync(SYM, "utf8").split("\n")) {
  const m = line.trim().match(/^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$/);
  if (m) sym[m[3]] = { bank: parseInt(m[1], 16), addr: parseInt(m[2], 16) };
}
const A = (n) => { if (!sym[n]) throw new Error("missing symbol " + n); return sym[n].addr; };
const QuizPlayerAttack = sym["QuizPlayerAttack"];
const hLoadedROMBank = A("hLoadedROMBank"), wObtainedBadges = A("wObtainedBadges");
const wTileMap = A("wTileMap"), wQuizDataBank = A("wQuizDataBank"), wQuizQStr = A("wQuizQStr");

function tile(b) {
  if (b === 0x7f || b === 0) return " ";
  if (b >= 0x80 && b <= 0x99) return String.fromCharCode(65 + b - 0x80);
  if (b >= 0xa0 && b <= 0xb9) return String.fromCharCode(97 + b - 0xa0);
  if (b >= 0xf6 && b <= 0xff) return String.fromCharCode(48 + b - 0xf6);
  return ({ 0x9c: ":", 0xb7: "x", 0xe3: "-", 0xe6: "?", 0xe7: "!", 0xe8: ".", 0xf3: "/" })[b] || ".";
}

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;
  // badges -> grade: grade = popcount(badges)/2 + 1.  These give grades 1..5.
  const cases = [["Grade 1", 0x00], ["Grade 2", 0x03], ["Grade 3", 0x0f], ["Grade 4", 0x3f], ["Grade 5", 0xff]];
  let failures = 0;
  for (const [label, badges] of cases) {
    const rp = module._malloc(size);
    module.HEAPU8.fill(0, rp, rp + size);
    module.HEAPU8.set(rom, rp);
    const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
    const rd = (a) => module._emulator_read_mem(e, a);
    const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
    const ticks = () => module._emulator_get_ticks_f64(e);
    const run = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TPF); };

    run(400);                                   // boot
    wr(0x2000, QuizPlayerAttack.bank);          // map the quiz code bank
    wr(hLoadedROMBank, QuizPlayerAttack.bank);
    wr(wObtainedBadges, badges);
    module._emulator_set_PC(e, QuizPlayerAttack.addr);
    run(40);                                     // select -> far-copy -> draw

    let q = ""; for (let i = 0; i < 20; i++) { const b = rd(wQuizQStr + i); if (b === 0x50) break; q += tile(b); }
    const row = (r) => { let s = ""; for (let c = 1; c < 19; c++) s += tile(rd(wTileMap + r * 20 + c)); return s.trim(); };
    const answers = [row(9), row(11), row(13)].filter((s) => s);
    const ok = q.length > 1 && answers.length >= 2 && !(q + answers.join("")).includes("~");
    if (!ok) failures++;
    console.log(`${ok ? "PASS" : "FAIL"}  ${label} (bank ${rd(wQuizDataBank)}): "${q}"  ->  ${answers.join(" / ")}`);
    module._emulator_delete(e);
    module._free(rp);
  }
  console.log(failures === 0 ? "\nALL GRADES RENDERED CORRECTLY" : `\n${failures} GRADE(S) FAILED`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
