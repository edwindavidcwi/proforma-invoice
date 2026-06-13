/*
 * Offline player wrapper for the Pokemon Quiz ROM.
 *
 * Adapted from binjgb's docs/simple.js
 *   Copyright (C) 2020 Ben Smith - MIT license (see binjgb.LICENSE)
 *   Some code from GB-Studio, see LICENSE.gbstudio
 *
 * Changes vs. upstream simple.js:
 *   - The emulator WASM is provided inline (window.__WASM_B64__) so nothing
 *     is fetched over the network -- works fully offline from file://.
 *   - The ROM is provided inline (window.__ROM_B64__) by default, and can be
 *     replaced at runtime with the "Open ROM" file picker.
 *   - Added visible on-screen buttons (save/load state, fullscreen, open ROM)
 *     so it is usable on a phone with no keyboard.
 */
"use strict";

// User configurable.
const ENABLE_FAST_FORWARD = true;
const ENABLE_REWIND = true;
const ENABLE_PAUSE = true;
const ENABLE_SWITCH_PALETTES = true;
const OSGP_DEADZONE = 0.1;    // On screen gamepad deadzone range
const CGB_COLOR_CURVE = 2;    // 0: none, 1: Sameboy 2: Gambatte/Gameboy Online

const DEFAULT_PALETTE_IDX = 79;
const PALETTES = [
  0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13, 14, 15, 16,
  17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
  34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
  51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67,
  68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83,
];

const REWIND_FRAMES_PER_BASE_STATE = 45;
const REWIND_BUFFER_CAPACITY = 4 * 1024 * 1024;
const REWIND_FACTOR = 1.5;
const REWIND_UPDATE_MS = 16;

const AUDIO_FRAMES = 4096;
const AUDIO_LATENCY_SEC = 0.1;
const MAX_UPDATE_SEC = 5 / 60;

// Constants
const RESULT_OK = 0;
const RESULT_ERROR = 1;
const SCREEN_WIDTH = 160;
const SCREEN_HEIGHT = 144;
const CPU_TICKS_PER_SECOND = 4194304;
const EVENT_NEW_FRAME = 1;
const EVENT_AUDIO_BUFFER_FULL = 2;
const EVENT_UNTIL_TICKS = 4;

const $ = document.querySelector.bind(document);
let emulator = null;

const controllerEl = $('#controller');
const dpadEl = $('#controller_dpad');
const selectEl = $('#controller_select');
const startEl = $('#controller_start');
const bEl = $('#controller_b');
const aEl = $('#controller_a');

// --- Base64 -> Uint8Array (used for the inlined WASM and ROM) ---------------
function b64ToBytes(b64) {
  const bin = atob(b64);
  const len = bin.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

// Boot the emulator core with the inlined WASM binary (no network fetch).
const binjgbPromise = Binjgb({ wasmBinary: b64ToBytes(window.__WASM_B64__) });

// Per-ROM key for saved cartridge RAM so different ROMs don't clobber.
let extRamKey = 'extram';
let saveStateKey = 'saveState';
function setStorageKeysForRom(name) {
  const safe = (name || 'rom').replace(/[^A-Za-z0-9_.-]/g, '_');
  extRamKey = 'extram:' + safe;
  saveStateKey = 'saveState:' + safe;
}

class VM {
  constructor() {
    this.ticks = 0;
    this.extRamUpdated = false;
    this.paused_ = false;
    this.volume = 0.5;
    this.palIdx = DEFAULT_PALETTE_IDX;
    this.rewind = { minTicks: 0, maxTicks: 0 };
    setInterval(() => {
      if (this.extRamUpdated) {
        this.updateExtRam();
        this.extRamUpdated = false;
      }
    }, 1000);
  }

  get paused() { return this.paused_; }
  set paused(newPaused) {
    let oldPaused = this.paused_;
    this.paused_ = newPaused;
    if (!emulator) return;
    if (newPaused == oldPaused) return;
    if (newPaused) {
      emulator.pause();
      this.ticks = emulator.ticks;
      this.rewind.minTicks = emulator.rewind.oldestTicks;
      this.rewind.maxTicks = emulator.rewind.newestTicks;
    } else {
      emulator.resume();
    }
  }

  togglePause() { this.paused = !this.paused; }

  updateExtRam() {
    if (!emulator) return;
    const extram = emulator.getExtRam();
    try {
      localStorage.setItem(extRamKey, JSON.stringify(Array.from(extram)));
    } catch (e) { /* storage may be full or disabled; ignore */ }
  }
};

const vm = new VM();
window.__vm = vm; // exposed for the Sound on/off toggle (vm.volume)

// Load a ROM ArrayBuffer into the emulator and start it.
function startRom(module, romBuffer, romName) {
  setStorageKeysForRom(romName);
  let extRam = new Uint8Array(0);
  try {
    const saved = localStorage.getItem(extRamKey);
    if (saved) extRam = new Uint8Array(JSON.parse(saved));
  } catch (e) { /* ignore */ }
  Emulator.start(module, romBuffer, extRam);
  emulator.setBuiltinPalette(vm.palIdx);
  hideOverlay();
}

// Boot with the inlined ROM.
(async function go() {
  const module = await binjgbPromise;
  window.__binjgbModule = module;
  if (window.__ROM_B64__ && window.__ROM_B64__.length) {
    const romBuffer = b64ToBytes(window.__ROM_B64__).buffer;
    try {
      startRom(module, romBuffer, window.__ROM_NAME__ || 'pokered.gbc');
    } catch (e) {
      showOverlay('Could not start the built-in ROM: ' + e.message +
                  '\nUse "Open ROM" to load a .gb/.gbc file.');
    }
  } else {
    showOverlay('No ROM is built in. Tap "Open ROM" to choose a .gb/.gbc file.');
  }
})();

// ---- UI helpers ------------------------------------------------------------
function showOverlay(msg) {
  const o = $('#overlay');
  if (!o) return;
  $('#overlay_msg').textContent = msg;
  o.style.display = 'flex';
}
function hideOverlay() {
  const o = $('#overlay');
  if (o) o.style.display = 'none';
}

function openRomFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    const module = await binjgbPromise;
    try {
      startRom(module, reader.result, file.name);
    } catch (e) {
      showOverlay('That file is not a valid Game Boy ROM.\n' + e.message);
    }
  };
  reader.readAsArrayBuffer(file);
}

