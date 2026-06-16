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
	call QuizStreakDamageBonus     ; the longer the first-try streak, the harder the hit
	ret
.miss
	ld a, $01                      ; wrong -> wMoveMissed = 1 (miss)
	ld [wMoveMissed], a
	ret

; Reward a mastery streak with extra attack power. Called only on a correct
; answer (the move lands), with wDamage already calculated by the battle engine.
; New damage = damage * (8 + min(streak,8)) / 8  -> up to 2x at an 8+ streak.
QuizStreakDamageBonus:
	ld a, [wQuizStreak]
	and a
	ret z                          ; no streak -> normal damage
	cp 9
	jr c, .haveMul
	ld a, 8                        ; cap the bonus (max +8/8 = double damage)
.haveMul
	add 8                          ; multiplier = 8 + min(streak,8)  (9..16)
	ldh [hMultiplier], a
	xor a
	ldh [hMultiplicand], a
	ld a, [wDamage]                ; damage high byte (wDamage is big-endian)
	ldh [hMultiplicand + 1], a
	ld a, [wDamage + 1]            ; damage low byte
	ldh [hMultiplicand + 2], a
	call Multiply                  ; hProduct = damage * multiplier
	ld a, 8
	ldh [hDivisor], a
	ld b, 4
	call Divide                    ; hQuotient = product / 8
	ldh a, [hQuotient]             ; bytes 0-1 must be 0, else result > 0xFFFF
	ld b, a
	ldh a, [hQuotient + 1]
	or b
	jr nz, .clamp
	ldh a, [hQuotient + 2]
	ld [wDamage], a                ; boosted damage high
	ldh a, [hQuotient + 3]
	ld [wDamage + 1], a            ; boosted damage low
	ret
.clamp
	ld a, $ff                      ; clamp to 0xFFFF (HP-capped downstream)
	ld [wDamage], a
	ld [wDamage + 1], a
	ret

; Enemy is attacking: optionally ask a grade-scaled question to defend.
; Behaviour is set in quiz_config.asm (QUIZ_ASK_ON_DEFENSE / QUIZ_SOFT_DEFENSE).
; Only triggers for damaging moves (power > 0).
QuizEnemyDefense::
	ld a, [wEnemyMovePower]
	and a
	ret z                          ; status move: nothing to defend against
IF QUIZ_ASK_ON_DEFENSE != 0
	call SaveScreenTilesToBuffer2
	call QuizSelectQuestion
	call QuizLoadQuestion          ; copy chosen question into RAM
	call QuizAsk                   ; carry set = answered correctly
	push af
	call LoadScreenTilesFromBuffer2
	call Delay3
	pop af
	jr nc, .wrong
	; correct
IF QUIZ_SOFT_DEFENSE != 0
	; reward a good defence: halve the incoming damage (16-bit, high byte first)
	ld hl, wDamage
	ld a, [hl]
	srl a
	ld [hli], a
	ld a, [hl]
	rra
	ld [hl], a
ENDC
	ret                            ; (otherwise leave damage as the game rolled it)
.wrong
IF QUIZ_SOFT_DEFENSE != 0
	ret                            ; soft: a wrong answer just takes normal damage
ELSE
	; make sure the hit lands, flag a critical hit, and double the damage
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
ENDC
ENDC
	ret                            ; QUIZ_ASK_ON_DEFENSE == 0: normal damage, no quiz

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

; Catching a wild Pokemon: the player must answer N questions in a row
; (3 for grades 1-2, 5 for grades 3-5). A miss lets the Pokemon escape.
; Sets wQuizResult (1 = caught, 0 = escaped) -- the flag survives the callfar
; back to ItemUseBall (the carry flag would not).
QuizCapture::
	call SaveScreenTilesToBuffer2
	; required streak length, by grade (badge count / 2 + 1)
	ld hl, wObtainedBadges
	ld b, 1
	call CountSetBits
	ld a, [wNumSetBits]
	srl a
	inc a                          ; a = grade (1-5)
	cp 3
	ld a, 3                        ; grades 1-2 -> need 3
	jr c, .gotNeed
	ld a, 5                        ; grades 3-5 -> need 5
