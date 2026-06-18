#!/usr/bin/env python3
# Audits the offline player (build_player.py) for two bug CLASSES that bit us
# this session and that the ROM/headless tests can't catch:
#
#   1. ADDRESS DRIFT: the player hardcodes Game Boy RAM addresses (to read quiz
#      state, etc.). If a WRAM change shifts a symbol, those reads silently point
#      at the wrong byte (this broke the streak feedback + report card). We assert
#      every hardcoded address still matches pokered.sym.
#
#   2. UNSAFE EMULATOR WRITES: writing to the cartridge's MBC control registers
#      ($0000-$7FFF) on the LIVE emulator races with the game's own bank-switching
#      (sprite decompression, saving) -- this corrupted the title sprite and risked
#      the save. We flag any _emulator_write_mem to an address below $8000.
#
# Run:  python3 audit_player.py
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYER = os.path.join(HERE, "build_player.py")
SYM = os.path.join(HERE, "..", "pokered", "pokered.sym")

src = open(PLAYER, encoding="utf-8").read()

# bank:addr name  (e.g. "00:def0 wQuizStreak", "01:a000 sQuizFocus")
sym, symbank = {}, {}
for line in open(SYM, encoding="utf-8"):
    m = re.match(r"\s*([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)\s*$", line)
    if m:
        sym[m.group(3)] = int(m.group(2), 16)
        symbank[m.group(3)] = int(m.group(1), 16)

# The contract: every RAM address the player hardcodes, with the symbol it means.
# (Verified against pokered.sym; also must still appear literally in the player.)
CONTRACT = {
    "wIsInBattle": 0xd057, "wTrainerClass": 0xd031, "wCurOpponent": 0xd059,
    "wGymLeaderNo": 0xd05c, "wBattleResult": 0xcf0b, "wCurMap": 0xd35e,
    "wCurMapTileset": 0xd367, "wChannelSoundIDs": 0xc026, "wAudioROMBank": 0xc0ef,
    "wObtainedBadges": 0xd356, "wQuizStreak": 0xdef0, "wQuizLastSubject": 0xdef4,
    "wQuizQStr": 0xda92, "wQuizA0": 0xdaa6, "wQuizNumAnswers": 0xdee7,
    "wQuizRotate": 0xdeea,
}

fails = 0
def check(name, cond, detail=""):
    global fails
    print(f"{'PASS' if cond else 'FAIL'}  {name}{'  (' + detail + ')' if detail else ''}")
    if not cond:
        fails += 1

print("-- hardcoded RAM addresses match pokered.sym + appear in the player --")
for name, addr in CONTRACT.items():
    in_sym = sym.get(name)
    check(f"{name} == 0x{addr:04x}", in_sym == addr, f"sym=0x{in_sym:04x}" if in_sym is not None else "missing from sym")
    check(f"player still references 0x{addr:04x} ({name})", f"0x{addr:04x}" in src.lower())

# The picker reaches sQuizFocus via SRAM flat offset 0x2000 (= bank 1 * 0x2000).
print("\n-- SRAM focus byte is where the player expects (bank 1, $A000 -> flat 0x2000) --")
fb = symbank.get("sQuizFocus"); fa = sym.get("sQuizFocus")
flat = (fb * 0x2000 + (fa - 0xa000)) if (fb is not None and fa is not None) else None
check("sQuizFocus flat offset == 0x2000", flat == 0x2000,
      f"bank={fb} addr=0x{fa:04x} -> flat=0x{flat:04x}" if flat is not None else "sQuizFocus missing")
check("player writes the focus at 0x2000", "0x2000" in src or "0x2001" in src)

# The quiz scratch intentionally overlays the current PC box (so battles render
# correctly -- the box isn't touched mid-battle; putting it on a screen buffer
# instead garbled the on-screen question/answers). That overlay is only SAFE
# because the box is reloaded from its SRAM copy after every battle, so the
# overworld / "SOMEONE's PC" / saving always see a valid box. Assert that the
# protective routine is actually present in the build.
print("\n-- quiz/box overlay is protected by a post-battle box reload --")
check("RefreshCurBoxFromSRAM is built into the ROM (reloads the box after battle)",
      "RefreshCurBoxFromSRAM" in sym,
      "missing -- the quiz/box overlay would be unsafe without it")

# The quiz strings must NEVER live on the battle's screen-backup buffers
# (wTileMapBackup / wSurroundingTiles, the "Buffer1" the battle engine reuses
# constantly). Putting them there shredded the on-screen question/answers.
print("\n-- quiz strings do NOT overlap the battle screen buffer (Buffer1) --")
SCREEN_AREA = 20 * 18
buf = sym.get("wTileMapBackup")
qlo, qhi = sym.get("wQuizEntry"), sym.get("wQuizFocusCache")
if buf is None or qlo is None or qhi is None:
    check("quiz + screen-buffer symbols present", False, "missing from sym")
else:
    overlap = not (qhi < buf or qlo >= buf + SCREEN_AREA)
    check(f"quiz scratch [{qlo:#06x},{qhi:#06x}] clear of Buffer1 [{buf:#06x},{buf + SCREEN_AREA:#06x})",
          not overlap, "OVERLAP -> battle text will garble")

print("\n-- no broken emoji escapes --")
# Emoji written as Python \U........ escapes inside the JS RAW strings leak into
# the page as literal text ("U0001F4DA") instead of the emoji (this broke the
# Learn Hub). Real emoji characters must be used in the JS instead.
leaked = re.findall(r"\\U[0-9A-Fa-f]{8}", src)
check("no \\U-style emoji escapes in the player (use real emoji characters)",
      not leaked, f"{len(leaked)} found, e.g. {leaked[0]}" if leaked else "")

print("\n-- MBC safety: no live writes to cartridge control registers ($0000-$7FFF) --")
bad = []
for m in re.finditer(r"_emulator_write_mem\(\s*\w+\s*,\s*(0x[0-9a-fA-F]+)", src):
    a = int(m.group(1), 16)
    if a < 0x8000:
        bad.append(m.group(1))
check("no _emulator_write_mem below 0x8000 (MBC/ROM range)", not bad,
      "found: " + ", ".join(bad) if bad else "")

print(f"\n{'ALL PLAYER-AUDIT CHECKS PASSED' if fails == 0 else str(fails) + ' CHECK(S) FAILED'}")
sys.exit(0 if fails == 0 else 1)