window.addEventListener('DOMContentLoaded', () => {
  const fileInput = $('#romFile');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => openRomFile(e.target.files[0]));
  }
  const openBtn = $('#btnOpen');
  if (openBtn) openBtn.addEventListener('click', () => fileInput && fileInput.click());

  const saveBtn = $('#btnSave');
  if (saveBtn) saveBtn.addEventListener('click', () => emulator && emulator.saveState());
  const loadBtn = $('#btnLoad');
  if (loadBtn) loadBtn.addEventListener('click', () => emulator && emulator.loadState());

  const fsBtn = $('#btnFull');
  if (fsBtn) fsBtn.addEventListener('click', () => {
    // Fullscreen the whole page (documentElement), NOT just #game -- otherwise
    // the browser hides everything outside the game element (toolbar, on-screen
    // gamepad, menu) and the controls vanish.
    const doc = document;
    const el = doc.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    const exit = doc.exitFullscreen || doc.webkitExitFullscreen;
    if (doc.fullscreenElement || doc.webkitFullscreenElement) {
      if (exit) exit.call(doc);
    } else if (req) {
      req.call(el);
    }
  });

  // Drag-and-drop a ROM onto the window.
  window.addEventListener('dragover', (e) => e.preventDefault());
  window.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files[0]) openRomFile(e.dataTransfer.files[0]);
  });
});

function makeWasmBuffer(module, ptr, size) {
  return new Uint8Array(module.HEAP8.buffer, ptr, size);
}

class Emulator {
  static start(module, romBuffer, extRamBuffer) {
    Emulator.stop();
    emulator = new Emulator(module, romBuffer, extRamBuffer);
    window.__emulator = emulator; // exposed for UI controls (speed, etc.)
    emulator.run();
  }

  static stop() {
    if (emulator) {
      emulator.destroy();
      emulator = null;
    }
  }

  constructor(module, romBuffer, extRamBuffer) {
    this.module = module;
    const size = (romBuffer.byteLength + 0x7fff) & ~0x7fff;
    this.romDataPtr = this.module._malloc(size);
    makeWasmBuffer(this.module, this.romDataPtr, size)
        .fill(0)
        .set(new Uint8Array(romBuffer));
    this.e = this.module._emulator_new_simple(
        this.romDataPtr, size, Audio.ctx.sampleRate, AUDIO_FRAMES,
        CGB_COLOR_CURVE);
    if (this.e == 0) {
      this.module._free(this.romDataPtr);
      throw new Error('Invalid ROM.');
    }

    this.audio = new Audio(module, this.e);
    this.video = new Video(module, this.e, $('canvas'));
    this.rewind = new Rewind(module, this.e);
    this.rewindIntervalId = 0;

    this.lastRafSec = 0;
    this.leftoverTicks = 0;
    this.fps = 60;
    this.fastForward = false;

    if (extRamBuffer && extRamBuffer.byteLength > 0) {
      this.loadExtRam(extRamBuffer);
    }

    this.bindKeys();
    this.bindTouch();

    this.touchEnabled = 'ontouchstart' in document.documentElement;
    this.updateOnscreenGamepad();
  }

