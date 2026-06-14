; ============================================================================
; Professor's Assistant - tutor
; ----------------------------------------------------------------------------
; Teaches the key skill for the player's current grade (a worked example), then
; gives one no-stakes practice question. Reached with `callfar Tutor` from the
; Start menu and from Pokemon Centre NPCs. Grades scale with badges, exactly
; like the quiz battles do.
; ============================================================================

SECTION "Tutor Engine", ROMX

Tutor::
	call TutorGrade                ; a = grade (1-5)
	dec a
	add a                          ; *2 (table of 2-byte pointers)
	ld c, a
	ld b, 0
	ld hl, TutorLessons
	add hl, bc
	ld a, [hli]
	ld h, [hl]
	ld l, a                        ; hl = this grade's lesson text
	call PrintText                 ; show the worked example
	; one no-stakes practice question (the quiz engine is in another bank)
	ld hl, QuizPractice
	ld b, BANK(QuizPractice)
	call Bankswitch
	ret

; grade = min(5, badges / 2 + 1)  (same scaling the quiz uses)
TutorGrade:
	ld hl, wObtainedBadges
	ld b, 1
	call CountSetBits
	ld a, [wNumSetBits]
	srl a
	inc a
	cp 6
	ret c
	ld a, 5
	ret

TutorLessons:
	dw Lesson1
	dw Lesson2
	dw Lesson3
	dw Lesson4
	dw Lesson5

; -- Grade 1: take-away and skip counting --
Lesson1:
	text "PROF AIDE:"
	line "Math time!"
	para "7 - 4 is TAKE"
	line "AWAY. Hop back"
	para "from 7: 6, 5,"
	line "4, 3. It is 3!"
	para "Count by 2s:"
	line "2, 4, 6, 8!"
	para "Now you try!"
	prompt

; -- Grade 2: place value and 2-digit addition --
Lesson2:
	text "PROF AIDE:"
	line "Big numbers!"
	para "TENS and ONES."
	line "40 is 4 tens."
	para "18 plus 15:"
	line "add tens, 10"
	cont "and 10 is 20."
	para "Add ones, 8 and"
	line "5 is 13."
	para "20 and 13 is 33"
	para "Now you try!"
	prompt

; -- Grade 3: multiplication as repeated adding, and division --
Lesson3:
	text "PROF AIDE:"
	line "Times tables!"
	para "3 x 6 means 3"
	line "groups of 6."
	para "6 and 6 and 6"
	line "is 18!"
	para "Divide is share:"
	line "15 / 3 is 5."
	para "Now you try!"
	prompt

; -- Grade 4: multi-digit times and simple fractions --
Lesson4:
	text "PROF AIDE:"
	line "Bigger times!"
	para "12 x 12: do"
	line "10 x 12 is 120,"
	para "2 x 12 is 24."
	line "120 and 24 is"
	cont "144!"
	para "Half a cake is"
	line "1 of 2 parts:"
	cont "that is 1/2."
	para "Now you try!"
	prompt

; -- Grade 5: order of operations and rounding --
Lesson5:
	text "PROF AIDE:"
	line "Order matters!"
	para "2 plus 3 x 4:"
	line "do TIMES first."
	para "3 x 4 is 12,"
	line "then plus 2 is"
	cont "14!"
	para "Round 4.7? It is"
	line "near 5. Up it"
	cont "goes to 5!"
	para "Now you try!"
	prompt
