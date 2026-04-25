"""
Assessment Node — the core of the agent.

Responsibilities:
- Generate adaptive questions per skill
- Evaluate candidate answers
- Track confidence per skill
- Know when to move to the next skill
- Handle the human-in-the-loop turn pattern
"""
from __future__ import annotations

import structlog

from config import get_settings
from models import (
    GraphState, SessionPhase, SkillAssessmentState,
    AssessmentQuestion, AssessmentAnswer, ProficiencyLevel,
)
from prompts import (
    ASSESSMENT_OPENING_SYSTEM, ASSESSMENT_OPENING_USER,
    QUESTION_GENERATOR_SYSTEM, QUESTION_GENERATOR_USER,
    ANSWER_EVALUATOR_SYSTEM, ANSWER_EVALUATOR_USER,
    SKILL_FINALISER_SYSTEM, SKILL_FINALISER_USER,
    TRANSITION_MESSAGE_SYSTEM, TRANSITION_MESSAGE_USER,
    COMPLETION_MESSAGE_USER,
)
from services import get_assessor_llm, call_llm_json, call_llm_text

logger = structlog.get_logger(__name__)

_SCORE_TO_LEVEL = {
    1: ProficiencyLevel.NO_KNOWLEDGE,
    2: ProficiencyLevel.SURFACE_AWARENESS,
    3: ProficiencyLevel.WORKING_KNOWLEDGE,
    4: ProficiencyLevel.PROFICIENT,
    5: ProficiencyLevel.EXPERT,
}


# ─────────────────────────────────────────────
# Opening message (called once at session start)
# ─────────────────────────────────────────────

async def generate_opening_message(state: GraphState) -> GraphState:
    """Generate the welcome/intro message before assessment begins."""
    llm = get_assessor_llm()
    skills_list = ", ".join(s.name for s in state.skills_to_assess)

    message = await call_llm_text(
        llm,
        system_prompt=ASSESSMENT_OPENING_SYSTEM.format(
            job_title=state.parsed_jd.job_title
        ),
        user_prompt=ASSESSMENT_OPENING_USER.format(
            candidate_name=state.parsed_resume.candidate_name,
            job_title=state.parsed_jd.job_title,
            skills_list=skills_list,
        ),
    )

    return state.model_copy(update={
        "pending_bot_message": message,
        "awaiting_human_input": True,
    })


# ─────────────────────────────────────────────
# Assessment node — processes one candidate turn
# ─────────────────────────────────────────────