  destroy() {
    this.unbindTouch();
    this.unbindKeys();
    this.cancelAnimationFrame();
    clearInterval(this.rewindIntervalId);
    this.rewind.destroy();
    this.audio.destroy();
    this.module._emulator_delete(this.e);
    this.module._free(this.romDataPtr);
  }

  withNewFileData(fileDataPtr, cb) {
    const buffer = makeWasmBuffer(
        this.module, this.module._get_file_data_ptr(fileDataPtr),
        this.module._get_file_data_size(fileDataPtr));
    const result = cb(fileDataPtr, buffer);
    this.module._file_data_delete(fileDataPtr);
    return result;
  }

  withNewExtRamFileData(cb) {
    return this.withNewFileData(this.module._ext_ram_file_data_new(this.e), cb);
  }

  withNewStateFileData(cb) {
    return this.withNewFileData(this.module._state_file_data_new(this.e), cb);
  }

  loadExtRam(extRamBuffer) {
    this.withNewExtRamFileData((fileDataPtr, buffer) => {
      if (buffer.byteLength === extRamBuffer.byteLength) {
        buffer.set(new Uint8Array(extRamBuffer));
        this.module._emulator_read_ext_ram(this.e, fileDataPtr);
      }
    });
  }

  getExtRam() {
    return this.withNewExtRamFileData((fileDataPtr, buffer) => {
      this.module._emulator_write_ext_ram(this.e, fileDataPtr);
      return new Uint8Array(buffer);
    });
  }

  loadState() {
    let saved;
    try { saved = localStorage.getItem(saveStateKey); } catch (e) {}
    if (!saved) return;
    const saveStateBuffer = new Uint8Array(JSON.parse(saved));
    this.withNewStateFileData((fileDataPtr, buffer) => {
      if (buffer.byteLength === saveStateBuffer.byteLength) {
        buffer.set(new Uint8Array(saveStateBuffer));
        this.module._emulator_read_state(this.e, fileDataPtr);
      }
    });
  }

  saveState() {
    const saveStateBuffer = this.withNewStateFileData((fileDataPtr, buffer) => {
      this.module._emulator_write_state(this.e, fileDataPtr);
      return new Uint8Array(buffer);
    });
    try {
      localStorage.setItem(saveStateKey, JSON.stringify(Array.from(saveStateBuffer)));
    } catch (e) { /* ignore */ }
  }

  // --- Named save slots (per-ROM). Used by the menu UI in build_player.py. ---
  saveStateToSlot(slot) {
    const buf = this.withNewStateFileData((fileDataPtr, buffer) => {
      this.module._emulator_write_state(this.e, fileDataPtr);
      return new Uint8Array(buffer);
    });
    try {
      localStorage.setItem(saveStateKey + ':' + slot, JSON.stringify(Array.from(buf)));
      localStorage.setItem(saveStateKey + ':' + slot + ':ts', String(Date.now()));
    } catch (e) { /* ignore */ }
  }

  loadStateFromSlot(slot) {
    let saved;
    try { saved = localStorage.getItem(saveStateKey + ':' + slot); } catch (e) {}
    if (!saved) return false;
    const stateBuffer = new Uint8Array(JSON.parse(saved));
    this.withNewStateFileData((fileDataPtr, buffer) => {
      if (buffer.byteLength === stateBuffer.byteLength) {
        buffer.set(new Uint8Array(stateBuffer));
        this.module._emulator_read_state(this.e, fileDataPtr);
      }
    });
    return true;
  }

  get isPaused() { return this.rafCancelToken === null; }

  pause() {
    if (!this.isPaused) {
      this.cancelAnimationFrame();
      this.audio.pause();
      this.beginRewind();
    }
  }

  resume() {
    if (this.isPaused) {
      this.endRewind();
      this.requestAnimationFrame();
      this.audio.resume();
    }
  }

  setBuiltinPalette(palIdx) {
    this.module._emulator_set_builtin_palette(this.e, PALETTES[palIdx]);
  }

  get isRewinding() { return ENABLE_REWIND && this.rewind.isRewinding; }

  beginRewind() {
    if (!ENABLE_REWIND) { return; }
    this.rewind.beginRewind();
  }

  rewindToTicks(ticks) {
    if (!ENABLE_REWIND) { return; }
    if (this.rewind.rewindToTicks(ticks)) {
      this.runUntil(ticks);
      this.video.renderTexture();
    }
  }

  endRewind() {
    if (!ENABLE_REWIND) { return; }
    this.rewind.endRewind();
    this.lastRafSec = 0;
    this.leftoverTicks = 0;
    this.audio.startSec = 0;
  }

  set autoRewind(enabled) {
    if (!ENABLE_REWIND) { return; }
    if (enabled) {
      this.rewindIntervalId = setInterval(() => {
        const oldest = this.rewind.oldestTicks;
        const start = this.ticks;
        const delta =
            REWIND_FACTOR * REWIND_UPDATE_MS / 1000 * CPU_TICKS_PER_SECOND;
        const rewindTo = Math.max(oldest, start - delta);
        this.rewindToTicks(rewindTo);
        vm.ticks = emulator.ticks;
      }, REWIND_UPDATE_MS);
    } else {
      clearInterval(this.rewindIntervalId);
      this.rewindIntervalId = 0;
    }
  }

