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

; One question entry (14 bytes):
;   quizq QUESTION, CORRECT_INDEX(0-3), NUM_ANSWERS(2-4), ANS0, ANS1, ANS2, ANS3, HINT
MACRO quizq
	dw \1       ; question text
	db \2       ; index (0-based) of the correct answer
	db \3       ; how many answers to show
	dw \4, \5, \6, \7
	dw \8       ; method hint, shown on a wrong-answer retry
ENDM

; Grade lookup: badge count -> grade.  Each entry: list pointer + question count.
; Counts are computed from the contiguous entry tables below.
QuizGradeTable::
	dw Grade1Questions
	db (Grade2Questions - Grade1Questions) / 14
	dw Grade2Questions
	db (Grade3Questions - Grade2Questions) / 14
	dw Grade3Questions
	db (Grade4Questions - Grade3Questions) / 14
	dw Grade4Questions
	db (Grade5Questions - Grade4Questions) / 14
	dw Grade5Questions
	db (QuestionsEnd - Grade5Questions) / 14

; ---- entry tables (must stay contiguous; strings live further down) ----
Grade1Questions::
	quizq G1Q1, 1, 3, G1Q1A, G1Q1B, G1Q1C, G1Q1C, G1Q1H
	quizq G1Q2, 2, 3, G1Q2A, G1Q2B, G1Q2C, G1Q2C, G1Q2H
	quizq G1Q3, 0, 3, G1Q3A, G1Q3B, G1Q3C, G1Q3C, G1Q3H
	quizq G1Q4, 1, 3, G1Q4A, G1Q4B, G1Q4C, G1Q4C, G1Q4H
	quizq G1Q5, 2, 3, G1Q5A, G1Q5B, G1Q5C, G1Q5C, G1Q5H
	quizq G1Q6, 1, 3, G1Q6A, G1Q6B, G1Q6C, G1Q6C, G1Q6H
	quizq G1Q7, 1, 3, G1Q7A, G1Q7B, G1Q7C, G1Q7C, G1Q7H
	quizq G1Q8, 1, 3, G1Q8A, G1Q8B, G1Q8C, G1Q8C, G1Q8H
	quizq G1Q9, 0, 3, G1Q9A, G1Q9B, G1Q9C, G1Q9C, G1Q9H
	quizq G1Q10, 2, 3, G1Q10A, G1Q10B, G1Q10C, G1Q10C, G1Q10H
Grade2Questions::
	quizq G2Q1, 2, 3, G2Q1A, G2Q1B, G2Q1C, G2Q1C, G2Q1H
	quizq G2Q2, 0, 3, G2Q2A, G2Q2B, G2Q2C, G2Q2C, G2Q2H
	quizq G2Q3, 1, 3, G2Q3A, G2Q3B, G2Q3C, G2Q3C, G2Q3H
	quizq G2Q4, 2, 3, G2Q4A, G2Q4B, G2Q4C, G2Q4C, G2Q4H
	quizq G2Q5, 1, 3, G2Q5A, G2Q5B, G2Q5C, G2Q5C, G2Q5H
	quizq G2Q6, 1, 3, G2Q6A, G2Q6B, G2Q6C, G2Q6C, G2Q6H
	quizq G2Q7, 1, 3, G2Q7A, G2Q7B, G2Q7C, G2Q7C, G2Q7H
	quizq G2Q8, 2, 3, G2Q8A, G2Q8B, G2Q8C, G2Q8C, G2Q8H
Grade3Questions::
	quizq G3Q1, 1, 3, G3Q1A, G3Q1B, G3Q1C, G3Q1C, G3Q1H
	quizq G3Q2, 2, 3, G3Q2A, G3Q2B, G3Q2C, G3Q2C, G3Q2H
	quizq G3Q3, 0, 3, G3Q3A, G3Q3B, G3Q3C, G3Q3C, G3Q3H
	quizq G3Q4, 1, 3, G3Q4A, G3Q4B, G3Q4C, G3Q4C, G3Q4H
	quizq G3Q5, 1, 3, G3Q5A, G3Q5B, G3Q5C, G3Q5C, G3Q5H
	quizq G3Q6, 1, 3, G3Q6A, G3Q6B, G3Q6C, G3Q6C, G3Q6H
	quizq G3Q7, 1, 3, G3Q7A, G3Q7B, G3Q7C, G3Q7C, G3Q7H
	quizq G3Q8, 1, 3, G3Q8A, G3Q8B, G3Q8C, G3Q8C, G3Q8H
