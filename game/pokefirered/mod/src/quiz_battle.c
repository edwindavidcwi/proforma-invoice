// Educational "Quiz Battle" mod for Pokemon FireRed -- battle engine glue.
//
// Implements battle-script command 0xF8 (showquiz): when the PLAYER uses a
// damaging move, a multiple-choice question is shown. A correct answer lets the
// move proceed; a wrong answer makes the move miss (the script jumps to the
// standard "it missed" handler). The question's grade scales with badge count.
//
// The UI reuses the battle engine's own Yes/No window + cursor so selection is
// always correct: the two answer choices replace the "Yes/No" labels, and the
// existing cursor highlights the picked row.

#include "global.h"
#include "gflib.h"
#include "random.h"
#include "event_data.h"
#include "sound.h"
#include "battle.h"
#include "battle_anim.h"
#include "battle_message.h"
#include "battle_script_commands.h"
#include "constants/battle.h"
#include "constants/battle_script_commands.h"
#include "constants/battle_string_ids.h"
#include "constants/songs.h"
#include "constants/flags.h"
#include "quiz_battle.h"

// "{PALETTE 5}{COLOR_HIGHLIGHT_SHADOW 13 14 15}" matches the Yes/No styling so
// our two answers render in the same window with the same colors.
static const u8 sQuizChoiceFormat[] = _("{PALETTE 5}{COLOR_HIGHLIGHT_SHADOW 13 14 15}{STR_VAR_1}\n{STR_VAR_2}");

static u8 sQuizState;
static u8 sQuizCorrectSlot;     // which displayed row (0/1) holds the correct answer

static u8 QuizCountBadges(void)
{
    u8 i, count = 0;
    for (i = 0; i < 8; i++)
    {
        if (FlagGet(FLAG_BADGE01_GET + i))
            count++;
    }
    return count;
}

const struct QuizQuestion *QuizSelectByBadges(void)
{
    u8 grade = (QuizCountBadges() / 2) + 1;      // 0-1 badges -> grade 1, ... up to 5
    const struct QuizGrade *g;

    if (grade > 5)
        grade = 5;
    g = &gQuizGrades[grade - 1];
    return &g->questions[Random() % g->count];
}

const struct QuizQuestion *QuizSelectByLevel(u8 level)
{
    u8 grade = (level + 9) / 10;                  // Lv 1-10 -> 1, 11-20 -> 2, ...
    const struct QuizGrade *g;

    if (grade < 1)
        grade = 1;
    if (grade > 5)
        grade = 5;
    g = &gQuizGrades[grade - 1];
    return &g->questions[Random() % g->count];
}

void Cmd_showquiz(void)
{
    switch (sQuizState)
    {
    case 0:
    {
        const struct QuizQuestion *q;
        const u8 *correct;
        const u8 *distractor;

        // Only the player is quizzed; the AI's moves pass straight through.
        if (GetBattlerSide(gBattlerAttacker) != B_SIDE_PLAYER)
        {
            gBattlescriptCurrInstr += 5;
            return;
        }

        q = QuizSelectByBadges();
        correct = q->answers[q->correctIndex];
        distractor = q->answers[(q->correctIndex + 1) % q->numAnswers];

        // Randomly place the correct answer in the top or bottom row.
        if (Random() & 1)
        {
            StringCopy(gStringVar1, correct);
            StringCopy(gStringVar2, distractor);
            sQuizCorrectSlot = 0;
        }
        else
        {
            StringCopy(gStringVar1, distractor);
            StringCopy(gStringVar2, correct);
            sQuizCorrectSlot = 1;
        }
        StringExpandPlaceholders(gStringVar4, sQuizChoiceFormat);

        BattlePutTextOnWindow(q->question, B_WIN_MSG);
        HandleBattleWindow(23, 8, 29, 13, 0);
        BattlePutTextOnWindow(gStringVar4, B_WIN_YESNO);
        gBattleCommunication[CURSOR_POSITION] = 0;
        BattleCreateYesNoCursorAt();
        sQuizState = 1;
        return;
    }
    case 1:
        if (JOY_NEW(DPAD_UP) && gBattleCommunication[CURSOR_POSITION] != 0)
        {
            PlaySE(SE_SELECT);
            BattleDestroyYesNoCursorAt();
            gBattleCommunication[CURSOR_POSITION] = 0;
            BattleCreateYesNoCursorAt();
        }
        if (JOY_NEW(DPAD_DOWN) && gBattleCommunication[CURSOR_POSITION] == 0)
        {
            PlaySE(SE_SELECT);
            BattleDestroyYesNoCursorAt();
            gBattleCommunication[CURSOR_POSITION] = 1;
            BattleCreateYesNoCursorAt();
        }
        if (JOY_NEW(A_BUTTON))
        {
            PlaySE(SE_SELECT);
            HandleBattleWindow(23, 8, 29, 13, WINDOW_CLEAR);
            sQuizState = 0;
            if (gBattleCommunication[CURSOR_POSITION] == sQuizCorrectSlot)
            {
                // Correct: skip the command's pointer operand and continue.
                gBattlescriptCurrInstr += 5;
            }
            else
            {
                // Wrong: behave like a normal miss and jump to the fail script.
                gMoveResultFlags |= MOVE_RESULT_MISSED;
                gBattleCommunication[MISS_TYPE] = B_MSG_MISSED;
                gBattlescriptCurrInstr = T1_READ_PTR(gBattlescriptCurrInstr + 1);
            }
        }
        return;
    }
}
