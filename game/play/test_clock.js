// Structural test for the drawn analog clock. We can't SEE it headlessly, but we
// can confirm the engine composes it correctly: when a clock question loads
// (wQuizClock = 1..12), the face numbers 12/3/6/9 are drawn, the hour hand "H"
// lands in the cell this hour maps to, the answers stack in the single right
// column, and the correct answer is "<hour>:00". Visual polish still needs eyes
// on a device, but this guarantees the wiring + hour->position mapping are right.
//
// Usage:  node test_clock.js [path/to/pokered.gbc]
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
const A = (n) => sym[n].addr;
const QPA = sym["QuizPlayerAttack"];
const hLoadedROMBank = A("hLoadedROMBank"), wObtainedBadges = A("wObtainedBadges");
const wTileMap = A("wTileMap"), wQuizClock = A("wQuizClock"), wQuizNumAnswers = A("wQuizNumAnswers");
const wQuizA0 = A("wQuizA0");

// Must match ClockHandTable in quiz.asm (row*20 + col of each hour's hand tip).
const HAND = [205, 206, 226, 246, 245, 264, 243, 242, 222, 202, 203, 184];
const C = { "1": 0xf7, "2": 0xf8, "3": 0xf9, "6": 0xfc, "9": 0xff, "o": 0xae, "M": 0x8c, "H": 0x87, " ": 0x7f };
function dec(b) {
  if (b === 0x7f || b === 0) return " ";
  if (b >= 0x80 && b <= 0x99) return String.fromCharCode(65 + b - 0x80);
  if (b >= 0xa0 && b <= 0xb9) return String.fromCharCode(97 + b - 0xa0);
  if (b >= 0xf6 && b <= 0xff) return String.fromCharCode(48 + b - 0xf6);
  return ({ 0x9c: ":", 0xe6: "?", 0xe7: "!", 0xe8: "." })[b] || "~";
}

let failures = 0;
const fail = (m) => { console.log("FAIL  " + m); failures++; };

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;
  const seen = {};

  for (let t = 0; t < 200 && Object.keys(seen).length < 6; t++) {
    const rp = module._malloc(size);
    module.HEAPU8.fill(0, rp, rp + size);
    module.HEAPU8.set(rom, rp);
    const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
    const rd = (a) => module._emulator_read_mem(e, a);
    const ticks = () => module._emulator_get_ticks_f64(e);
    const run = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TPF); };
    run(380 + (t % 60));
    module._emulator_write_mem(e, wObtainedBadges, 0xff);   // Grade 5: most clock questions
    module._emulator_write_mem(e, 0x2000, QPA.bank);
    module._emulator_write_mem(e, hLoadedROMBank, QPA.bank);
    module._emulator_set_PC(e, QPA.addr);
    run(50);

    const hour = rd(wQuizClock);
    const n = rd(wQuizNumAnswers);
    if (hour >= 1 && hour <= 12 && n >= 2 && n <= 6 && !seen[hour]) {
      seen[hour] = true;
      const tm = (off) => rd(wTileMap + off);
      // face numbers present
      if (tm(164) !== C["1"] || tm(165) !== C["2"]) fail(`hour ${hour}: "12" not at top`);
      if (tm(227) !== C["3"]) fail(`hour ${hour}: "3" missing`);
      if (tm(284) !== C["6"]) fail(`hour ${hour}: "6" missing`);
      if (tm(221) !== C["9"]) fail(`hour ${hour}: "9" missing`);
      // hour hand in the mapped cell
      if (tm(HAND[hour - 1]) !== C["H"]) fail(`hour ${hour}: hand not at expected cell ${HAND[hour - 1]}`);
      // answers stacked in the right column (col 11, row 8 = offset 171)
      if (tm(8 * 20 + 11) === C[" "]) fail(`hour ${hour}: no answer in right column`);
      // correct answer text = "<hour>:00"
      let ans = ""; for (let i = 0; i < 8; i++) { const b = rd(wQuizA0 + i); if (b === 0x50) break; ans += dec(b); }
      if (ans !== hour + ":00") fail(`hour ${hour}: correct answer is "${ans}", expected "${hour}:00"`);
    }
    module._emulator_delete(e); module._free(rp);
  }

  const hours = Object.keys(seen).map(Number).sort((a, b) => a - b);
  console.log(`clock questions exercised for hours: ${hours.join(", ")}`);
  if (hours.length < 3) fail(`only ${hours.length} distinct clock hours seen (need >= 3)`);
  console.log(`\n${failures === 0 ? "ALL CLOCK CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
