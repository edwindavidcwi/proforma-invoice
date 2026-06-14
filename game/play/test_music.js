// Headless verification for the context-aware background music (MUSIC_JS in
// build_player.py). The track-selection logic is pure JS that reads the live
// game state out of emulator RAM, so we:
//
//   1. Boot the REAL pokered.gbc in binjgb.
//   2. Stub just enough of a browser (window, AudioContext, performance) and
//      point window.__emulator at the running emulator, then eval MUSIC_JS.
//   3. Write the documented WRAM state bytes (battle flag, trainer class, gym
//      no., tileset, map) to drive each situation and assert window.__music.pick
//      selects the right theme: region (town/route/cave/centre), generic battle
//      (wild/trainer), and person themes (rival/boss) overriding battle.
//
// Run:  node test_music.js [path/to/pokered.gbc]
const fs = require("fs"), path = require("path"), vm = require("vm");
const Binjgb = require("./vendor/binjgb.js");

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const TICKS_PER_FRAME = 70224;

// Stock pokered WRAM addresses (must match MUSIC_JS / pokered.sym).
const A = { inBattle: 0xd057, trClass: 0xd031, curOpp: 0xd059, gym: 0xd05c,
            result: 0xcf0b, map: 0xd35e, tileset: 0xd367 };
const OPP = 200; // OPP_ID_OFFSET

let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
};

// Minimal MUSIC_JS extractor: pull the r""" ... """ block from build_player.py.
function loadMusicJs() {
  const py = fs.readFileSync(path.join(__dirname, "build_player.py"), "utf8");
  const m = py.match(/MUSIC_JS = r"""([\s\S]*?)"""/);
  if (!m) throw new Error("could not find MUSIC_JS in build_player.py");
  return m[1];
}

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;
  const romPtr = module._malloc(size);
  module.HEAPU8.fill(0, romPtr, romPtr + size);
  module.HEAPU8.set(rom, romPtr);
  const e = module._emulator_new_simple(romPtr, size, 44100, 4096, 0);
  if (e === 0) throw new Error("emulator_new_simple failed (invalid ROM)");

  const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
  const ticks = () => module._emulator_get_ticks_f64(e);
  // Run a little so RAM is real (not all zero) before we override specific bytes.
  for (let i = 0; i < 120; i++) module._emulator_run_until_f64(e, ticks() + TICKS_PER_FRAME);

  // --- Browser stub + eval MUSIC_JS ---
  const listeners = {};
  const sandbox = {
    setInterval: () => 0, clearInterval: () => {}, setTimeout: () => 0,
    performance: { now: () => 0 },
    console,
    AudioContext: function () {
      return { state: "running", currentTime: 0, destination: {}, resume() {},
               createGain: () => ({ gain: { value: 0, setValueAtTime() {}, cancelScheduledValues() {},
                 linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} },
                 connect() {} }),
               createOscillator: () => ({ frequency: { value: 0 }, type: "", connect() {}, start() {}, stop() {} }) };
    },
  };
  sandbox.window = {
    AudioContext: sandbox.AudioContext,
    __emulator: { module, e },
    __soundOn: false, // don't auto-start the scheduler during the test
    addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
  };
  vm.createContext(sandbox);
  vm.runInContext(loadMusicJs(), sandbox);

  const music = sandbox.window.__music;
  if (!music) throw new Error("MUSIC_JS did not expose window.__music");

  // readState must read the live emulator memory through window.__emulator.
  const pickFor = (state) => {
    wr(A.inBattle, state.inBattle || 0);
    wr(A.trClass, state.trClass || 0);
    wr(A.curOpp, state.curOpp || 0);
    wr(A.gym, state.gym || 0);
    wr(A.result, state.result || 0);
    wr(A.map, state.map || 0);
    wr(A.tileset, state.tileset || 0);
    const s = music.read();
    return music.pick(s);
  };

  console.log("-- region themes (overworld, not in battle) --");
  check("Pallet Town (overworld tileset, map 0) -> town", pickFor({ tileset: 0, map: 0x00 }) === "town");
  check("Saffron City (overworld, map 0x0a) -> town", pickFor({ tileset: 0, map: 0x0a }) === "town");
  check("Route 1 (overworld tileset, map 0x0c) -> route", pickFor({ tileset: 0, map: 0x0c }) === "route");
  check("Cavern tileset (17) -> cave", pickFor({ tileset: 17, map: 0x3b }) === "cave");
  check("Cemetery tileset (15) -> cave", pickFor({ tileset: 15 }) === "cave");
  check("Underground tileset (11) -> cave", pickFor({ tileset: 11 }) === "cave");
  check("Poke Center tileset (6) -> centre", pickFor({ tileset: 6, map: 0x29 }) === "centre");
  check("Generic house tileset (8) -> centre", pickFor({ tileset: 8 }) === "centre");
  check("Forest tileset (3) -> route", pickFor({ tileset: 3, map: 0x33 }) === "route");
  check("Indigo Plateau (PLATEAU tileset 23, map 0x09) -> town", pickFor({ tileset: 23, map: 0x09 }) === "town");

  console.log("\n-- battle themes --");
  check("wild battle (inBattle 1, opp<200) -> wild",
        pickFor({ inBattle: 1, curOpp: 25, tileset: 0, map: 0x0c }) === "wild");
  check("generic trainer (YOUNGSTER 0x01) -> trainer",
        pickFor({ inBattle: 2, trClass: 0x01, curOpp: OPP + 0x01 }) === "trainer");
  check("trainer via curOpp only (no trClass) -> trainer",
        pickFor({ inBattle: 2, trClass: 0, curOpp: OPP + 0x02 }) === "trainer");

  console.log("\n-- person themes override generic battle --");
  check("RIVAL1 (0x19) -> rival", pickFor({ inBattle: 2, trClass: 0x19, curOpp: OPP + 0x19 }) === "rival");
  check("RIVAL2 (0x2a) -> rival", pickFor({ inBattle: 2, trClass: 0x2a, curOpp: OPP + 0x2a }) === "rival");
  check("RIVAL3/Champion (0x2b) -> rival", pickFor({ inBattle: 2, trClass: 0x2b, curOpp: OPP + 0x2b }) === "rival");
  check("BROCK (0x22) -> boss", pickFor({ inBattle: 2, trClass: 0x22, curOpp: OPP + 0x22 }) === "boss");
  check("SABRINA (0x28) -> boss", pickFor({ inBattle: 2, trClass: 0x28, curOpp: OPP + 0x28 }) === "boss");
  check("GIOVANNI (0x1d) -> boss", pickFor({ inBattle: 2, trClass: 0x1d, curOpp: OPP + 0x1d }) === "boss");
  check("LANCE / Elite Four (0x2f) -> boss", pickFor({ inBattle: 2, trClass: 0x2f, curOpp: OPP + 0x2f }) === "boss");
  check("gym-leader flag set, generic class -> boss",
        pickFor({ inBattle: 2, trClass: 0x01, curOpp: OPP + 0x01, gym: 1 }) === "boss");

  console.log(`\n${failures === 0 ? "ALL CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
