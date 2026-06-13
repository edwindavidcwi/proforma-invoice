/*
 * Minimal offline driver for IodineGBA (pure-JS Game Boy Advance emulator).
 *
 * IodineGBA core + glue (GfxGlueCode, AudioGlueCode, XAudioJS) are MIT-licensed,
 *   Copyright (C) 2010-2019 Grant Galitz.  See IodineGBA.LICENSE.
 *
 * This driver replaces IodineGBA's menu-heavy GUIGlueCode/CoreGlueCode with a
 * tiny frontend tuned for a single self-contained .html that runs from file://:
 *   - forces the ON-THREAD core (no Web Workers, no SharedArrayBuffer), so it
 *     works offline from a local file with no special server headers;
 *   - skips the GBA BIOS (HLE), so no copyrighted BIOS file is needed;
 *   - loads the ROM from an inlined base64 blob (window.__ROM_B64__);
 *   - maps keyboard + on-screen touch buttons to the pad.
 */
"use strict";
(function () {
  // GBA pad indices used by Iodine.keyDown/keyUp:
  // A=0 B=1 Select=2 Start=3 Right=4 Left=5 Up=6 Down=7 R=8 L=9
  var PAD = { A:0, B:1, SELECT:2, START:3, RIGHT:4, LEFT:5, UP:6, DOWN:7, R:8, L:9 };

  var KEYMAP = {
    "KeyX":PAD.A, "KeyZ":PAD.B,
    "ShiftRight":PAD.SELECT, "ShiftLeft":PAD.L,
    "Enter":PAD.START,
    "ArrowRight":PAD.RIGHT, "ArrowLeft":PAD.LEFT, "ArrowUp":PAD.UP, "ArrowDown":PAD.DOWN,
    "KeyS":PAD.R, "KeyA":PAD.L,
    "Backspace":PAD.SELECT
  };

  var Iodine = null, Blitter = null, Mixer = null, mixerInput = null;
  var coreTimerID = null, startTime = Date.now(), audioOn = false;

  function $(id){ return document.getElementById(id); }

  function b64ToBytes(b64) {
    var bin = atob(b64), len = bin.length, bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  }

  function startTimer() {
    if (coreTimerID) return;
    coreTimerID = setInterval(function () {
      Iodine.timerCallback(((Date.now()) - startTime) >>> 0);
    }, 8);
  }
  function stopTimer() {
    if (coreTimerID) { clearInterval(coreTimerID); coreTimerID = null; }
  }

  function showOverlay(msg) {
    var o = $("overlay"); if (!o) return;
    $("overlay_msg").textContent = msg; o.style.display = "flex";
  }
  function hideOverlay() { var o = $("overlay"); if (o) o.style.display = "none"; }

  // Resume/enable audio on the first user gesture (browser autoplay policy).
  function enableAudioOnce() {
    if (audioOn || !Iodine) return;
    try {
      Iodine.enableAudio();
      if (Mixer && Mixer.audio && Mixer.audio.audioContextHandle &&
          Mixer.audio.audioContextHandle.resume) {
        Mixer.audio.audioContextHandle.resume();
      }
      audioOn = true;
      var b = $("btnSound"); if (b) b.textContent = "Sound: on";
    } catch (e) { console.warn("audio enable failed", e); }
  }

  function startRom(romBytes, name) {
    stopTimer();
    Iodine = new GameBoyAdvanceEmulator();
    Iodine.setIntervalRate(8);
    Iodine.toggleOffthreadGraphics(false); // in-thread render -> no workers
    Iodine.toggleDynamicSpeed(false);
    Iodine.toggleSkipBootROM(true);        // skip the BIOS intro animation
    // The core requires these handlers to exist before play().
    Iodine.attachPlayStatusHandler(function (isPlaying) {});
    if (Iodine.attachSpeedHandler) Iodine.attachSpeedHandler(function (s) {});

    Blitter = new GfxGlueCode(240, 160);
    Blitter.attachCanvas($("emulator_target"));
    Iodine.attachGraphicsFrameHandler(Blitter);
    try { Blitter.setSmoothScaling(true); } catch (e) {}

    try {
      Mixer = new GlueCodeMixer($("emulator_target"));
      mixerInput = new GlueCodeMixerInput(Mixer);
      Iodine.attachAudioHandler(mixerInput);
      mixerInput.setVolume(1);
    } catch (e) { console.warn("audio init failed; running muted", e); }

    // IodineGBA has no HLE BIOS, so a real 16 KB BIOS must be provided.
    // We bundle the open-source Cult-of-GBA replacement BIOS (MIT).
    if (window.__BIOS_B64__ && window.__BIOS_B64__.length) {
      Iodine.attachBIOS(b64ToBytes(window.__BIOS_B64__));
    }
    Iodine.attachROM(romBytes);
    Iodine.play();
    startTimer();
    hideOverlay();
  }

  // ---- input -------------------------------------------------------------
  function bindKeys() {
    window.addEventListener("keydown", function (e) {
      enableAudioOnce();
      if (e.code in KEYMAP) { Iodine.keyDown(KEYMAP[e.code]); e.preventDefault(); }
    });
    window.addEventListener("keyup", function (e) {
      if (e.code in KEYMAP) { Iodine.keyUp(KEYMAP[e.code]); e.preventDefault(); }
    });
  }

  function bindButton(el, padIndex) {
    if (!el) return;
    var down = function (e) { enableAudioOnce(); Iodine.keyDown(padIndex); el.classList.add("pressed"); e.preventDefault(); };
    var up   = function (e) { Iodine.keyUp(padIndex); el.classList.remove("pressed"); e.preventDefault(); };
    el.addEventListener("touchstart", down, {passive:false});
    el.addEventListener("touchend", up, {passive:false});
    el.addEventListener("touchcancel", up, {passive:false});
    el.addEventListener("mousedown", down);
    el.addEventListener("mouseup", up);
    el.addEventListener("mouseleave", up);
  }

  function bindTouch() {
    bindButton($("touch-up"), PAD.UP);
    bindButton($("touch-down"), PAD.DOWN);
    bindButton($("touch-left"), PAD.LEFT);
    bindButton($("touch-right"), PAD.RIGHT);
    bindButton($("touch-a"), PAD.A);
    bindButton($("touch-b"), PAD.B);
    bindButton($("touch-l"), PAD.L);
    bindButton($("touch-r"), PAD.R);
    bindButton($("touch-start"), PAD.START);
    bindButton($("touch-select"), PAD.SELECT);
  }

  function openRomFile(file) {
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      try { startRom(new Uint8Array(reader.result), file.name); }
      catch (e) { showOverlay("That file could not be loaded as a GBA ROM.\n" + e.message); }
    };
    reader.readAsArrayBuffer(file);
  }

  function wireToolbar() {
    var fileInput = $("romFile");
    if (fileInput) fileInput.addEventListener("change", function (e) { openRomFile(e.target.files[0]); });
    var openBtn = $("btnOpen");
    if (openBtn) openBtn.addEventListener("click", function () { fileInput && fileInput.click(); });
    var soundBtn = $("btnSound");
    if (soundBtn) soundBtn.addEventListener("click", enableAudioOnce);
    var fsBtn = $("btnFull");
    if (fsBtn) fsBtn.addEventListener("click", function () {
      var el = $("stage");
      if (document.fullscreenElement) document.exitFullscreen();
      else if (el.requestFullscreen) el.requestFullscreen();
    });
    window.addEventListener("dragover", function (e) { e.preventDefault(); });
    window.addEventListener("drop", function (e) {
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files[0]) openRomFile(e.dataTransfer.files[0]);
    });
    // Pause when tab hidden, resume when visible.
    document.addEventListener("visibilitychange", function () {
      if (!Iodine) return;
      if (document.hidden) { Iodine.pause(); stopTimer(); }
      else { Iodine.play(); startTimer(); }
    });
  }

  function boot() {
    wireToolbar();
    bindKeys();
    bindTouch();
    if (window.__ROM_B64__ && window.__ROM_B64__.length) {
      try { startRom(b64ToBytes(window.__ROM_B64__), window.__ROM_NAME__ || "game.gba"); }
      catch (e) { showOverlay("Could not start the built-in ROM: " + e.message); }
    } else {
      showOverlay('No ROM built in. Tap "Open ROM" to choose a .gba file.');
    }
  }

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
