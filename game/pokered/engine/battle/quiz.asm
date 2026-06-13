; ============================================================================
; Quiz Battle - core engine
; ----------------------------------------------------------------------------
; Shows a multiple-choice question, scaled to the player's progress (badge
; count -> grade 1-5), and reports whether it was answered correctly.  Used by
; the battle hooks in engine/battle/core.asm.
;
; This lives in its own ROM bank and is reached with `callfar` from the battle
; engine, so question text (in this same bank) is always paged in while we run.
; ============================================================================

INCLUDE "engine/battle/quiz_config.asm"

; Player attacked: ask a grade-scaled question.
; Correct answer -> the move hits.  Wrong (after retries) -> the move misses.
; Clobbers all registers (safe at the HandleIfPlayerMoveMissed hook).
QuizPlayerAttack::
	call SaveScreenTilesToBuffer2
	call QuizSelectQuestion        ; hl = chosen question entry
	call QuizAsk                   ; carry set = answered correctly
	push af
	call LoadScreenTilesFromBuffer2
	call Delay3
	pop af
	jr nc, .miss
	xor a                          ; correct -> wMoveMissed = 0 (hit)
	ld [wMoveMissed], a
	ret
.miss
	ld a, $01                      ; wrong -> wMoveMissed = 1 (miss)
	ld [wMoveMissed], a
	ret

; Enemy is attacking: ask a grade-scaled question to defend.
; Correct -> the enemy hits normally.  Wrong -> force a doubled critical hit.
; Only triggers for damaging moves (power > 0).
QuizEnemyDefense::
	ld a, [wEnemyMovePower]
	and a
	ret z                          ; status move: nothing to defend against
	call SaveScreenTilesToBuffer2
	call QuizSelectQuestion
	call QuizAsk                   ; carry set = answered correctly
	push af
	call LoadScreenTilesFromBuffer2
	call Delay3
	pop af
	ret c                          ; correct -> leave damage as the game rolled it
	; wrong -> make sure the hit lands, flag a critical hit, and double the damage
	xor a
	ld [wMoveMissed], a
	ld a, $01
	ld [wCriticalHitOrOHKO], a
	ld hl, wDamage + 1             ; wDamage is stored high byte first
	ld a, [hl]
	add a
	ld [hld], a
	ld a, [hl]
	adc a
	ld [hl], a
	ret nc
	ld a, $ff                      ; cap at 0xFFFF (clamped to HP downstream)
	ld [hli], a
	ld [hl], a
	ret

; Player wants to use a bag item in battle: ask a question scaled to the
; active Pokemon's level.  Sets wQuizResult to 1 (allow) or 0 (deny).
; The battle engine skips UseItem on a deny, so the item is not consumed.
QuizItemUse::
	call SaveScreenTilesToBuffer2
	call QuizSelectByLevel
	call QuizAsk
	push af
	call LoadScreenTilesFromBuffer2
	call Delay3
	pop af
	jr nc, .deny
	ld a, $01
	ld [wQuizResult], a
	ret
.deny
	xor a
	ld [wQuizResult], a
	ret

; Choose a question scaled to the player's badges (used by battle attack/defense).
; Grade = min(5, badgeCount / 2 + 1).  Returns hl -> 12-byte question entry.
QuizSelectQuestion::
	ld hl, wObtainedBadges
	ld b, 1
	call CountSetBits              ; -> [wNumSetBits]
	ld a, [wNumSetBits]
	srl a                          ; badges / 2
	inc a                          ; + 1
	jr QuizPickGrade

; Choose a question scaled to the active Pokemon's level (used by item use).
; Grade rises every 10 levels: Lv<=10 -> 1, <=20 -> 2, ... Lv 41+ -> 5.
QuizSelectByLevel::
	ld a, [wBattleMonLevel]
	ld b, 1
	cp 11
	jr c, .got
	inc b
	cp 21
	jr c, .got
	inc b
	cp 31
	jr c, .got
	inc b
	cp 41
	jr c, .got
	inc b
.got
	ld a, b
	; fall through

; Pick a random question from grade `a` (1-based, clamped to 5).
; Returns hl -> 12-byte question entry.
QuizPickGrade:
	cp 6
	jr c, .capped
	ld a, 5
