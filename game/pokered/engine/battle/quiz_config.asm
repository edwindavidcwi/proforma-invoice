; ============================================================================
; Quiz Battle - parent-editable settings
; ----------------------------------------------------------------------------
; Change a number here, then re-run `make` to rebuild the game.
; ============================================================================

; How many tries the player gets per battle question.
; 1 = no second chance.  2 = one gentle hint + retry (recommended for young kids).
DEF QUIZ_MAX_ATTEMPTS EQU 2

; Should the answer cursor wrap around from the bottom back to the top?
; 1 = yes (easier to navigate), 0 = no.
DEF QUIZ_WRAP_MENU EQU 1
