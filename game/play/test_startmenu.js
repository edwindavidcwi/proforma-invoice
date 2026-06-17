// Headless guard for the START MENU item count (DrawStartMenu in
// engine/menus/draw_start_menu.asm + the wrap bounds in home/start_menu.asm).
//
// The start menu has the stock 7 items with the Pokedex (POKEDEX..OPTION,EXIT)
// and 6 without. wMaxMenuItem is the HIGHEST selectable index, so it must be
// itemCount-1 (6 with Pokedex, 5 without). (An earlier build added a "STUDY"
// item and botched the count, which let the cursor land on a phantom blank row
// and made EXIT unreachable; STUDY was removed and the menu restored to stock.)
// This test calls the real DrawStartMenu and asserts the index is exactly right,
// both with and without the Pokedex, so the count can never drift again.
//
// Run:  node test_startmenu.js [path/to/pokered.gbc]
const fs = require("fs"), path = require("path");
const Binjgb = require("./vendor/binjgb.js");

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const TICKS_PER_FRAME = 70224;

const SYM = ROM.replace(/\.gb[c]?$/, ".sym");
const _sym = {}, _bank = {};
for (const line of fs.readFileSync(SYM, "utf8").split("\n")) {
  const m = line.trim().match(/^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$/);
  if (m) { _sym[m[3]] = parseInt(m[2], 16); _bank[m[3]] = parseInt(m[1], 16); }
}
const S = (n) => { if (_sym[n] === undefined) throw new Error("missing symbol " + n); return _sym[n]; };
const BANK = (n) => { if (_bank[n] === undefined) throw new Error("missing symbol " + n); return _bank[n]; };

const DrawStartMenu = S("DrawStartMenu"), drawBank = BANK("DrawStartMenu");
const wMaxMenuItem = S("wMaxMenuItem"), hLoadedROMBank = S("hLoadedROMBank");
const wEventFlags = S("wEventFlags");
const POKEDEX_BYTE = wEventFlags + (37 >> 3);   // EVENT_GOT_POKEDEX = index 37
const POKEDEX_MASK = 1 << (37 & 7);             // -> byte wEventFlags+4, bit 0x20

let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
};

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;
  const romPtr = module._malloc(size);
  module.HEAPU8.fill(0, romPtr, romPtr + size);
  module.HEAPU8.set(rom, romPtr);
  const e = module._emulator_new_simple(romPtr, size, 44100, 4096, 0);
  if (e === 0) throw new Error("emulator_new_simple failed (invalid ROM)");

  const rd = (a) => module._emulator_read_mem(e, a);
  const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
  const ticks = () => module._emulator_get_ticks_f64(e);
  const runFrames = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TICKS_PER_FRAME); };

  runFrames(150); // boot to the intro (initialized, no active menu)

  const SPIN = 0xc6e8; // a scratch WRAM byte we can park the CPU on after the call
  const drawAndReadMax = (hasPokedex) => {
    // set/clear the Pokedex event the menu branches on
    const b = rd(POKEDEX_BYTE);
    wr(POKEDEX_BYTE, hasPokedex ? (b | POKEDEX_MASK) : (b & ~POKEDEX_MASK));
    wr(0x2000, drawBank); wr(hLoadedROMBank, drawBank); // map the menu ROM bank
    wr(SPIN, 0x18); wr(SPIN + 1, 0xfe);                 // jr -2 (idle here after ret)
    const sp = module._emulator_get_SP(e);
    wr(sp, SPIN & 0xff); wr(sp + 1, (SPIN >> 8) & 0xff); // return address -> spin
    wr(wMaxMenuItem, 0xee);                              // poison so we know it's written
    module._emulator_set_PC(e, DrawStartMenu);
    module._emulator_run_until_f64(e, ticks() + 60000);  // run the routine, then idle
    return rd(wMaxMenuItem);
  };

  drawAndReadMax(true); // warm-up: settle VRAM/menu state before measuring

  // With the Pokedex: 7 items (POKEDEX..OPTION,EXIT) -> max index 6.
  const withDex = drawAndReadMax(true);
  check("with Pokedex: wMaxMenuItem == 6 (7 items)", withDex === 6, "got " + withDex);

  // Without the Pokedex: 6 items -> max index 5.
  const noDex = drawAndReadMax(false);
  check("without Pokedex: wMaxMenuItem == 5 (6 items)", noDex === 5, "got " + noDex);

  check("the two cases differ by exactly one item", withDex - noDex === 1, `withDex=${withDex} noDex=${noDex}`);

  console.log(`\n${failures === 0 ? "ALL START-MENU CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