  requestAnimationFrame() {
    this.rafCancelToken = requestAnimationFrame(this.rafCallback.bind(this));
  }

  cancelAnimationFrame() {
    cancelAnimationFrame(this.rafCancelToken);
    this.rafCancelToken = null;
  }

  run() { this.requestAnimationFrame(); }

  get ticks() { return this.module._emulator_get_ticks_f64(this.e); }

  runUntil(ticks) {
    while (true) {
      const event = this.module._emulator_run_until_f64(this.e, ticks);
      if (event & EVENT_NEW_FRAME) {
        this.rewind.pushBuffer();
        this.video.uploadTexture();
      }
      if ((event & EVENT_AUDIO_BUFFER_FULL) && !this.isRewinding) {
        this.audio.pushBuffer();
      }
      if (event & EVENT_UNTIL_TICKS) { break; }
    }
    if (this.module._emulator_was_ext_ram_updated(this.e)) {
      vm.extRamUpdated = true;
    }
  }

  rafCallback(startMs) {
    this.requestAnimationFrame();
    let deltaSec = 0;
    if (!this.isRewinding) {
      const startSec = startMs / 1000;
      deltaSec = Math.max(startSec - (this.lastRafSec || startSec), 0);

      const startTimeMs = performance.now();
      const speedMul = window.__speed || 1; // UI speed control: 1x / 2x / 4x
      const deltaTicks =
          Math.min(deltaSec, MAX_UPDATE_SEC) * CPU_TICKS_PER_SECOND * speedMul;
      let runUntilTicks = this.ticks + deltaTicks - this.leftoverTicks;
      this.runUntil(runUntilTicks);
      const deltaTimeMs = performance.now() - startTimeMs;
      const deltaTimeSec = deltaTimeMs / 1000;

      if (this.fastForward) {
        const speedUp = (deltaTicks / CPU_TICKS_PER_SECOND) / deltaTimeSec;
        const extraFrames = Math.floor(speedUp - deltaTimeSec);
        const extraTicks = extraFrames * deltaTicks;
        runUntilTicks = this.ticks + extraTicks - this.leftoverTicks;
        this.runUntil(runUntilTicks);
      }

      this.leftoverTicks = (this.ticks - runUntilTicks) | 0;
      this.lastRafSec = startSec;
    }
    const lerp = (from, to, alpha) => (alpha * from) + (1 - alpha) * to;
    this.fps = lerp(this.fps, Math.min(1 / deltaSec, 10000), 0.3);
    this.video.renderTexture();
  }

  updateOnscreenGamepad() {
    $('#controller').style.display = this.touchEnabled ? 'block' : 'none';
  }

  bindTouch() {
    this.touchFuncs = {
      'controller_b': this.setJoypB.bind(this),
      'controller_a': this.setJoypA.bind(this),
      'controller_start': this.setJoypStart.bind(this),
      'controller_select': this.setJoypSelect.bind(this),
    };

    this.boundButtonTouchStart = this.buttonTouchStart.bind(this);
    this.boundButtonTouchEnd = this.buttonTouchEnd.bind(this);
    selectEl.addEventListener('touchstart', this.boundButtonTouchStart);
    selectEl.addEventListener('touchend', this.boundButtonTouchEnd);
    startEl.addEventListener('touchstart', this.boundButtonTouchStart);
    startEl.addEventListener('touchend', this.boundButtonTouchEnd);
    bEl.addEventListener('touchstart', this.boundButtonTouchStart);
    bEl.addEventListener('touchend', this.boundButtonTouchEnd);
    aEl.addEventListener('touchstart', this.boundButtonTouchStart);
    aEl.addEventListener('touchend', this.boundButtonTouchEnd);

    this.boundDpadTouchStartMove = this.dpadTouchStartMove.bind(this);
    this.boundDpadTouchEnd = this.dpadTouchEnd.bind(this);
    dpadEl.addEventListener('touchstart', this.boundDpadTouchStartMove);
    dpadEl.addEventListener('touchmove', this.boundDpadTouchStartMove);
    dpadEl.addEventListener('touchend', this.boundDpadTouchEnd);

    this.boundTouchRestore = this.touchRestore.bind(this);
    window.addEventListener('touchstart', this.boundTouchRestore);
  }