.gotNeed
	ld [wQuizCapNeed], a
	xor a
	ld [wQuizCapCount], a
.ask
	call QuizSelectQuestion
	call QuizLoadQuestion
	call QuizAsk                   ; carry set = answered correctly
	ld a, [wQuizFirstTry]          ; capture requires FIRST-TRY correct (anti-luck)
	and a
	jr z, .escaped                 ; wrong, or right only after a hint -> it escapes
	ld a, [wQuizCapCount]
	inc a
	ld [wQuizCapCount], a
	ld hl, wQuizCapNeed
	cp [hl]
	jr c, .ask                     ; streak < needed -> ask another
	ld a, 1                        ; full streak -> caught
	ld [wQuizResult], a
	jr .done
.escaped
	xor a
	ld [wQuizResult], a
.done
	call LoadScreenTilesFromBuffer2
	call Delay3
	ret

; Player wants to flee a wild battle: ask a grade-scaled question.
; Returns carry set = answered correctly (allow the escape attempt),
; carry clear = wrong (caller makes the escape fail and spends the turn).
QuizRun::
	call SaveScreenTilesToBuffer2
	call QuizSelectQuestion
	call QuizLoadQuestion           ; copy chosen question into RAM
	call QuizAsk                    ; carry set = answered correctly
	push af
	call LoadScreenTilesFromBuffer2
	call Delay3
	pop af
	ret

; A no-stakes practice question for the Professor's Assistant tutor (reached from
; the overworld, not a battle). Shows one grade-scaled question with the normal
; hint/answer/streak feedback, then restores the screen. No hit/miss effect.
QuizPractice::
	call SaveScreenTilesToBuffer2
	call ClearSprites              ; hide overworld sprites (player/NPCs) during the quiz
	call ClearScreen               ; blank the background so the quiz box sits on a clean screen
	call QuizSelectQuestion
	call QuizLoadQuestion
	call QuizAsk
	call LoadScreenTilesFromBuffer2
	call Delay3
	ret

; Choose a question scaled to the player's badges (used by battle attack/defense).
; Grade = min(5, badgeCount / 2 + 1).  Returns hl -> 12-byte question entry.
QuizSelectQuestion::
	; Spaced repetition: when there are recently-missed questions, sometimes
	; (~1 in 3) re-ask one instead of a fresh question. Mastered questions are
	; removed from the ring (see QuizReviewRemove), so they stop coming back.
	ld a, [wQuizReviewFilled]
	and a
	jr z, .newQuestion
	cp 5
	jr nc, .newQuestion            ; stale/garbage count -> ignore the ring
	call Random
	cp 85                          ; ~33% review, ~67% a fresh question
	jr nc, .newQuestion
	ld a, [wQuizReviewFilled]
	ld b, a                        ; b = filled count (1-4)
	call Random
.modReview
	cp b
	jr c, .gotReview
	sub b
	jr .modReview
.gotReview
	add a                           ; ring index * 2
	ld c, a
	ld b, 0
	ld hl, wQuizReviewRing
	add hl, bc
	ld a, [hli]
	cp 5
	jr nc, .newQuestion            ; bad grade index -> fall back to a new question
	ld [wQuizGradeIdx], a
	ld a, [hl]
	ld [wQuizPickIdx], a
	; validate index < this grade's question count (guards stale overlay data)
	ld a, [wQuizGradeIdx]
	add a
	add a
	ld c, a
	ld b, 0
	ld hl, QuizGradeTable + 2      ; count byte of grade entry 0
	add hl, bc
	ld a, [wQuizPickIdx]
	cp [hl]
	jr nc, .newQuestion            ; index out of range -> new question
	jp QuizEntryFromIdx             ; load that exact question