Grade4Questions::
	quizq G4Q1, 2, 3, G4Q1A, G4Q1B, G4Q1C, G4Q1C, G4Q1H
	quizq G4Q2, 0, 3, G4Q2A, G4Q2B, G4Q2C, G4Q2C, G4Q2H
	quizq G4Q3, 1, 3, G4Q3A, G4Q3B, G4Q3C, G4Q3C, G4Q3H
	quizq G4Q4, 2, 3, G4Q4A, G4Q4B, G4Q4C, G4Q4C, G4Q4H
	quizq G4Q5, 1, 3, G4Q5A, G4Q5B, G4Q5C, G4Q5C, G4Q5H
	quizq G4Q6, 1, 3, G4Q6A, G4Q6B, G4Q6C, G4Q6C, G4Q6H
	quizq G4Q7, 1, 3, G4Q7A, G4Q7B, G4Q7C, G4Q7C, G4Q7H
	quizq G4Q8, 1, 3, G4Q8A, G4Q8B, G4Q8C, G4Q8C, G4Q8H
Grade5Questions::
	quizq G5Q1, 1, 3, G5Q1A, G5Q1B, G5Q1C, G5Q1C, G5Q1H
	quizq G5Q2, 2, 3, G5Q2A, G5Q2B, G5Q2C, G5Q2C, G5Q2H
	quizq G5Q3, 0, 3, G5Q3A, G5Q3B, G5Q3C, G5Q3C, G5Q3H
	quizq G5Q4, 1, 3, G5Q4A, G5Q4B, G5Q4C, G5Q4C, G5Q4H
	quizq G5Q5, 1, 3, G5Q5A, G5Q5B, G5Q5C, G5Q5C, G5Q5H
	quizq G5Q6, 1, 3, G5Q6A, G5Q6B, G5Q6C, G5Q6C, G5Q6H
	quizq G5Q7, 1, 3, G5Q7A, G5Q7B, G5Q7C, G5Q7C, G5Q7H
	quizq G5Q8, 0, 3, G5Q8A, G5Q8B, G5Q8C, G5Q8C, G5Q8H
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