.capped
	dec a                          ; grade index 0-4
	; entry in QuizGradeTable is 3 bytes: dw listPtr, db count -> offset = idx*3
	ld c, a
	add a                          ; idx*2
	add c                          ; idx*3
	ld c, a
	ld b, 0
	ld hl, QuizGradeTable
	add hl, bc
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a                        ; de = list base
	ld a, [hl]                     ; a = number of questions in this grade
	ld c, a                        ; c = count
	; pick a random index in [0, count)
	call Random                    ; a = random byte
.mod
	cp c
	jr c, .haveIndex
	sub c
	jr .mod
.haveIndex
	; hl = de + index*12
	ld h, d
	ld l, e
	and a
	ret z                          ; index 0 -> first entry
	ld b, a                        ; b = index
	ld de, 12
.addLoop
	add hl, de
	dec b
	jr nz, .addLoop
	ret

; Ask the question pointed to by hl (12-byte entry).
; Returns carry set if answered correctly, carry clear if not (after retries).
QuizAsk::
	ld a, [hli]
	ld [wQuizQuestionText], a
	ld a, [hli]
	ld [wQuizQuestionText + 1], a
	ld a, [hli]
	ld [wQuizCorrectIndex], a
	ld a, [hli]
	ld [wQuizNumAnswers], a
	ld a, l
	ld [wQuizAnswersPtr], a
	ld a, h
	ld [wQuizAnswersPtr + 1], a
	ld a, QUIZ_MAX_ATTEMPTS
	ld [wQuizAttemptsLeft], a
.attempt
	call QuizDrawScreen
	call HandleMenuInput           ; only A is watched; selection -> wCurrentMenuItem
	ld a, [wCurrentMenuItem]
	ld hl, wQuizCorrectIndex
	cp [hl]
	jr z, .correct
	ld hl, wQuizAttemptsLeft
	dec [hl]
	jr z, .failed
	ld hl, QuizTryAgainText
	call PrintText
	jr .attempt
.correct
	ld hl, QuizCorrectText
	call PrintText
	scf
	ret
.failed
	ld hl, QuizMissText
	call PrintText
	and a                          ; clear carry
	ret

; Draw the question box, the question, the answers, and prime the menu.
QuizDrawScreen::
	ldh a, [hUILayoutFlags]
	set BIT_DOUBLE_SPACED_MENU, a  ; answers on every other row, easier to read
	ldh [hUILayoutFlags], a
	hlcoord 0, 6
	ld b, 10
	ld c, 18
	call TextBoxBorder
	hlcoord 1, 7
	ld a, [wQuizQuestionText]
	ld e, a
	ld a, [wQuizQuestionText + 1]
	ld d, a
	call PlaceString
	call QuizPrintAnswers
	ld a, 9
	ld [wTopMenuItemY], a
	ld a, 1
	ld [wTopMenuItemX], a
	xor a
	ld [wCurrentMenuItem], a
	ld [wLastMenuItem], a
	ld a, [wQuizNumAnswers]
	dec a
	ld [wMaxMenuItem], a
	ld a, PAD_A
	ld [wMenuWatchedKeys], a
	ld a, QUIZ_WRAP_MENU
	ld [wMenuWrappingEnabled], a
	ret

; Print up to 4 answers down the left of the box, double-spaced from row 9.
QuizPrintAnswers::
	ld a, [wQuizAnswersPtr]
	ld c, a
	ld a, [wQuizAnswersPtr + 1]
	ld b, a                        ; bc = pointer into the answer table
	ld a, [wQuizNumAnswers]
	hlcoord 2, 9                   ; hl = destination tile
.loop
	and a
	ret z
	dec a
	push af                        ; save remaining count
	push hl                        ; save destination
	ld a, [bc]
	inc bc
	ld e, a
	ld a, [bc]
	inc bc
	ld d, a                        ; de = answer string
	push bc                        ; save table cursor across PlaceString
	call PlaceString
	pop bc
	pop hl
	ld de, 2 * SCREEN_WIDTH        ; advance two rows (double spaced)
	add hl, de
	pop af
	jr .loop

INCLUDE "engine/battle/quiz_data.asm"