async def assessment_node(state: GraphState) -> GraphState:
    """
    Main assessment node. Called each time the candidate submits a response.

    Flow:
    1. If no current skill question yet → generate first question for current skill
    2. If candidate just answered → evaluate answer, update skill state
    3. If skill confidence >= threshold or max questions reached → finalise skill
    4. If all skills done → transition to analysis phase
    5. Otherwise → generate next question
    """
    settings = get_settings()
    llm = get_assessor_llm()

    skills = state.skills_to_assess
    idx = state.current_skill_index

    # All skills assessed → move to analysis
    if idx >= len(skills):
        return await _finish_assessment(state, llm)

    current_skill_name = skills[idx].name
    skill_state = state.skill_states[current_skill_name]

    # ── Step 1: Evaluate the candidate's last answer (if any) ──
    if state.conversation_history and not skill_state.questions_asked:
        # First question for this skill hasn't been asked yet
        pass
    elif state.conversation_history:
        last_human = _get_last_human_message(state.conversation_history)
        if last_human and skill_state.questions_asked:
            skill_state = await _evaluate_answer(
                llm, skill_state, last_human, settings
            )

    # ── Step 2: Check if current skill is done ──
    skill_done = (
        skill_state.current_confidence >= settings.confidence_threshold
        or len(skill_state.questions_asked) >= settings.max_questions_per_skill
    )

    if skill_done:
        skill_state = await _finalise_skill(llm, skill_state)
        skill_state = skill_state.model_copy(update={"is_complete": True})

        # Update states
        new_skill_states = dict(state.skill_states)
        new_skill_states[current_skill_name] = skill_state

        next_idx = idx + 1

        # All skills done?
        if next_idx >= len(skills):
            final_state = state.model_copy(update={
                "skill_states": new_skill_states,
                "current_skill_index": next_idx,
            })
            return await _finish_assessment(final_state, llm)

        # Transition to next skill
        next_skill_name = skills[next_idx].name
        transition_msg = await _generate_transition(
            llm,
            completed_skill=current_skill_name,
            score=skill_state.final_score or skill_state.provisional_score,
            next_skill=next_skill_name,
            candidate_name=state.parsed_resume.candidate_name,
        )

        # Generate first question for next skill
        next_skill_state = new_skill_states[next_skill_name]
        next_skill_state, first_question = await _generate_question(
            llm, next_skill_state, settings
        )
        new_skill_states[next_skill_name] = next_skill_state

        bot_msg = f"{transition_msg}\n\n{first_question}"

        return state.model_copy(update={
            "skill_states": new_skill_states,
            "current_skill_index": next_idx,
            "pending_bot_message": bot_msg,
            "awaiting_human_input": True,
        })

    # ── Step 3: Generate next question for current skill ──
    skill_state, question_text = await _generate_question(llm, skill_state, settings)

    new_skill_states = dict(state.skill_states)
    new_skill_states[current_skill_name] = skill_state

    return state.model_copy(update={
        "skill_states": new_skill_states,
        "pending_bot_message": question_text,
        "awaiting_human_input": True,
    })


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

async def _generate_question(
    llm,
    skill_state: SkillAssessmentState,
    settings,
) -> tuple[SkillAssessmentState, str]:
    """Generate the next adaptive question for a skill."""
    qa_history = _format_qa_history(skill_state)

    data = await call_llm_json(
        llm,
        system_prompt=QUESTION_GENERATOR_SYSTEM,
        user_prompt=QUESTION_GENERATOR_USER.format(
            skill_name=skill_state.skill.name,
            claimed_level=skill_state.skill.claimed_level or "Not stated",
            questions_count=len(skill_state.questions_asked),
            max_questions=settings.max_questions_per_skill,
            qa_history=qa_history,
            evidence_notes="\n".join(skill_state.evidence_notes) or "None yet",
            confidence=round(skill_state.current_confidence, 2),
            provisional_score=skill_state.provisional_score,
        ),
    )

    question = AssessmentQuestion(
        question=data["question"],
        skill_name=skill_state.skill.name,
        difficulty=int(data.get("difficulty", 3)),
    )

    updated_questions = list(skill_state.questions_asked) + [question]
    updated_skill = skill_state.model_copy(update={"questions_asked": updated_questions})

    return updated_skill, data["question"]


async def _evaluate_answer(
    llm,
    skill_state: SkillAssessmentState,
    answer_text: str,
    settings,
) -> SkillAssessmentState:
    """Evaluate the candidate's latest answer and update skill state."""
    if not skill_state.questions_asked:
        return skill_state

    last_question = skill_state.questions_asked[-1]
    qa_history = _format_qa_history(skill_state)

    data = await call_llm_json(
        llm,
        system_prompt=ANSWER_EVALUATOR_SYSTEM,
        user_prompt=ANSWER_EVALUATOR_USER.format(
            skill_name=skill_state.skill.name,
            question=last_question.question,
            answer=answer_text,
            qa_history=qa_history,
            evidence_notes="\n".join(skill_state.evidence_notes) or "None",
            provisional_score=skill_state.provisional_score,
            confidence=round(skill_state.current_confidence, 2),
        ),
    )

    answer = AssessmentAnswer(
        question_id=last_question.id,
        question_text=last_question.question,
        answer_text=answer_text,
        score=int(data["score"]),
        reasoning=data.get("reasoning", ""),
        flags=data.get("flags", []),
    )

    return skill_state.model_copy(update={
        "answers": list(skill_state.answers) + [answer],
        "current_confidence": float(data.get("updated_confidence", skill_state.current_confidence)),
        "provisional_score": int(data.get("updated_provisional_score", skill_state.provisional_score)),
        "evidence_notes": list(data.get("updated_evidence_notes", skill_state.evidence_notes)),
    })