.newQuestion
	ld hl, wObtainedBadges
	ld b, 1
	call CountSetBits              ; -> [wNumSetBits]
	ld a, [wNumSetBits]
	srl a                          ; badges / 2
	inc a                          ; + 1
	jp QuizPickGrade

; Compute a question entry from wQuizGradeIdx + wQuizPickIdx (used by review).
; Out: a = data bank, hl = entry address, wQuizDataBank set.
QuizEntryFromIdx:
	ld a, [wQuizGradeIdx]
	add a
	add a                          ; idx * 4
	ld c, a
	ld b, 0
	ld hl, QuizGradeTable
	add hl, bc
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a                        ; de = list base
	inc hl                         ; skip count byte
	ld a, [hl]
	ld [wQuizDataBank], a          ; data bank
	ld h, d
	ld l, e                        ; hl = base
	ld a, [wQuizPickIdx]
	and a
	jr z, .done
	ld b, a
	ld de, 18                      ; question entry size (must match QuizPickGrade / quizq)
.loop
	add hl, de
	dec b
	jr nz, .loop
.done
	ld a, [wQuizDataBank]
	ret

; ---- spaced-repetition ring (linear array of up to 4 distinct missed
; questions). A miss adds one; answering it correctly removes it, so a mastered
; question stops coming back. ----

; Search the ring for (wQuizGradeIdx, wQuizPickIdx) among the first wQuizReviewFilled
; entries. Out: carry set + b = its index if found; carry clear otherwise.
QuizReviewFind:
	ld a, [wQuizReviewFilled]
	cp 5
	jr c, .lenOk
	xor a                          ; stale/garbage count -> reset to empty
	ld [wQuizReviewFilled], a
.lenOk
	and a
	ret z                          ; empty -> not found (carry clear)
	ld c, a                        ; c = count
	ld b, 0                        ; b = index
	ld hl, wQuizReviewRing
	ld a, [wQuizGradeIdx]
	ld e, a                        ; e = target grade
	ld a, [wQuizPickIdx]
	ld d, a                        ; d = target index
.scan
	ld a, [hli]                    ; grade
	cp e
	jr nz, .miss
	ld a, [hl]                     ; index
	cp d
	jr z, .hit
.miss
	inc hl                         ; step past index byte to next entry
	inc b
	dec c
	jr nz, .scan
	and a                          ; not found -> clear carry
	ret
.hit
	scf
	ret

; Add the current question to the review ring (deduped; drops the oldest if full).
QuizReviewPush:
	call QuizReviewFind
	ret c                          ; already queued -> don't duplicate
	ld a, [wQuizReviewFilled]
	cp 4
	jr c, .append
	ld hl, wQuizReviewRing         ; full -> shift entries 1..3 down to 0..2
	ld de, wQuizReviewRing + 2
	ld c, 6
.drop
	ld a, [de]
	ld [hli], a
	inc de
	dec c
	jr nz, .drop
	ld a, 3
	ld [wQuizReviewFilled], a
.append
	ld a, [wQuizReviewFilled]
	add a
	ld l, a
	ld h, 0
	ld de, wQuizReviewRing
	add hl, de
	ld a, [wQuizGradeIdx]
	ld [hli], a
	ld a, [wQuizPickIdx]
	ld [hl], a
	ld hl, wQuizReviewFilled
	inc [hl]
	ret

