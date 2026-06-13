#ifndef GUARD_QUIZ_BATTLE_H
#define GUARD_QUIZ_BATTLE_H

// Educational "Quiz Battle" mod for Pokemon FireRed.
//
// A quiz question is multiple-choice (2-4 answers). Questions are grouped into
// grades 1-5; the player's badge count selects the grade so difficulty grows
// with progress. See quiz_data.c for the content.

#define QUIZ_MAX_ANSWERS 4

struct QuizQuestion
{
    const u8 *question;            // FireRed-encoded string (built with _())
    const u8 *answers[QUIZ_MAX_ANSWERS];
    u8 correctIndex;               // 0-based index of the correct answer
    u8 numAnswers;                 // how many answers to show (2-4)
};

struct QuizGrade
{
    const struct QuizQuestion *questions;
    u8 count;
};

// grades 1-5, indexed 0-4
extern const struct QuizGrade gQuizGrades[5];

// Pick a question scaled to the player's badges (grade = badges/2 + 1, max 5).
// Pick a question scaled to a Pokemon level (grade rises every 10 levels).
const struct QuizQuestion *QuizSelectByBadges(void);
const struct QuizQuestion *QuizSelectByLevel(u8 level);

// Battle-script command 0xF8: ask the player a question mid-battle; a wrong
// answer forces the current move to miss. Implemented in quiz_battle.c.
void Cmd_showquiz(void);

#endif // GUARD_QUIZ_BATTLE_H
