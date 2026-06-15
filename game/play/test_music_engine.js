// Headless verification of the hidden-audio-Game-Boy music engine (MUSIC_JS).
// The runtime can't be heard in Node, but its core mechanism CAN be checked:
//
//   1. The "install a polling stub once, then change songs via a RAM mailbox"
//      trick really makes a second binjgb instance play a chosen song.
//   2. Each context song (id, bank) produces REAL, NON-SILENT audio, and
//      different songs produce DIFFERENT audio.
//   3. REGRESSION: switching songs many times across all three audio banks in
//      ONE running instance keeps producing audio (the old code forced the PC on
//      every switch, which corrupted the stack and silenced everything after a
//      few changes -- "no battle music, missing in many areas").
//   4. Every music id the runtime maps lives in the 0xBA..0xFC music band it
//      filters on when reading wChannelSoundIDs.
//
// Run:  node test_music_engine.js [path/to/pokered.gbc]
const fs = require("fs"), path = require("path");
const Binjgb = require("./vendor/binjgb.js");

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const RATE = 22050, TPF = 70224, CPU = 4194304, FRAMES = 4096;
const EV_AUDIO = 2, EV_TICKS = 4;
const STUB = 0xc6e8, PLAYMUSIC = 0x23a1, MUS_LO = 0xba, MUS_HI = 0xfc;
const FLAG = 0xc700, IDV = 0xc701, BANKV = 0xc702;

const SONGS = {
  town:    { id: 0xba, bank: 0x02 }, route:   { id: 0xeb, bank: 0x02 },
  centre:  { id: 0xbd, bank: 0x02 }, cave:    { id: 0xe0, bank: 0x1f },
  wild:    { id: 0xf0, bank: 0x08 }, trainer: { id: 0xed, bank: 0x08 },
  boss:    { id: 0xea, bank: 0x08 }, rival:   { id: 0xf3, bank: 0x08 },
  victory: { id: 0xf6, bank: 0x08 }, title:   { id: 0xdc, bank: 0x1f },
};

let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
};
const std = (f) => { let m = 0; for (const x of f) m += x; m /= f.length;
  let v = 0; for (const x of f) { const d = x - m; v += d * d; } return Math.sqrt(v / f.length); };
const fingerprint = (f) => { const fp = new Array(8).fill(0), n = (f.length / 8) | 0;
  for (let s = 0; s < 8; s++) { let a = 0; for (let i = 0; i < n; i++) a += Math.abs(f[s * n + i]); fp[s] = a / n; } return fp; };
const fpDist = (a, b) => { let d = 0; for (let i = 0; i < 8; i++) d += Math.abs(a[i] - b[i]); return d; };

// One running instance whose music can be switched via the RAM mailbox -- exactly
// like the runtime: install the polling stub once (single set_PC), then `play`.
async function makeInstance(wasm, rom, size) {
  const m = await Binjgb({ wasmBinary: wasm });
  const p = m._malloc(size); m.HEAPU8.fill(0, p, p + size); m.HEAPU8.set(rom, p);
  const e = m._emulator_new_simple(p, size, RATE, FRAMES, 0);
  if (e === 0) throw new Error("emulator_new_simple failed");
  const aptr = m._get_audio_buffer_ptr(e);
  const wr = (a, v) => m._emulator_write_mem(e, a, v & 0xff);

  let tgt = m._emulator_get_ticks_f64(e) + 400 * TPF;          // run to title
  while (true) { if (m._emulator_run_until_f64(e, tgt) & EV_TICKS) break; }

  const code = [0xfa, FLAG & 0xff, FLAG >> 8, 0xa7, 0x28, 0xfa, 0xaf,
                0xea, FLAG & 0xff, FLAG >> 8, 0xfa, BANKV & 0xff, BANKV >> 8, 0x4f,
                0xfa, IDV & 0xff, IDV >> 8, 0xcd, PLAYMUSIC & 0xff, PLAYMUSIC >> 8, 0x18, 0xea];
  for (let i = 0; i < code.length; i++) wr(STUB + i, code[i]);
  wr(FLAG, 0); m._emulator_set_PC(e, STUB);

  return {
    play: (id, bank) => { wr(IDV, id); wr(BANKV, bank); wr(FLAG, 1); },
    capture: (sec) => {
      const want = Math.ceil(sec * RATE), out = new Float32Array(want);
      let got = 0; const t = m._emulator_get_ticks_f64(e) + Math.ceil((sec + 4) * CPU);
      while (got < want) {
        const ev = m._emulator_run_until_f64(e, t);
        if (ev & EV_AUDIO) for (let i = 0; i < FRAMES && got < want; i++) {
          out[got++] = ((m.HEAPU8[aptr + 2 * i] + m.HEAPU8[aptr + 2 * i + 1]) / 2 - 128) / 128;
        }
        if (ev & EV_TICKS) break;
      }
      return out.subarray(0, got);
    },
  };
}

(async () => {
  const wasm = fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm"));
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;

  console.log("-- every context song id is in the 0xBA..0xFC music band --");
  for (const [name, s] of Object.entries(SONGS))
    check(`${name} id 0x${s.id.toString(16)} in music band`, s.id >= MUS_LO && s.id <= MUS_HI);

  console.log("\n-- each song plays real audio; different contexts differ --");
  const inst = await makeInstance(wasm, rom, size);
  const fps = {};
  for (const [name, s] of Object.entries(SONGS)) {
    inst.play(s.id, s.bank); inst.capture(0.4);          // let the switch settle
    const audio = inst.capture(0.8), sd = std(audio);
    check(`${name}: real (non-silent) audio`, sd > 0.02, "std=" + sd.toFixed(3));
    fps[name] = fingerprint(audio);
  }
  for (const [a, b] of [["town", "wild"], ["town", "cave"], ["wild", "boss"], ["route", "centre"], ["title", "town"]])
    check(`${a} differs from ${b}`, fpDist(fps[a], fps[b]) > 0.01, "dist=" + fpDist(fps[a], fps[b]).toFixed(3));

  console.log("\n-- REGRESSION: many switches across banks stay audible --");
  const order = ["town", "wild", "town", "boss", "cave", "title", "wild", "centre", "rival", "route"];
  let allAudible = true, worst = 1;
  for (const name of order) {
    const s = SONGS[name];
    inst.play(s.id, s.bank); inst.capture(0.3);
    const sd = std(inst.capture(0.5));
    if (sd <= 0.02) allAudible = false;
    worst = Math.min(worst, sd);
  }
  check("all " + order.length + " consecutive switches still produce audio", allAudible, "worst std=" + worst.toFixed(3));

  console.log(`\n${failures === 0 ? "ALL MUSIC-ENGINE CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