async def _finalise_skill(llm, skill_state: SkillAssessmentState) -> SkillAssessmentState:
    """Finalise the score and proficiency level for a skill."""
    qa_history = _format_qa_history(skill_state)

    data = await call_llm_json(
        llm,
        system_prompt=SKILL_FINALISER_SYSTEM,
        user_prompt=SKILL_FINALISER_USER.format(
            skill_name=skill_state.skill.name,
            qa_history=qa_history,
            evidence_notes="\n".join(skill_state.evidence_notes),
            provisional_score=skill_state.provisional_score,
            confidence=round(skill_state.current_confidence, 2),
        ),
    )

    final_score = int(data.get("final_score", skill_state.provisional_score))
    level_str = data.get("final_level", "working_knowledge")

    try:
        final_level = ProficiencyLevel(level_str)
    except ValueError:
        final_level = _SCORE_TO_LEVEL.get(final_score, ProficiencyLevel.WORKING_KNOWLEDGE)

    notes = list(skill_state.evidence_notes)
    summary = data.get("summary", "")
    if summary:
        notes.append(f"SUMMARY: {summary}")

    return skill_state.model_copy(update={
        "final_score": final_score,
        "final_level": final_level,
        "evidence_notes": notes,
    })


async def _generate_transition(
    llm,
    completed_skill: str,
    score: int,
    next_skill: str,
    candidate_name: str,
) -> str:
    return await call_llm_text(
        llm,
        system_prompt=TRANSITION_MESSAGE_SYSTEM,
        user_prompt=TRANSITION_MESSAGE_USER.format(
            completed_skill=completed_skill,
            score=score,
            next_skill=next_skill,
            candidate_name=candidate_name,
        ),
    )


async def _finish_assessment(state: GraphState, llm) -> GraphState:
    """All skills assessed — generate closing message and transition to analysis."""
    skills_count = len(state.skills_to_assess)

    closing = await call_llm_text(
        llm,
        system_prompt="You are a warm professional interviewer.",
        user_prompt=COMPLETION_MESSAGE_USER.format(
            candidate_name=state.parsed_resume.candidate_name,
            skills_count=skills_count,
            duration_minutes=skills_count * 3,  # rough estimate
        ),
    )

    logger.info("assessment_complete", session_id=state.session_id)

    return state.model_copy(update={
        "phase": SessionPhase.ANALYSING,
        "pending_bot_message": closing,
        "awaiting_human_input": False,
    })


def _format_qa_history(skill_state: SkillAssessmentState) -> str:
    """Format Q&A history as readable text for LLM context."""
    if not skill_state.questions_asked:
        return "No questions asked yet."

    lines = []
    answer_map = {a.question_id: a for a in skill_state.answers}

    for i, q in enumerate(skill_state.questions_asked):
        lines.append(f"Q{i+1} [difficulty {q.difficulty}]: {q.question}")
        answer = answer_map.get(q.id)
        if answer:
            lines.append(f"A{i+1}: {answer.answer_text}")
            lines.append(f"   → Score: {answer.score}/5 | {answer.reasoning}")
        else:
            lines.append("A: [awaiting answer]")
        lines.append("")

    return "\n".join(lines)


def _get_last_human_message(history: list[dict]) -> str | None:
    """Get the most recent human message from conversation history."""
    for msg in reversed(history):
        if msg.get("role") == "human":
            return msg.get("content")
    return None