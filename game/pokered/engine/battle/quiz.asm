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
	call QuizSelectQuestion        ; a = bank, hl = entry (in that bank)
	call QuizLoadQuestion          ; copy it into RAM -> hl = wQuizEntry
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
	call QuizLoadQuestion          ; copy chosen question into RAM
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
	call QuizLoadQuestion          ; copy chosen question into RAM
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
; QuizGradeTable entry is 4 bytes: dw listBase, db count, db bank.
; Output: a = data bank, hl = entry address (within that bank).
QuizPickGrade:
	cp 6
	jr c, .capped
	ld a, 5
.capped
	dec a                          ; grade index 0-4
	add a
	add a                          ; idx * 4
	ld c, a
	ld b, 0
	ld hl, QuizGradeTable
	add hl, bc
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a                        ; de = list base (address in the data bank)
	ld a, [hli]
	ld c, a                        ; c = count
	ld a, [hl]
	ld [wQuizDataBank], a          ; data bank
	; pick a random index in [0, count) (guard de and count across Random)
	push de
	push bc
	call Random                    ; a = random byte
	pop bc                         ; c = count
	pop de                         ; de = base
.mod
	cp c
	jr c, .haveIndex
	sub c
	jr .mod
.haveIndex
	; hl = base + index*14
	ld h, d
	ld l, e
	and a
	jr z, .gotEntry
	ld b, a                        ; b = index
	ld de, 14
.addLoop
	add hl, de
	dec b
	jr nz, .addLoop
.gotEntry
	ld a, [wQuizDataBank]
	ret                            ; a = bank, hl = entry

; Copy the chosen question (entry + all its strings) from the data bank into RAM,
; rewriting the entry's pointers to the RAM copies. After this the display code
; runs entirely on RAM and never switches banks. In: a = bank, hl = entry addr.
; Out: hl = wQuizEntry.
QuizLoadQuestion:
	ld [wQuizDataBank], a
	ld de, wQuizEntry
	ld bc, 14
	call FarCopyData               ; bank:hl(entry) -> wQuizEntry
	ld hl, wQuizEntry              ; question text pointer (offset 0)
	ld de, wQuizQStr
	call QuizFixupStr
	ld hl, wQuizEntry + 4          ; answer 0 (offset 4)
	ld de, wQuizA0
	call QuizFixupStr
	ld hl, wQuizEntry + 6
	ld de, wQuizA1
	call QuizFixupStr
	ld hl, wQuizEntry + 8
	ld de, wQuizA2
	call QuizFixupStr
	ld hl, wQuizEntry + 10
	ld de, wQuizA3
	call QuizFixupStr
	ld hl, wQuizEntry + 12         ; hint (offset 12)
	ld de, wQuizHStr
	call QuizFixupStr
	ld hl, wQuizEntry
	ret

; Far-copy one string into RAM and repoint it. In: hl -> 2-byte source pointer
; (inside wQuizEntry), de = RAM destination buffer. Copies a fixed 20 bytes
; (every string is <=19 chars incl. terminator) then rewrites the pointer to de.
QuizFixupStr:
	push hl
	ld a, [hli]
	ld h, [hl]
	ld l, a                        ; hl = source string address (in data bank)
	ld bc, 20
	ld a, [wQuizDataBank]
	push de
	call FarCopyData               ; bank:hl -> de
	pop de                         ; de = destination
	pop hl                         ; hl -> the pointer field
	ld a, e
	ld [hli], a
	ld a, d
	ld [hl], a
	ret

; Ask the question pointed to by hl (14-byte entry).
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
	; Remember the correct answer's text pointer (hl still points at the answer
	; table) so a missed question can reveal the answer and still teach.
	ld a, [wQuizCorrectIndex]
	add a                          ; correct index * 2 (pointers are 2 bytes)
	ld c, a
	ld b, 0
	push hl
	add hl, bc
	ld a, [hli]
	ld [wQuizCorrectAnsPtr], a
	ld a, [hl]
	ld [wQuizCorrectAnsPtr + 1], a
	pop hl
	; Remember the method-hint pointer (entry offset 12 = answer-table base + 8).
	push hl
	ld bc, 8
	add hl, bc
	ld a, [hli]
	ld [wQuizHintPtr], a
	ld a, [hl]
	ld [wQuizHintPtr + 1], a
	pop hl
	; Pick a random rotation k in [0, numAnswers) so the answers appear in a
	; different on-screen order every time -- kids must read and compute the
	; answer instead of memorizing a fixed slot.
	call Random
	ld c, a                        ; c = random byte
	ld a, [wQuizNumAnswers]
	ld b, a                        ; b = n (reloaded after Random in case it clobbers)
	ld a, c
.modK
	cp b
	jr c, .haveK
	sub b
	jr .modK