; ---- extra questions (added for variety so kids can't memorize) ----
; Grade 1
G1Q5: db "4 plus 4?@"
G1Q5A: db "6@"
G1Q5B: db "7@"
G1Q5C: db "8@"
G1Q6: db "9 - 3?@"
G1Q6A: db "5@"
G1Q6B: db "6@"
G1Q6C: db "7@"
G1Q7: db "Next: 2 4 6 ?@"
G1Q7A: db "7@"
G1Q7B: db "8@"
G1Q7C: db "9@"
G1Q8: db "10 - 5?@"
G1Q8A: db "4@"
G1Q8B: db "5@"
G1Q8C: db "6@"
G1Q9: db "3 plus 6?@"
G1Q9A: db "9@"
G1Q9B: db "8@"
G1Q9C: db "7@"
G1Q10: db "8 - 2?@"
G1Q10A: db "4@"
G1Q10B: db "5@"
G1Q10C: db "6@"
; Grade 2
G2Q5: db "20 plus 15?@"
G2Q5A: db "30@"
G2Q5B: db "35@"
G2Q5C: db "40@"
G2Q6: db "50 - 25?@"
G2Q6A: db "20@"
G2Q6B: db "25@"
G2Q6C: db "30@"
G2Q7: db "Tens in 70?@"
G2Q7A: db "6@"
G2Q7B: db "7@"
G2Q7C: db "8@"
G2Q8: db "9 plus 9?@"
G2Q8A: db "16@"
G2Q8B: db "17@"
G2Q8C: db "18@"
; Grade 3
G3Q5: db "7 x 8?@"
G3Q5A: db "54@"
G3Q5B: db "56@"
G3Q5C: db "58@"
G3Q6: db "36 / 6?@"
G3Q6A: db "5@"
G3Q6B: db "6@"
G3Q6C: db "7@"
G3Q7: db "9 x 9?@"
G3Q7A: db "72@"
G3Q7B: db "81@"
G3Q7C: db "90@"
G3Q8: db "Half of 20?@"
G3Q8A: db "9@"
G3Q8B: db "10@"
G3Q8C: db "11@"
; Grade 4
G4Q5: db "11 x 11?@"
G4Q5A: db "111@"
G4Q5B: db "121@"
G4Q5C: db "131@"
G4Q6: db "3/4 of 8?@"
G4Q6A: db "5@"
G4Q6B: db "6@"
G4Q6C: db "7@"
G4Q7: db "100 / 4?@"
G4Q7A: db "20@"
G4Q7B: db "25@"
G4Q7C: db "30@"
G4Q8: db "0.5 plus 0.5?@"
G4Q8A: db "0.5@"
G4Q8B: db "1.0@"
G4Q8C: db "1.5@"
; Grade 5
G5Q5: db "6 x 7 - 2?@"
G5Q5A: db "38@"
G5Q5B: db "40@"
G5Q5C: db "42@"
G5Q6: db "1/2 plus 1/4?@"
G5Q6A: db "1/4@"
G5Q6B: db "3/4@"
G5Q6C: db "2/4@"
G5Q7: db "Round 5.5?@"
G5Q7A: db "5@"
G5Q7B: db "6@"
G5Q7C: db "7@"
G5Q8: db "10 - 2 x 3?@"
G5Q8A: db "4@"
G5Q8B: db "24@"
G5Q8C: db "8@"

; ---- method hints (shown on a wrong-answer retry; <= 18 chars) ----
; Grade 1
G1Q1H: db "Count on from 2@"
G1Q2H: db "Take 4 from 7@"
G1Q3H: db "1 2 3 then 4@"
G1Q4H: db "One more than 6@"
G1Q5H: db "Double of 4@"
G1Q6H: db "3 less than 9@"
G1Q7H: db "Skip count by 2@"
G1Q8H: db "Half of 10@"
G1Q9H: db "Count on from 6@"
G1Q10H: db "2 less than 8@"
; Grade 2
G2Q1H: db "14 plus 6 is 20@"
G2Q2H: db "30 -10 then -2@"
G2Q3H: db "40 is 4 tens@"
G2Q4H: db "5 plus 5 plus 5@"
G2Q5H: db "Add tens then ones@"
G2Q6H: db "Half of 50@"
G2Q7H: db "70 is 7 tens@"
G2Q8H: db "Double of 9@"
; Grade 3
G3Q1H: db "Six 7s@"
G3Q2H: db "4 times what is 24@"
G3Q3H: db "Eight 5s@"
G3Q4H: db "Split 18 in two@"
G3Q5H: db "Seven 8s@"
G3Q6H: db "6 times what is 36@"
G3Q7H: db "Nine 9s@"
G3Q8H: db "Split 20 in two@"
; Grade 4
G4Q1H: db "10x12 plus 2x12@"
G4Q2H: db "1.0 split in two@"
G4Q3H: db "12 x what is 144@"
G4Q4H: db "Top and bottom /2@"
G4Q5H: db "11 tens plus 11@"
G4Q6H: db "8 /4 then x3@"
G4Q7H: db "Quarter of 100@"
G4Q8H: db "Two halves make 1@"
; Grade 5
G5Q1H: db "Add the tenths@"
G5Q2H: db "Times before plus@"
G5Q3H: db "Add tops: 3 plus 1@"
G5Q4H: db ".5 or more goes up@"
G5Q5H: db "Times first 42-2@"
G5Q6H: db "1/2 is 2/4@"
G5Q7H: db ".5 rounds up@"
G5Q8H: db "Times first 10-6@"

; ---- result messages (shown via PrintText) ----
QuizCorrectText::
	text "Great job!"
	line "Streak "
	text_ram wStringBuffer
	prompt

QuizTryAgainText::
	text "Hint:"
	line ""
	text_ram wStringBuffer
	cont "Try once more!"
	prompt

QuizMissText::
	text "The answer was"
	line ""
	text_ram wStringBuffer
	cont "Now you know!"
	prompt
