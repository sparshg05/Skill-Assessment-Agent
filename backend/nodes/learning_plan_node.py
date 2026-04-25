"""
Learning Plan Node — generates the personalised learning roadmap.

Uses the gap analysis output to create:
- A prioritised, sequenced learning path
- Real resources per skill (Tavily + curated)
- Time estimates based on commitment hours/week
- Milestone checkpoints
"""
from __future__ import annotations

import asyncio
import structlog

from models import (
    GraphState, SessionPhase, LearningPlan,
    SkillLearningPath, LearningResource, ResourceType,
)
from prompts import LEARNING_PLAN_SYSTEM, LEARNING_PLAN_USER
from services import get_planner_llm, call_llm_json, get_resources_for_skill

logger = structlog.get_logger(__name__)


async def learning_plan_node(state: GraphState) -> GraphState:
    """
    Generate a complete personalised learning plan from skill gaps.
    Fetches resources concurrently for all skills.
    """
    logger.info("learning_plan_start", session_id=state.session_id)

    if not state.skill_gaps:
        logger.info("no_gaps_found", session_id=state.session_id)
        plan = LearningPlan(
            total_estimated_hours=0,
            total_estimated_weeks=0,
            executive_summary="Great news! Your assessed skills closely match the job requirements. Focus on deepening expertise in your strongest areas.",
            skill_paths=[],
            quick_wins=[],
            recommended_sequence=[],
        )
        return state.model_copy(update={
            "phase": SessionPhase.COMPLETE,
            "learning_plan": plan,
        })

    try:
        llm = get_planner_llm()
        commitment = getattr(state, "commitment_hours_per_week", 10)

        # Build candidate profile
        strengths = [
            name for name, s in state.skill_states.items()
            if (s.final_score or s.provisional_score) >= 4
        ]

        # Format gaps for LLM
        gaps_formatted = _format_gaps(state)

        # Get the structural plan from LLM (sequence, milestones, time estimates)
        plan_data = await call_llm_json(
            llm,
            system_prompt=LEARNING_PLAN_SYSTEM.format(
                commitment_hours=commitment
            ),
            user_prompt=LEARNING_PLAN_USER.format(
                candidate_name=state.parsed_resume.candidate_name,
                current_role=state.parsed_resume.current_role,
                years_experience=state.parsed_resume.years_experience,
                strengths=", ".join(strengths) or "General programming",
                job_title=state.parsed_jd.job_title,
                skill_gaps=gaps_formatted,
                commitment_hours=commitment,
            ),
        )

        # Fetch resources concurrently for all gap skills
        skill_names = [g.skill_name for g in state.skill_gaps]
        resource_lists = await asyncio.gather(
            *[get_resources_for_skill(name) for name in skill_names],
            return_exceptions=True,
        )
        resource_map: dict[str, list[LearningResource]] = {}
        for skill_name, result in zip(skill_names, resource_lists):
            if isinstance(result, Exception):
                logger.warning("resource_fetch_failed", skill=skill_name, error=str(result))
                resource_map[skill_name] = []
            else:
                resource_map[skill_name] = result

        # Build SkillLearningPath objects
        skill_paths = _build_skill_paths(plan_data, state, resource_map)

        # Build final LearningPlan
        total_hours = sum(p.estimated_hours for p in skill_paths)
        total_weeks = total_hours / max(commitment, 1)

        plan = LearningPlan(
            total_estimated_hours=round(total_hours, 1),
            total_estimated_weeks=round(total_weeks, 1),
            commitment_hours_per_week=commitment,
            executive_summary=plan_data.get("executive_summary", ""),
            skill_paths=skill_paths,
            quick_wins=plan_data.get("quick_wins", []),
            recommended_sequence=plan_data.get("recommended_sequence", skill_names),
        )

        logger.info(
            "learning_plan_complete",
            session_id=state.session_id,
            total_hours=total_hours,
            paths=len(skill_paths),
        )

        return state.model_copy(update={
            "phase": SessionPhase.COMPLETE,
            "learning_plan": plan,
        })

    except Exception as e:
        logger.error("learning_plan_failed", session_id=state.session_id, error=str(e))
        return state.model_copy(update={
            "phase": SessionPhase.ERROR,
            "error_message": f"Learning plan generation failed: {str(e)}",
        })


def _format_gaps(state: GraphState) -> str:
    lines = []
    for gap in state.skill_gaps:
        lines.append(
            f"- {gap.skill_name}: assessed {gap.assessed_level}/5, "
            f"required {gap.required_level}/5, "
            f"gap={gap.gap_size}, "
            f"adjacent={'yes' if gap.is_adjacent else 'no'}, "
            f"priority={gap.priority}"
        )
    return "\n".join(lines)


def _build_skill_paths(
    plan_data: dict,
    state: GraphState,
    resource_map: dict[str, list[LearningResource]],
) -> list[SkillLearningPath]:
    """Merge LLM plan with fetched resources into SkillLearningPath objects."""
    paths = []
    gap_map = {g.skill_name: g for g in state.skill_gaps}

    for path_data in plan_data.get("skill_paths", []):
        skill_name = path_data.get("skill_name", "")
        gap = gap_map.get(skill_name)
        if not gap:
            continue

        # Use LLM-suggested resources if provided, otherwise use fetched
        llm_resources = []
        for r in path_data.get("resources", []):
            try:
                llm_resources.append(LearningResource(
                    title=r.get("title", ""),
                    url=r.get("url", "#"),
                    resource_type=ResourceType(r.get("resource_type", "course")),
                    platform=r.get("platform", ""),
                    estimated_hours=float(r.get("estimated_hours", 5)),
                    difficulty=int(r.get("difficulty", 3)),
                    is_free=bool(r.get("is_free", True)),
                    description=r.get("description", ""),
                ))
            except Exception:
                continue

        # Merge: LLM resources + fetched resources (deduplicate)
        fetched = resource_map.get(skill_name, [])
        all_resources = _merge_resources(llm_resources, fetched)

        paths.append(SkillLearningPath(
            skill_name=skill_name,
            gap=gap,
            why_prioritised=path_data.get("why_prioritised", ""),
            prerequisite_skills=path_data.get("prerequisite_skills", []),
            resources=all_resources,
            estimated_hours=float(path_data.get("estimated_hours", gap.gap_size * 5)),
            estimated_weeks=float(path_data.get("estimated_weeks", gap.gap_size)),
            milestones=path_data.get("milestones", []),
        ))

    # Handle gaps not covered in plan_data (fallback)
    covered = {p.skill_name for p in paths}
    for gap in state.skill_gaps:
        if gap.skill_name not in covered:
            paths.append(SkillLearningPath(
                skill_name=gap.skill_name,
                gap=gap,
                why_prioritised="Required skill with identified proficiency gap.",
                resources=resource_map.get(gap.skill_name, []),
                estimated_hours=float(gap.gap_size * 8),
                estimated_weeks=float(gap.gap_size),
                milestones=[f"Achieve level {gap.assessed_level + 1} in {gap.skill_name}"],
            ))

    return paths


def _merge_resources(
    primary: list[LearningResource],
    secondary: list[LearningResource],
) -> list[LearningResource]:
    seen = set()
    merged = []
    for r in primary + secondary:
        key = r.title.lower()
        if key not in seen and r.url and r.url != "#":
            seen.add(key)
            merged.append(r)
    return merged[:4]