  unbindTouch() {
    selectEl.removeEventListener('touchstart', this.boundButtonTouchStart);
    selectEl.removeEventListener('touchend', this.boundButtonTouchEnd);
    startEl.removeEventListener('touchstart', this.boundButtonTouchStart);
    startEl.removeEventListener('touchend', this.boundButtonTouchEnd);
    bEl.removeEventListener('touchstart', this.boundButtonTouchStart);
    bEl.removeEventListener('touchend', this.boundButtonTouchEnd);
    aEl.removeEventListener('touchstart', this.boundButtonTouchStart);
    aEl.removeEventListener('touchend', this.boundButtonTouchEnd);

    dpadEl.removeEventListener('touchstart', this.boundDpadTouchStartMove);
    dpadEl.removeEventListener('touchmove', this.boundDpadTouchStartMove);
    dpadEl.removeEventListener('touchend', this.boundDpadTouchEnd);

    window.removeEventListener('touchstart', this.boundTouchRestore);
  }

  buttonTouchStart(event) {
    if (event.currentTarget.id in this.touchFuncs) {
      this.touchFuncs[event.currentTarget.id](true);
      event.currentTarget.classList.add('btnPressed');
      event.preventDefault();
    }
  }

  buttonTouchEnd(event) {
    if (event.currentTarget.id in this.touchFuncs) {
      this.touchFuncs[event.currentTarget.id](false);
      event.currentTarget.classList.remove('btnPressed');
      event.preventDefault();
    }
  }

  dpadTouchStartMove(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (2 * (event.targetTouches[0].clientX - rect.left)) / rect.width - 1;
    const y = (2 * (event.targetTouches[0].clientY - rect.top)) / rect.height - 1;

    if (Math.abs(x) > OSGP_DEADZONE) {
      if (y > x && y < -x) {
        this.setJoypLeft(true);
        this.setJoypRight(false);
      } else if (y < x && y > -x) {
        this.setJoypLeft(false);
        this.setJoypRight(true);
      }
    } else {
      this.setJoypLeft(false);
      this.setJoypRight(false);
    }

    if (Math.abs(y) > OSGP_DEADZONE) {
      if (x > y && x < -y) {
        this.setJoypUp(true);
        this.setJoypDown(false);
      } else if (x < y && x > -y) {
        this.setJoypUp(false);
        this.setJoypDown(true);
      }
    } else {
      this.setJoypUp(false);
      this.setJoypDown(false);
    }
    event.preventDefault();
  }

  dpadTouchEnd(event) {
    this.setJoypLeft(false);
    this.setJoypRight(false);
    this.setJoypUp(false);
    this.setJoypDown(false);
    event.preventDefault();
  }

  touchRestore() {
    this.touchEnabled = true;
    this.updateOnscreenGamepad();
  }

  bindKeys() {
    this.keyFuncs = {
      'ArrowDown': this.setJoypDown.bind(this),
      'ArrowLeft': this.setJoypLeft.bind(this),
      'ArrowRight': this.setJoypRight.bind(this),
      'ArrowUp': this.setJoypUp.bind(this),
      'KeyZ': this.setJoypB.bind(this),
      'KeyX': this.setJoypA.bind(this),
      'Enter': this.setJoypStart.bind(this),
      'Tab': this.setJoypSelect.bind(this),
      'Backspace': this.keyRewind.bind(this),
      'Space': this.keyPause.bind(this),
      'BracketLeft': this.keyPrevPalette.bind(this),
      'BracketRight': this.keyNextPalette.bind(this),
      'ShiftLeft': this.setFastForward.bind(this),
      'F6': this.saveState.bind(this),
      'F9': this.loadState.bind(this),
    };
    this.boundKeyDown = this.keyDown.bind(this);
    this.boundKeyUp = this.keyUp.bind(this);

    window.addEventListener('keydown', this.boundKeyDown);
    window.addEventListener('keyup', this.boundKeyUp);
  }

  unbindKeys() {
    window.removeEventListener('keydown', this.boundKeyDown);
    window.removeEventListener('keyup', this.boundKeyUp);
  }

  keyDown(event) {
    if (event.code in this.keyFuncs) {
      if (this.touchEnabled) {
        this.touchEnabled = false;
        this.updateOnscreenGamepad();
      }
      this.keyFuncs[event.code](true);
      event.preventDefault();
    }
  }

  keyUp(event) {
    if (event.code in this.keyFuncs) {
      this.keyFuncs[event.code](false);
      event.preventDefault();
    }
  }

  keyRewind(isKeyDown) {
    if (!ENABLE_REWIND) { return; }
    if (this.isRewinding !== isKeyDown) {
      if (isKeyDown) {
        vm.paused = true;
        this.autoRewind = true;
      } else {
        this.autoRewind = false;
        vm.paused = false;
      }
    }
  }

  keyPause(isKeyDown) {
    if (!ENABLE_PAUSE) { return; }
    if (isKeyDown) vm.togglePause();
  }

  keyPrevPalette(isKeyDown) {
    if (!ENABLE_SWITCH_PALETTES) { return; }
    if (isKeyDown) {
      vm.palIdx = (vm.palIdx + PALETTES.length - 1) % PALETTES.length;
      emulator.setBuiltinPalette(vm.palIdx);
    }
  }