.haveK
	ld [wQuizRotate], a            ; k in [0, n)
	; The correct answer is shown at display slot (correctIndex + n - k) mod n.
	ld a, [wQuizCorrectIndex]
	ld b, a                        ; b = correct (original index)
	ld a, [wQuizNumAnswers]
	add b                          ; a = n + correct
	ld b, a
	ld a, [wQuizRotate]
	ld c, a                        ; c = k
	ld a, b
	sub c                          ; a = n + correct - k  (in [1, 2n-1])
	ld b, a
	ld a, [wQuizNumAnswers]
	ld c, a                        ; c = n
	ld a, b
	cp c
	jr c, .haveCorrect
	sub c                          ; one subtraction suffices (value < 2n)
.haveCorrect
	ld [wQuizCorrectIndex], a      ; correct index, now in display space
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
	; Wrong, but a try is left: teach the method via the hint, then retry.
	ld a, [wQuizHintPtr]
	ld e, a
	ld a, [wQuizHintPtr + 1]
	ld d, a
	call CopyToStringBuffer        ; wStringBuffer <- hint text
	ld hl, QuizTryAgainText
	call PrintText
	jr .attempt
.correct
	; Bump the answered-in-a-row streak (capped at 99) and show it.
	ld a, [wQuizStreak]
	cp 99
	jr nc, .streakReady
	inc a
	ld [wQuizStreak], a
.streakReady
	call QuizStreakToBuffer        ; wStringBuffer <- streak as text
	ld hl, QuizCorrectText
	call PrintText
	scf
	ret
.failed
	xor a
	ld [wQuizStreak], a            ; a miss breaks the streak
	; Reveal the correct answer so even a missed question teaches the fact.
	ld a, [wQuizCorrectAnsPtr]
	ld e, a
	ld a, [wQuizCorrectAnsPtr + 1]
	ld d, a
	call CopyToStringBuffer        ; wStringBuffer <- correct answer text
	ld hl, QuizMissText
	call PrintText
	and a                          ; clear carry
	ret

; Write wQuizStreak (0-99) as a decimal string into wStringBuffer for display.
QuizStreakToBuffer::
	ld a, [wQuizStreak]
	ld b, 0                        ; b = tens digit
.tens
	cp 10
	jr c, .ones
	sub 10
	inc b
	jr .tens
.ones
	ld c, a                        ; c = ones digit
	ld hl, wStringBuffer
	ld a, b
	and a
	jr z, .noTens
	add CHARVAL("0")               ; tens digit (skip a leading zero)
	ld [hli], a
.noTens
	ld a, c
	add CHARVAL("0")               ; ones digit
	ld [hli], a
	ld [hl], CHARVAL("@")          ; string terminator
	ret

; Draw the question box, the question, the answers, and prime the menu.
QuizDrawScreen::
	ldh a, [hUILayoutFlags]
	res BIT_DOUBLE_SPACED_MENU, a  ; cursor steps 2 rows, matching answers placed
	ldh [hUILayoutFlags], a        ; on every other row (see QuizPrintAnswers)
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

; Print the answers down the left of the box, double-spaced from row 9, in the
; rotated order chosen in QuizAsk: display slot s shows the original answer at
; index (s + wQuizRotate) mod numAnswers.
QuizPrintAnswers::
	xor a
	ld [wQuizSlot], a              ; start at display slot 0
	hlcoord 2, 9                   ; hl = destination tile for slot 0
.loop
	ld a, [wQuizSlot]
	ld b, a                        ; b = slot
	ld a, [wQuizNumAnswers]
	cp b
	ret z                          ; printed every slot -> done
	; original answer index o = (slot + k) mod n
	ld a, [wQuizRotate]
	add b                          ; k + slot
	ld c, a
	ld a, [wQuizNumAnswers]
	ld b, a                        ; b = n
	ld a, c
.mod
	cp b
	jr c, .haveIndex
	sub b
	jr .mod
.haveIndex
	add a                          ; o * 2 (answer pointers are 2 bytes)
	ld c, a
	ld b, 0
	push hl                        ; save destination
	ld a, [wQuizAnswersPtr]
	ld l, a
	ld a, [wQuizAnswersPtr + 1]
	ld h, a
	add hl, bc                     ; hl -> chosen answer pointer
	ld a, [hli]
	ld e, a
	ld a, [hl]
	ld d, a                        ; de = answer string
	pop hl                         ; restore destination
	push hl                        ; keep it across PlaceString
	call PlaceString
	pop hl
	ld de, 2 * SCREEN_WIDTH        ; advance two rows (double spaced)
	add hl, de
	ld a, [wQuizSlot]
	inc a
	ld [wQuizSlot], a
	jr .loop

INCLUDE "engine/battle/quiz_data.asm"
