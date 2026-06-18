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

; Ask a question when the ENEMY attacks too? 1 = yes (answer to defend), 0 = no
; (questions only on YOUR attacks -> fewer, faster battles for young kids).
DEF QUIZ_ASK_ON_DEFENSE EQU 1

; Kinder stakes on defence: 1 = a correct answer HALVES the incoming hit (reward)
; and a wrong one just takes normal damage; 0 = old behaviour (a wrong answer
; lets the enemy land a doubled critical hit).
DEF QUIZ_SOFT_DEFENSE EQU 1