  keyNextPalette(isKeyDown) {
    if (!ENABLE_SWITCH_PALETTES) { return; }
    if (isKeyDown) {
      vm.palIdx = (vm.palIdx + 1) % PALETTES.length;
      emulator.setBuiltinPalette(vm.palIdx);
    }
  }

  setFastForward(isKeyDown) {
    if (!ENABLE_FAST_FORWARD) { return; }
    this.fastForward = isKeyDown;
  }

  setJoypDown(set) { this.module._set_joyp_down(this.e, set); }
  setJoypUp(set) { this.module._set_joyp_up(this.e, set); }
  setJoypLeft(set) { this.module._set_joyp_left(this.e, set); }
  setJoypRight(set) { this.module._set_joyp_right(this.e, set); }
  setJoypSelect(set) { this.module._set_joyp_select(this.e, set); }
  setJoypStart(set) { this.module._set_joyp_start(this.e, set); }
  setJoypB(set) { this.module._set_joyp_B(this.e, set); }
  setJoypA(set) { this.module._set_joyp_A(this.e, set); }
}

// Multiple save slots, keyed per-ROM. Exposed for the menu UI (build_player.py).
// __pqSave returns false if no game is running yet; __pqSlots reports which
// slots are occupied and when they were last written.
window.__pqSave = function (slot) {
  if (!emulator) return false;
  emulator.saveStateToSlot(slot);
  return true;
};
window.__pqLoad = function (slot) {
  return emulator ? emulator.loadStateFromSlot(slot) : false;
};
window.__pqSlots = function () {
  const out = [];
  for (let i = 1; i <= 3; i++) {
    let ts = 0;
    try { const v = localStorage.getItem(saveStateKey + ':' + i + ':ts'); if (v) ts = +v; } catch (e) {}
    out.push({ slot: i, ts: ts, used: ts > 0 });
  }
  return out;
};

class Audio {
  constructor(module, e) {
    this.started = false;
    this.module = module;
    this.buffer = makeWasmBuffer(
        this.module, this.module._get_audio_buffer_ptr(e),
        this.module._get_audio_buffer_capacity(e));
    this.startSec = 0;
    this.resume();

    this.boundStartPlayback = this.startPlayback.bind(this);
    window.addEventListener('keydown', this.boundStartPlayback, true);
    window.addEventListener('click', this.boundStartPlayback, true);
    window.addEventListener('touchend', this.boundStartPlayback, true);
  }

  startPlayback() {
    window.removeEventListener('touchend', this.boundStartPlayback, true);
    window.removeEventListener('keydown', this.boundStartPlayback, true);
    window.removeEventListener('click', this.boundStartPlayback, true);
    this.started = true;
    this.resume();
  }

  get sampleRate() { return Audio.ctx.sampleRate; }

  pushBuffer() {
    if (!this.started) { return; }
    const nowSec = Audio.ctx.currentTime;
    const nowPlusLatency = nowSec + AUDIO_LATENCY_SEC;
    const volume = vm.volume;
    this.startSec = (this.startSec || nowPlusLatency);
    // Resync if we've fallen behind, OR run too far ahead (e.g. at 2x/4x speed
    // the core generates audio faster than real time). Without this cap the
    // scheduled time races ahead unbounded and playback eventually stalls.
    if (this.startSec < nowSec || this.startSec > nowSec + 0.5) {
      this.startSec = nowPlusLatency;
    }
    {
      const buffer = Audio.ctx.createBuffer(2, AUDIO_FRAMES, this.sampleRate);
      const channel0 = buffer.getChannelData(0);
      const channel1 = buffer.getChannelData(1);
      for (let i = 0; i < AUDIO_FRAMES; i++) {
        channel0[i] = this.buffer[2 * i] * volume / 255;
        channel1[i] = this.buffer[2 * i + 1] * volume / 255;
      }
      const bufferSource = Audio.ctx.createBufferSource();
      bufferSource.buffer = buffer;
      bufferSource.connect(Audio.ctx.destination);
      bufferSource.start(this.startSec);
      const bufferSec = AUDIO_FRAMES / this.sampleRate;
      this.startSec += bufferSec;
    }
  }

  pause() {
    if (!this.started) { return; }
    Audio.ctx.suspend();
  }

  resume() {
    if (!this.started) { return; }
    Audio.ctx.resume();
  }

  destroy() {
    if (this.boundStartPlayback) {
      window.removeEventListener('keydown',  this.boundStartPlayback, true);
      window.removeEventListener('click',    this.boundStartPlayback, true);
      window.removeEventListener('touchend', this.boundStartPlayback, true);
      this.boundStartPlayback = null;
    }
    this.buffer = null;
    this.started = false;
  }
}

