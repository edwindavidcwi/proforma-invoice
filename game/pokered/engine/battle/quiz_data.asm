; ============================================================================
; Quiz Battle - question banks (grades 1-5)
; ----------------------------------------------------------------------------
; To add/change a question: write its text + answer strings in the STRINGS
; section (each ending in "@"), then add a `quizq` line to the right grade's
; list.  The per-grade counts update automatically.
;
; IMPORTANT - the game font has NO "=", "+", or "%" characters.  Use words like
; "plus", and write math as a question, e.g. "2 plus 3?".  These DO work:
;   digits 0-9, A-Z, a-z, space, and  - / x . : ? !
; Keep question text <= 18 characters and each answer <= 9 characters.
; Re-run `make` afterwards.
; ============================================================================

; One question entry (12 bytes):
;   quizq QUESTION, CORRECT_INDEX(0-3), NUM_ANSWERS(2-4), ANS0, ANS1, ANS2, ANS3
MACRO quizq
	dw \1       ; question text
	db \2       ; index (0-based) of the correct answer
	db \3       ; how many answers to show
	dw \4, \5, \6, \7
ENDM

; Grade lookup: badge count -> grade.  Each entry: list pointer + question count.
; Counts are computed from the contiguous entry tables below.
QuizGradeTable::
	dw Grade1Questions
	db (Grade2Questions - Grade1Questions) / 12
	dw Grade2Questions
	db (Grade3Questions - Grade2Questions) / 12
	dw Grade3Questions
	db (Grade4Questions - Grade3Questions) / 12
	dw Grade4Questions
	db (Grade5Questions - Grade4Questions) / 12
	dw Grade5Questions
	db (QuestionsEnd - Grade5Questions) / 12

; ---- entry tables (must stay contiguous; strings live further down) ----
Grade1Questions::
	quizq G1Q1, 1, 3, G1Q1A, G1Q1B, G1Q1C, G1Q1C
	quizq G1Q2, 2, 3, G1Q2A, G1Q2B, G1Q2C, G1Q2C
	quizq G1Q3, 0, 3, G1Q3A, G1Q3B, G1Q3C, G1Q3C
	quizq G1Q4, 1, 3, G1Q4A, G1Q4B, G1Q4C, G1Q4C
Grade2Questions::
	quizq G2Q1, 2, 3, G2Q1A, G2Q1B, G2Q1C, G2Q1C
	quizq G2Q2, 0, 3, G2Q2A, G2Q2B, G2Q2C, G2Q2C
	quizq G2Q3, 1, 3, G2Q3A, G2Q3B, G2Q3C, G2Q3C
	quizq G2Q4, 2, 3, G2Q4A, G2Q4B, G2Q4C, G2Q4C
Grade3Questions::
	quizq G3Q1, 1, 3, G3Q1A, G3Q1B, G3Q1C, G3Q1C
	quizq G3Q2, 2, 3, G3Q2A, G3Q2B, G3Q2C, G3Q2C
	quizq G3Q3, 0, 3, G3Q3A, G3Q3B, G3Q3C, G3Q3C
	quizq G3Q4, 1, 3, G3Q4A, G3Q4B, G3Q4C, G3Q4C
Grade4Questions::
	quizq G4Q1, 2, 3, G4Q1A, G4Q1B, G4Q1C, G4Q1C
	quizq G4Q2, 0, 3, G4Q2A, G4Q2B, G4Q2C, G4Q2C
	quizq G4Q3, 1, 3, G4Q3A, G4Q3B, G4Q3C, G4Q3C
	quizq G4Q4, 2, 3, G4Q4A, G4Q4B, G4Q4C, G4Q4C
Grade5Questions::
	quizq G5Q1, 1, 3, G5Q1A, G5Q1B, G5Q1C, G5Q1C
	quizq G5Q2, 2, 3, G5Q2A, G5Q2B, G5Q2C, G5Q2C
	quizq G5Q3, 0, 3, G5Q3A, G5Q3B, G5Q3C, G5Q3C
	quizq G5Q4, 1, 3, G5Q4A, G5Q4B, G5Q4C, G5Q4C
QuestionsEnd::

; ---- strings ----
; Grade 1: add/sub within 10, counting
G1Q1: db "2 plus 3?@"
G1Q1A: db "4@"
G1Q1B: db "5@"
G1Q1C: db "6@"
G1Q2: db "7 - 4?@"
G1Q2A: db "1@"
G1Q2B: db "2@"
G1Q2C: db "3@"
G1Q3: db "Next: 1 2 3 ?@"
G1Q3A: db "4@"
G1Q3B: db "5@"
G1Q3C: db "3@"
G1Q4: db "6 plus 1?@"
G1Q4A: db "6@"
G1Q4B: db "7@"
G1Q4C: db "8@"

; Grade 2: add/sub within 100, place value
G2Q1: db "14 plus 8?@"
G2Q1A: db "20@"
G2Q1B: db "21@"
G2Q1C: db "22@"
G2Q2: db "30 - 12?@"
G2Q2A: db "18@"
G2Q2B: db "19@"
G2Q2C: db "20@"
G2Q3: db "Tens in 40?@"
G2Q3A: db "3@"
G2Q3B: db "4@"
G2Q3C: db "5@"
G2Q4: db "Add three 5s@"
G2Q4A: db "10@"
G2Q4B: db "12@"
G2Q4C: db "15@"

; Grade 3: x and / facts
G3Q1: db "6 x 7?@"
G3Q1A: db "36@"
G3Q1B: db "42@"
G3Q1C: db "48@"
G3Q2: db "24 / 4?@"
G3Q2A: db "4@"
G3Q2B: db "5@"
G3Q2C: db "6@"
G3Q3: db "8 x 5?@"
G3Q3A: db "40@"
G3Q3B: db "45@"
G3Q3C: db "35@"
G3Q4: db "Half of 18?@"
G3Q4A: db "8@"
G3Q4B: db "9@"
G3Q4C: db "10@"

; Grade 4: multi-digit x, decimals, fractions
G4Q1: db "12 x 12?@"
G4Q1A: db "124@"
G4Q1B: db "134@"
G4Q1C: db "144@"
G4Q2: db "Half of 1.0?@"
G4Q2A: db "0.5@"
G4Q2B: db "0.2@"
G4Q2C: db "5.0@"
G4Q3: db "144 / 12?@"
G4Q3A: db "11@"
G4Q3B: db "12@"
G4Q3C: db "13@"
G4Q4: db "2/4 equals?@"
G4Q4A: db "1/3@"
G4Q4B: db "1/4@"
G4Q4C: db "1/2@"

; Grade 5: decimal ops, order of operations, rounding
G5Q1: db "0.6 plus 0.7?@"
G5Q1A: db "1.2@"
G5Q1B: db "1.3@"
G5Q1C: db "0.13@"
G5Q2: db "2 plus 3 x 4?@"
G5Q2A: db "20@"
G5Q2B: db "24@"
G5Q2C: db "14@"
G5Q3: db "3/4 plus 1/4?@"
G5Q3A: db "1@"
G5Q3B: db "4/8@"
G5Q3C: db "2@"
G5Q4: db "Round 4.7?@"
G5Q4A: db "4@"
G5Q4B: db "5@"
G5Q4C: db "6@"

; ---- result messages (shown via PrintText) ----
QuizCorrectText::
	text "Great job!"
	line "Direct hit!"
	prompt

QuizTryAgainText::
	text "Not quite..."
	line "Try once more!"
	prompt

QuizMissText::
	text "That's okay!"
	line "We'll get the"
	cont "next one!"
	prompt
