"""
Gap Analysis Node — runs after assessment is complete.
Computes the delta between required skill levels and assessed levels.
"""
from __future__ import annotations

import structlog

from models import GraphState, SessionPhase, SkillGap, SkillTier
from prompts import GAP_ANALYSER_SYSTEM, GAP_ANALYSER_USER
from services import get_planner_llm, call_llm_json

logger = structlog.get_logger(__name__)

# Required level mapping based on JD tier and seniority
_TIER_REQUIRED_LEVEL = {
    SkillTier.MUST_HAVE: 4,
    SkillTier.NICE_TO_HAVE: 3,
    SkillTier.BONUS: 2,
}


async def gap_analysis_node(state: GraphState) -> GraphState:
    """
    Compare assessed skill levels against JD requirements.
    Identify gaps and whether they are adjacent (bridgeable).
    """
    logger.info("gap_analysis_start", session_id=state.session_id)

    try:
        llm = get_planner_llm()

        # Build required skills summary
        required_skills = []
        for skill in state.skills_to_assess:
            required_level = _TIER_REQUIRED_LEVEL.get(skill.tier, 3)
            required_skills.append({
                "name": skill.name,
                "tier": skill.tier.value,
                "required_level": required_level,
            })

        # Build assessed scores
        assessed_scores = {}
        for skill_name, skill_state in state.skill_states.items():
            assessed_scores[skill_name] = {
                "final_score": skill_state.final_score or skill_state.provisional_score,
                "evidence": " | ".join(skill_state.evidence_notes[:3]),
            }

        # Build candidate strengths (skills scored 4+)
        strengths = [
            f"{name} (score: {s['final_score']})"
            for name, s in assessed_scores.items()
            if s["final_score"] >= 4
        ]

        # Ask LLM to compute gaps with adjacency analysis
        gaps_data = await call_llm_json(
            llm,
            system_prompt=GAP_ANALYSER_SYSTEM,
            user_prompt=GAP_ANALYSER_USER.format(
                required_skills=_format_required(required_skills),
                assessed_scores=_format_assessed(assessed_scores),
                candidate_strengths=", ".join(strengths) or "None identified",
            ),
        )

        # Build SkillGap objects — only include actual gaps
        skill_gaps = []
        for gap_data in gaps_data:
            assessed = gap_data.get("assessed_level", 0)
            required = gap_data.get("required_level", 3)
            gap_size = required - assessed

            if gap_size > 0:  # Only real gaps
                skill_gaps.append(SkillGap(
                    skill_name=gap_data["skill_name"],
                    required_level=required,
                    assessed_level=assessed,
                    gap_size=gap_size,
                    is_adjacent=bool(gap_data.get("is_adjacent", False)),
                    priority=int(gap_data.get("priority", 3)),
                ))

        # Sort by priority
        skill_gaps.sort(key=lambda g: g.priority)

        logger.info(
            "gap_analysis_complete",
            session_id=state.session_id,
            gaps_found=len(skill_gaps),
        )

        return state.model_copy(update={
            "phase": SessionPhase.PLANNING,
            "skill_gaps": skill_gaps,
        })

    except Exception as e:
        logger.error("gap_analysis_failed", session_id=state.session_id, error=str(e))
        return state.model_copy(update={
            "phase": SessionPhase.ERROR,
            "error_message": f"Gap analysis failed: {str(e)}",
        })


def _format_required(skills: list[dict]) -> str:
    lines = []
    for s in skills:
        lines.append(f"- {s['name']} ({s['tier']}): required level {s['required_level']}/5")
    return "\n".join(lines)


def _format_assessed(scores: dict) -> str:
    lines = []
    for name, data in scores.items():
        lines.append(f"- {name}: assessed {data['final_score']}/5 | {data['evidence'][:100]}")
    return "\n".join(lines)