Audio.ctx = new AudioContext;
// Keep audio alive: mobile browsers suspend the AudioContext when the tab/app
// loses focus or the screen locks. Resume it whenever we regain focus or the
// user touches the screen. Exposed so UI controls can resume it too.
window.__resumeAudio = function () { try { if (Audio.ctx.state === 'suspended') Audio.ctx.resume(); } catch (e) {} };
document.addEventListener('visibilitychange', function () { if (!document.hidden) window.__resumeAudio(); });
window.addEventListener('pointerdown', window.__resumeAudio, true);
window.addEventListener('focus', window.__resumeAudio);

class Video {
  constructor(module, e, el) {
    this.module = module;
    if (window.navigator.userAgent.match(/iPhone|iPad/)) {
      this.renderer = new Canvas2DRenderer(el);
    } else {
      try {
        this.renderer = new WebGLRenderer(el);
      } catch (error) {
        console.log(`Error creating WebGLRenderer: ${error}`);
        this.renderer = new Canvas2DRenderer(el);
      }
    }
    this.buffer = makeWasmBuffer(
        this.module, this.module._get_frame_buffer_ptr(e),
        this.module._get_frame_buffer_size(e));
  }

  uploadTexture() { this.renderer.uploadTexture(this.buffer); }
  renderTexture() { this.renderer.renderTexture(); }
}

class Canvas2DRenderer {
  constructor(el) {
    this.ctx = el.getContext('2d');
    this.imageData = this.ctx.createImageData(el.width, el.height);
  }
  renderTexture() { this.ctx.putImageData(this.imageData, 0, 0); }
  uploadTexture(buffer) { this.imageData.data.set(buffer); }
}