; Remove the current question from the ring (called when it's answered correctly).
QuizReviewRemove:
	call QuizReviewFind
	ret nc                         ; not queued -> nothing to do
	ld a, [wQuizReviewFilled]
	dec a
	ld [wQuizReviewFilled], a      ; new count
	sub b                          ; entries after the removed one
	ret z                          ; it was the last -> done
	ld c, a
	sla c                          ; bytes to shift down
	ld a, b
	add a
	ld l, a
	ld h, 0
	ld de, wQuizReviewRing
	add hl, de                     ; hl = removed slot
	ld d, h
	ld e, l
	inc de
	inc de                         ; de = next slot
.shift
	ld a, [de]
	ld [hli], a
	inc de
	dec c
	jr nz, .shift
	ret

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
	ld [wQuizGradeIdx], a
	add a
	add a                          ; idx * 4
	ld c, a
	ld b, 0
	ld hl, QuizGradeTable
	add hl, bc
	ld a, [hli]
	ld [wQuizPickBase], a
	ld a, [hli]
	ld [wQuizPickBase + 1], a       ; list base (address in the data bank)
	ld a, [hli]
	ld [wQuizPickCount], a          ; count
	ld a, [hl]
	ld [wQuizDataBank], a           ; data bank
	; this grade's subject-array base (in this same bank as QuizGradeTable)
	ld a, [wQuizGradeIdx]
	add a                           ; idx * 2
	ld e, a
	ld d, 0
	ld hl, QuizSubjectTable
	add hl, de
	ld a, [hli]
	ld [wQuizSubjBase], a
	ld a, [hl]
	ld [wQuizSubjBase + 1], a
	; pick an index whose subject differs from the previous question (<=4 tries)
	ld a, 4
	ld [wQuizPickTries], a
.pick
	ld a, [wQuizPickCount]
	ld b, a                         ; b = count
	call Random                     ; a = random byte
.mod
	cp b
	jr c, .haveIndex
	sub b
	jr .mod
.haveIndex
	ld [wQuizPickIdx], a
	; subject id of this candidate = [wQuizSubjBase + index]
	ld a, [wQuizSubjBase]
	ld l, a
	ld a, [wQuizSubjBase + 1]
	ld h, a
	ld a, [wQuizPickIdx]
	ld e, a
	ld d, 0
	add hl, de
	ld a, [hl]                      ; a = candidate subject id
	ld hl, wQuizLastSubject
	cp [hl]
	jr nz, .accept                  ; different subject -> take it
	ld hl, wQuizPickTries
	dec [hl]
	jr nz, .pick                    ; same subject, retry
.accept
	ld [wQuizLastSubject], a        ; a still holds the chosen subject id
	; hl = base + index*14
	ld a, [wQuizPickBase]
	ld l, a
	ld a, [wQuizPickBase + 1]
	ld h, a
	ld a, [wQuizPickIdx]
	and a
	jr z, .gotEntry
	ld b, a                         ; b = index
	ld de, 18
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
	ld bc, 18
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
	ld hl, wQuizEntry + 12
	ld de, wQuizA4
	call QuizFixupStr
	ld hl, wQuizEntry + 14
	ld de, wQuizA5
	call QuizFixupStr
	ld hl, wQuizEntry + 16         ; hint (offset 16)
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
	; Remember the method-hint pointer (entry offset 16 = answer-table base + 12).
	push hl
	ld bc, 12
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
	; The overworld/battle flow may leave "don't wait after text" set; clear it so
	; the hint and the answer-reveal always pause for the player to read them.
	xor a
	ld [wDoNotWaitForButtonPressAfterDisplayingText], a
.attempt
	call QuizDrawScreen
	call QuizGridInput             ; 2-column grid; selection (absolute slot) -> wCurrentMenuItem
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
	; Real-mastery / anti-luck rule: only a FIRST-TRY correct answer builds the
	; streak. Getting it right only after a wrong guess (hint shown) earns no
	; streak credit and breaks the streak -- guessing can't fake progress.
	ld a, [wQuizAttemptsLeft]
	cp QUIZ_MAX_ATTEMPTS            ; still full == no wrong attempt yet == first try
	jr z, .firstTry
	xor a
	ld [wQuizStreak], a            ; correct only after a miss -> streak resets
	ld [wQuizFirstTry], a
	call QuizReviewRemove          ; answered right (with help) -> stop reviewing it
	jr .streakReady
.firstTry
	call QuizReviewRemove          ; mastered first-try -> stop reviewing it
	ld a, 1
	ld [wQuizFirstTry], a
	ld a, [wQuizStreak]
	cp 99
	jr nc, .streakReady
	inc a
	ld [wQuizStreak], a
	cp 8                           ; just reached x2.0 -> MAX POWER!
	jr z, .maxPower
	cp 4                           ; just reached x1.5 -> POWER UP!
	jr z, .powerUp
.streakReady
	call QuizStreakToBuffer        ; wStringBuffer <- "streak  xN.N"
	ld hl, QuizCorrectText
	jr .showCorrect
.powerUp
	call QuizStreakToBuffer
	ld hl, QuizPowerUpText
	jr .showCorrect
.maxPower
	call QuizStreakToBuffer
	ld hl, QuizMaxPowerText
.showCorrect
	call PrintText
	scf
	ret
.failed
	xor a
	ld [wQuizStreak], a            ; a miss breaks the streak
	ld [wQuizFirstTry], a
	call QuizReviewPush            ; missed -> queue for spaced-repetition review
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

; Write the streak and the current attack-power multiplier into wStringBuffer,
; e.g. "4  x1.5" -- shown as "Streak 4  x1.5". The multiplier matches the damage
; bonus in QuizStreakDamageBonus: (8 + min(streak,8)) / 8, in tenths (1.0 .. 2.0).
QuizStreakToBuffer::
	ld hl, wStringBuffer
	ld a, [wQuizStreak]
	call QuizPutDec                ; streak number
	ld a, CHARVAL(" ")
	ld [hli], a
	ld a, CHARVAL("x")
	ld [hli], a
	; multiplier in tenths T = (8 + min(streak,8)) * 5 / 4   (range 10..20)
	ld a, [wQuizStreak]
	cp 9
	jr c, .cap
	ld a, 8
.cap
	add 8                          ; n = 8 + min(streak,8)
	ld b, a
	add a
	add a                          ; n*4
	add b                          ; n*5
	srl a
	srl a                          ; (n*5)/4 = T
	; ones = T/10 (1 or 2), tenth = T mod 10
	ld c, 0
.tens
	cp 10
	jr c, .haveOnes
	sub 10
	inc c
	jr .tens
.haveOnes
	ld b, a                        ; b = tenths digit
	ld a, c
	add CHARVAL("0")               ; whole part
	ld [hli], a
	ld a, CHARVAL(".")
	ld [hli], a
	ld a, b
	add CHARVAL("0")               ; tenths
	ld [hli], a
	ld [hl], CHARVAL("@")
	ret

; Write a (0-99) as a decimal string to [hl] (no leading zero), advancing hl.
QuizPutDec:
	ld c, 0
.tens
	cp 10
	jr c, .ones
	sub 10
	inc c
	jr .tens
.ones
	ld b, a                        ; ones
	ld a, c
	and a
	jr z, .skipTens
	add CHARVAL("0")
	ld [hli], a
.skipTens
	ld a, b
	add CHARVAL("0")
	ld [hli], a
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
	xor a                          ; start at the top of the left column
	ld [wQuizCol], a
	ld [wCurrentMenuItem], a
	ld [wLastMenuItem], a
	ret

; Answers fill two columns to use the space and allow up to 6 options. Display
; slot s (in the rotated order from QuizAsk) goes to the left column for the
; first ceil(n/2) slots, otherwise the right column; rows are double-spaced from
; row 8. Left text at col 2 (cursor col 1); right text at col 11 (cursor col 10).
QuizPrintAnswers::
	xor a
	ld [wQuizSlot], a              ; start at display slot 0
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
	ld a, [wQuizAnswersPtr]
	ld l, a
	ld a, [wQuizAnswersPtr + 1]
	ld h, a
	add hl, bc                     ; hl -> chosen answer pointer
	ld a, [hli]
	ld e, a
	ld a, [hl]
	ld d, a                        ; de = answer string
	push de                        ; save string pointer across the layout math
	; destination = base(col) + row * 2 rows.  leftN = (n + 1) / 2.
	ld a, [wQuizNumAnswers]
	inc a
	srl a
	ld c, a                        ; c = leftN
	ld a, [wQuizSlot]
	cp c
	jr c, .leftCol
	sub c                          ; row = slot - leftN
	ld b, a                        ; b = row
	hlcoord 11, 8                  ; right column base
	jr .addRows
.leftCol
	ld b, a                        ; b = row = slot
	hlcoord 2, 8                   ; left column base
.addRows
	ld a, b
	and a
	jr z, .place
	ld de, 2 * SCREEN_WIDTH
.rowLoop
	add hl, de
	dec b
	jr nz, .rowLoop
.place
	pop de                         ; de = answer string
	call PlaceString
	ld a, [wQuizSlot]
	inc a
	ld [wQuizSlot], a
	jr .loop

; Two-column answer selection. Up/Down move within a column (HandleMenuInput);
; Left/Right switch columns. Returns the chosen ABSOLUTE slot in wCurrentMenuItem
; (so it can be compared to wQuizCorrectIndex). Only A confirms -- no B escape.
QuizGridInput::
.loop
	call QuizSetupColumnCursor
	call HandleMenuInput           ; handles Up/Down; returns pressed watched keys in a
	bit B_PAD_A, a
	jr nz, .confirm
	ld b, a                        ; b = pressed keys
	ld a, [wQuizNumAnswers]
	inc a
	srl a
	ld c, a                        ; c = leftN
	bit B_PAD_LEFT, b
	jr nz, .toLeft
	bit B_PAD_RIGHT, b
	jr z, .loop                    ; neither A/Left/Right (e.g. input timeout) -> keep waiting
	; Right pressed: move to the right column (if not already there).
	ld a, [wQuizCol]
	and a
	jr nz, .loop
	call EraseMenuCursor           ; remove the left arrow before drawing the right one
	ld a, 1
	ld [wQuizCol], a
	ld a, [wQuizNumAnswers]
	sub c                          ; rightN
	dec a                          ; max row in right column
	jr .clamp
.toLeft
	; Left pressed: move to the left column (if not already there).
	ld a, [wQuizCol]
	and a
	jr z, .loop
	call EraseMenuCursor           ; remove the right arrow before drawing the left one
	xor a
	ld [wQuizCol], a
	ld a, c                        ; leftN
	dec a                          ; max row in left column
.clamp
	ld b, a                        ; b = max row in the new column
	ld a, [wCurrentMenuItem]
	cp b
	jr c, .clamped
	ld a, b                        ; clamp the row to the new column's last item
.clamped
	ld [wCurrentMenuItem], a
	ld [wLastMenuItem], a
	jr .loop
.confirm
	; absolute slot = row, plus leftN if we're in the right column
	ld a, [wQuizCol]
	and a
	ret z
	ld a, [wQuizNumAnswers]
	inc a
	srl a
	ld b, a                        ; leftN
	ld a, [wCurrentMenuItem]
	add b
	ld [wCurrentMenuItem], a
	ret

; Point HandleMenuInput at the current column: cursor X (1 = left, 10 = right),
; top row 8, and the number of items in that column.
QuizSetupColumnCursor::
	ld a, 8
	ld [wTopMenuItemY], a
	ld a, [wQuizCol]
	and a
	ld a, 1                        ; left cursor column
	jr z, .haveX
	ld a, 10                       ; right cursor column
.haveX
	ld [wTopMenuItemX], a
	ld a, [wQuizNumAnswers]
	inc a
	srl a
	ld b, a                        ; leftN
	ld a, [wQuizCol]
	and a
	jr z, .leftCount
	ld a, [wQuizNumAnswers]
	sub b                          ; rightN
	jr .haveCount
.leftCount
	ld a, b                        ; leftN
.haveCount
	dec a
	ld [wMaxMenuItem], a
	ld a, PAD_A | PAD_LEFT | PAD_RIGHT
	ld [wMenuWatchedKeys], a
	ld a, QUIZ_WRAP_MENU
	ld [wMenuWrappingEnabled], a
	ret

INCLUDE "engine/battle/quiz_data.asm"
