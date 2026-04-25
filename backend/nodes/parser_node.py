"""
Parser Node — LangGraph node responsible for:
1. Parsing the Job Description into structured skills
2. Parsing the Resume into structured skills
3. Building the prioritised list of skills to assess
"""
from __future__ import annotations

import structlog

from models import (
    GraphState, ParsedJD, ParsedResume, Skill,
    SkillTier, SessionPhase, SkillAssessmentState,
)
from prompts import (
    JD_PARSER_SYSTEM, JD_PARSER_USER,
    RESUME_PARSER_SYSTEM, RESUME_PARSER_USER,
)
from services import get_parser_llm, call_llm_json
from config import get_settings

logger = structlog.get_logger(__name__)


async def parser_node(state: GraphState) -> GraphState:
    """
    Parse JD and Resume concurrently, build skill_states dict.
    Returns updated GraphState with parsed_jd, parsed_resume, skills_to_assess.
    """
    logger.info("parser_node_start", session_id=state.session_id)
    settings = get_settings()

    try:
        llm = get_parser_llm()

        # Parse JD and Resume (could be done concurrently with asyncio.gather)
        import asyncio
        jd_data, resume_data = await asyncio.gather(
            call_llm_json(
                llm,
                system_prompt=JD_PARSER_SYSTEM,
                user_prompt=JD_PARSER_USER.format(jd_text=state.jd_raw),
            ),
            call_llm_json(
                llm,
                system_prompt=RESUME_PARSER_SYSTEM,
                user_prompt=RESUME_PARSER_USER.format(resume_text=state.resume_raw),
            ),
        )

        # Build ParsedJD
        parsed_jd = _build_parsed_jd(jd_data)

        # Build ParsedResume
        parsed_resume = _build_parsed_resume(resume_data)

        # Build the list of skills to assess (JD skills, prioritised by tier)
        skills_to_assess = _build_skills_to_assess(parsed_jd, parsed_resume, settings)

        # Initialise SkillAssessmentState for each skill
        skill_states = {
            skill.name: SkillAssessmentState(skill=skill)
            for skill in skills_to_assess
        }

        logger.info(
            "parser_node_complete",
            session_id=state.session_id,
            jd_title=parsed_jd.job_title,
            candidate=parsed_resume.candidate_name,
            skills_count=len(skills_to_assess),
        )

        return state.model_copy(update={
            "phase": SessionPhase.ASSESSING,
            "parsed_jd": parsed_jd,
            "parsed_resume": parsed_resume,
            "skills_to_assess": skills_to_assess,
            "skill_states": skill_states,
            "current_skill_index": 0,
        })

    except Exception as e:
        logger.error("parser_node_failed", session_id=state.session_id, error=str(e))
        return state.model_copy(update={
            "phase": SessionPhase.ERROR,
            "error_message": f"Failed to parse documents: {str(e)}",
        })


def _build_parsed_jd(data: dict) -> ParsedJD:
    required = [
        Skill(
            name=s["name"],
            category=s.get("category", ""),
            tier=SkillTier.MUST_HAVE,
            claimed_level=None,
            years_mentioned=s.get("years_mentioned"),
        )
        for s in data.get("required_skills", [])
    ]
    preferred = [
        Skill(
            name=s["name"],
            category=s.get("category", ""),
            tier=SkillTier.NICE_TO_HAVE,
            claimed_level=None,
            years_mentioned=s.get("years_mentioned"),
        )
        for s in data.get("preferred_skills", [])
    ]
    return ParsedJD(
        job_title=data.get("job_title", "Software Engineer"),
        company=data.get("company", ""),
        seniority_level=data.get("seniority_level", ""),
        domain=data.get("domain", ""),
        required_skills=required,
        preferred_skills=preferred,
        raw_text="",
    )


def _build_parsed_resume(data: dict) -> ParsedResume:
    skills = [
        Skill(
            name=s["name"],
            category=s.get("category", ""),
            tier=SkillTier.MUST_HAVE,
            claimed_level=s.get("claimed_level"),
            years_mentioned=s.get("years_mentioned"),
        )
        for s in data.get("skills", [])
    ]
    return ParsedResume(
        candidate_name=data.get("candidate_name", "Candidate"),
        current_role=data.get("current_role", ""),
        years_experience=float(data.get("years_experience", 0)),
        skills=skills,
        education=data.get("education", []),
    )


def _build_skills_to_assess(
    parsed_jd: ParsedJD,
    parsed_resume: ParsedResume,
    settings,
) -> list[Skill]:
    """
    Build prioritised list of skills to assess.
    Strategy:
    - Must-have JD skills first (up to MAX_ASSESS cap)
    - Enrich with claimed_level from resume where available
    - Limit to a reasonable number to avoid candidate fatigue
    """
    MAX_SKILLS = 8  # Max skills to assess in one session

    resume_skill_map = {
        s.name.lower(): s for s in parsed_resume.skills
    }

    all_jd_skills = parsed_jd.required_skills + parsed_jd.preferred_skills

    enriched: list[Skill] = []
    for skill in all_jd_skills:
        resume_match = resume_skill_map.get(skill.name.lower())
        enriched.append(Skill(
            name=skill.name,
            category=skill.category,
            tier=skill.tier,
            claimed_level=resume_match.claimed_level if resume_match else None,
            years_mentioned=resume_match.years_mentioned if resume_match else None,
        ))

    # Sort: must_have first, then nice_to_have
    must_have = [s for s in enriched if s.tier == SkillTier.MUST_HAVE]
    nice_to_have = [s for s in enriched if s.tier == SkillTier.NICE_TO_HAVE]

    ordered = must_have + nice_to_have
    return ordered[:MAX_SKILLS]