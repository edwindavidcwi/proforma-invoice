// Headless verification of the hidden-audio-Game-Boy music engine (MUSIC_JS).
// The runtime can't be heard in Node, but its core mechanism CAN be checked:
//
//   1. The same "inject a PlayMusic stub + let V-blank advance it" trick the
//      runtime uses really makes a second binjgb instance play a chosen song.
//   2. Each context song (id, bank) produces REAL, NON-SILENT audio, and
//      different songs produce DIFFERENT audio (so the per-context switching is
//      meaningful, not all-the-same).
//   3. Every music id the runtime maps to lives in the 0xBA..0xFC music band the
//      runtime filters on when reading wChannelSoundIDs (so SFX/cries, which are
//      below 0xBA, are correctly ignored).
//
// Run:  node test_music_engine.js [path/to/pokered.gbc]
const fs = require("fs"), path = require("path");
const Binjgb = require("./vendor/binjgb.js");

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const RATE = 22050, TPF = 70224, CPU = 4194304, FRAMES = 4096;
const EV_AUDIO = 2, EV_TICKS = 4;
const STUB = 0xc6e8, PLAYMUSIC = 0x23a1, MUS_LO = 0xba, MUS_HI = 0xfc;

// The exact (id, bank) pairs the runtime plays per context (from pokered.sym:
// id = (header_addr - 0x4000) / 3; banks Audio1=0x02, Audio2=0x08, Audio3=0x1f).
const SONGS = {
  town:    { id: 0xba, bank: 0x02 }, route:   { id: 0xeb, bank: 0x02 },
  centre:  { id: 0xbd, bank: 0x02 }, cave:    { id: 0xe0, bank: 0x1f },
  wild:    { id: 0xf0, bank: 0x08 }, trainer: { id: 0xed, bank: 0x08 },
  boss:    { id: 0xea, bank: 0x08 }, rival:   { id: 0xf3, bank: 0x08 },
  victory: { id: 0xf6, bank: 0x08 }, title:   { id: 0xc3, bank: 0x1f },
};

let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
};

// Boot a fresh instance, inject the song, and record ~1.2s of mono audio + a
// cheap fingerprint (std dev + coarse spectrum-ish buckets) to compare songs.
async function capture(wasm, rom, size, id, bank) {
  const m = await Binjgb({ wasmBinary: wasm });
  const p = m._malloc(size); m.HEAPU8.fill(0, p, p + size); m.HEAPU8.set(rom, p);
  const e = m._emulator_new_simple(p, size, RATE, FRAMES, 0);
  if (e === 0) throw new Error("emulator_new_simple failed");
  const aptr = m._get_audio_buffer_ptr(e);

  let tgt = m._emulator_get_ticks_f64(e) + 400 * TPF;     // run to title
  while (true) { if (m._emulator_run_until_f64(e, tgt) & EV_TICKS) break; }

  const stub = [0x3e, id, 0x0e, bank, 0xcd, PLAYMUSIC & 0xff, (PLAYMUSIC >> 8) & 0xff, 0x18, 0xfe];
  for (let i = 0; i < stub.length; i++) m._emulator_write_mem(e, STUB + i, stub[i]);
  m._emulator_set_PC(e, STUB);

  const want = Math.ceil(1.2 * RATE);
  const out = new Float32Array(want);
  let got = 0;
  tgt = m._emulator_get_ticks_f64(e) + Math.ceil(2.0 * CPU);
  while (got < want) {
    const ev = m._emulator_run_until_f64(e, tgt);
    if (ev & EV_AUDIO) {
      for (let i = 0; i < FRAMES && got < want; i++) {
        const l = m.HEAPU8[aptr + 2 * i], r = m.HEAPU8[aptr + 2 * i + 1];
        out[got++] = ((l + r) / 2 - 128) / 128;
      }
    }
    if (ev & EV_TICKS) break;
  }
  return out.subarray(0, got);
}

// Coarse fingerprint: mean abs level over 8 equal time-slices.
function fingerprint(f) {
  const fp = new Array(8).fill(0), n = (f.length / 8) | 0;
  for (let s = 0; s < 8; s++) {
    let a = 0; for (let i = 0; i < n; i++) a += Math.abs(f[s * n + i]);
    fp[s] = a / n;
  }
  return fp;
}
function fpDist(a, b) { let d = 0; for (let i = 0; i < 8; i++) d += Math.abs(a[i] - b[i]); return d; }
function std(f) { let m = 0; for (let i = 0; i < f.length; i++) m += f[i]; m /= f.length;
  let v = 0; for (let i = 0; i < f.length; i++) { const d = f[i] - m; v += d * d; } return Math.sqrt(v / f.length); }

(async () => {
  const wasm = fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm"));
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;

  console.log("-- every context song id is in the 0xBA..0xFC music band --");
  for (const [name, s] of Object.entries(SONGS)) {
    check(`${name} id 0x${s.id.toString(16)} in music band`, s.id >= MUS_LO && s.id <= MUS_HI);
  }

  console.log("\n-- each song injects + produces real audio --");
  const fps = {};
  for (const [name, s] of Object.entries(SONGS)) {
    const audio = await capture(wasm, rom, size, s.id, s.bank);
    const sd = std(audio);
    check(`${name}: hidden GB plays real (non-silent) audio`, sd > 0.02, "std=" + sd.toFixed(3));
    fps[name] = fingerprint(audio);
  }

  console.log("\n-- different contexts sound different (not all the same track) --");
  const pairs = [["town", "wild"], ["town", "cave"], ["wild", "boss"], ["route", "centre"], ["title", "town"]];
  for (const [a, b] of pairs) {
    const d = fpDist(fps[a], fps[b]);
    check(`${a} differs from ${b}`, d > 0.01, "dist=" + d.toFixed(3));
  }

  console.log(`\n${failures === 0 ? "ALL MUSIC-ENGINE CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