class WebGLRenderer {
  constructor(el) {
    const gl = this.gl = el.getContext('webgl', {preserveDrawingBuffer: true});
    if (gl === null) { throw new Error('unable to create webgl context'); }

    // Render at 3x the GB resolution for a sharper base image (and so the HD
    // upscaler has output pixels to fill).
    el.width = SCREEN_WIDTH * 3;
    el.height = SCREEN_HEIGHT * 3;
    gl.viewport(0, 0, el.width, el.height);

    const w = SCREEN_WIDTH / 256;
    const h = SCREEN_HEIGHT / 256;
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,  0, h,
      +1, -1,  w, h,
      -1, +1,  0, 0,
      +1, +1,  w, 0,
    ]), gl.STATIC_DRAW);

    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(
        gl.TEXTURE_2D, 0, gl.RGBA, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);

    function compileShader(type, source) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        throw new Error(`compileShader failed: ${gl.getShaderInfoLog(shader)}`);
      }
      return shader;
    }

    const vertexShader = compileShader(gl.VERTEX_SHADER,
       `attribute vec2 aPos;
        attribute vec2 aTexCoord;
        varying highp vec2 vTexCoord;
        void main(void) {
          gl_Position = vec4(aPos, 0.0, 1.0);
          vTexCoord = aTexCoord;
        }`);
    // HD upscaler: when uHD>=0.5, smooth jagged edges with the Scale3x
    // algorithm; otherwise pass the pixels through unchanged. If this richer
    // shader fails to compile on some GPU, fall back to the plain passthrough.
    const hdFragSrc =
       `precision highp float;
        varying highp vec2 vTexCoord;
        uniform sampler2D uSampler;
        uniform vec2 uTexSize;
        uniform float uHD;
        bool eq(vec3 a, vec3 b){ return all(lessThan(abs(a-b), vec3(0.02))); }
        vec3 tx(vec2 t){ return texture2D(uSampler, t).rgb; }
        void main(void){
          if (uHD < 0.5) { gl_FragColor = texture2D(uSampler, vTexCoord); return; }
          vec2 px = 1.0/uTexSize; vec2 t = vTexCoord;
          vec3 A=tx(t+px*vec2(-1.,-1.)), B=tx(t+px*vec2(0.,-1.)), C=tx(t+px*vec2(1.,-1.));
          vec3 D=tx(t+px*vec2(-1.,0.)),  E=tx(t),                 F=tx(t+px*vec2(1.,0.));
          vec3 G=tx(t+px*vec2(-1.,1.)),  H=tx(t+px*vec2(0.,1.)),  I=tx(t+px*vec2(1.,1.));
          bool DB=eq(D,B), BF=eq(B,F), DH=eq(D,H), HF=eq(H,F);
          vec2 f = floor(fract(t*uTexSize)*3.0);
          vec3 r = E;
          if (f.x<0.5 && f.y<0.5) { if (DB&&!BF&&!DH) r=D; }
          else if (f.x>1.5 && f.y<0.5) { if (BF&&!DB&&!HF) r=F; }
          else if (f.x<0.5 && f.y>1.5) { if (DH&&!DB&&!HF) r=D; }
          else if (f.x>1.5 && f.y>1.5) { if (HF&&!DH&&!BF) r=F; }
          else if (f.y<0.5) { if ((DB&&!BF&&!DH&&!eq(E,C))||(BF&&!DB&&!HF&&!eq(E,A))) r=B; }
          else if (f.y>1.5) { if ((DH&&!DB&&!HF&&!eq(E,I))||(HF&&!DH&&!BF&&!eq(E,G))) r=H; }
          else if (f.x<0.5) { if ((DB&&!BF&&!DH&&!eq(E,G))||(DH&&!DB&&!HF&&!eq(E,A))) r=D; }
          else if (f.x>1.5) { if ((BF&&!DB&&!HF&&!eq(E,I))||(HF&&!DH&&!BF&&!eq(E,C))) r=F; }
          gl_FragColor = vec4(r, 1.0);
        }`;
    let fragmentShader, hdEnabled = true;
    try { fragmentShader = compileShader(gl.FRAGMENT_SHADER, hdFragSrc); }
    catch (e) {
      hdEnabled = false;
      fragmentShader = compileShader(gl.FRAGMENT_SHADER,
       `varying highp vec2 vTexCoord;
        uniform sampler2D uSampler;
        void main(void) { gl_FragColor = texture2D(uSampler, vTexCoord); }`);
    }

    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(`program link failed: ${gl.getProgramInfoLog(program)}`);
    }
    gl.useProgram(program);

    const aPos = gl.getAttribLocation(program, 'aPos');
    const aTexCoord = gl.getAttribLocation(program, 'aTexCoord');
    const uSampler = gl.getUniformLocation(program, 'uSampler');

    gl.enableVertexAttribArray(aPos);
    gl.enableVertexAttribArray(aTexCoord);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, gl.FALSE, 16, 0);
    gl.vertexAttribPointer(aTexCoord, 2, gl.FLOAT, gl.FALSE, 16, 8);
    gl.uniform1i(uSampler, 0);

    // HD upscaler controls (no-ops if the HD shader wasn't compiled).
    const uTexSize = gl.getUniformLocation(program, 'uTexSize');
    if (uTexSize) gl.uniform2f(uTexSize, 256.0, 256.0);
    this.uHD = hdEnabled ? gl.getUniformLocation(program, 'uHD') : null;
    const initHD = hdEnabled && window.__hd !== false ? 1.0 : 0.0;
    if (this.uHD) gl.uniform1f(this.uHD, initHD);
    const self = this;
    window.__glSetHD = function (on) {
      if (!self.uHD) return;
      self.gl.useProgram(program);
      self.gl.uniform1f(self.uHD, on ? 1.0 : 0.0);
    };
    window.__hdAvailable = hdEnabled;
  }

  renderTexture() {
    this.gl.clearColor(0.5, 0.5, 0.5, 1.0);
    this.gl.clear(this.gl.COLOR_BUFFER_BIT);
    this.gl.drawArrays(this.gl.TRIANGLE_STRIP, 0, 4);
  }

  uploadTexture(buffer) {
    this.gl.texSubImage2D(
        this.gl.TEXTURE_2D, 0, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, this.gl.RGBA,
        this.gl.UNSIGNED_BYTE, buffer);
  }
}

class Rewind {
  constructor(module, e) {
    this.module = module;
    this.e = e;
    this.joypadBufferPtr = this.module._joypad_new();
    this.statePtr = 0;
    this.bufferPtr = this.module._rewind_new_simple(
        e, REWIND_FRAMES_PER_BASE_STATE, REWIND_BUFFER_CAPACITY);
    this.module._emulator_set_default_joypad_callback(e, this.joypadBufferPtr);
  }

  destroy() {
    this.module._rewind_delete(this.bufferPtr);
    this.module._joypad_delete(this.joypadBufferPtr);
  }

  get oldestTicks() { return this.module._rewind_get_oldest_ticks_f64(this.bufferPtr); }
  get newestTicks() { return this.module._rewind_get_newest_ticks_f64(this.bufferPtr); }

  pushBuffer() {
    if (!this.isRewinding) {
      this.module._rewind_append(this.bufferPtr, this.e);
    }
  }

  get isRewinding() { return this.statePtr !== 0; }

  beginRewind() {
    if (this.isRewinding) return;
    this.statePtr =
        this.module._rewind_begin(this.e, this.bufferPtr, this.joypadBufferPtr);
  }

  rewindToTicks(ticks) {
    if (!this.isRewinding) return;
    return this.module._rewind_to_ticks_wrapper(this.statePtr, ticks) ===
        RESULT_OK;
  }

  endRewind() {
    if (!this.isRewinding) return;
    this.module._emulator_set_default_joypad_callback(
        this.e, this.joypadBufferPtr);
    this.module._rewind_end(this.statePtr);
    this.statePtr = 0;
  }
}
