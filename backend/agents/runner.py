"""
Agent Runner — the service layer between the API and the LangGraph orchestrator.

Responsibilities:
- Create and initialise sessions
- Resume sessions from Redis on each API call
- Run the graph forward by one "step" (up to the next human interrupt)
- Persist updated state back to Redis
"""
from __future__ import annotations

from uuid import uuid4

import structlog

from models import (
    GraphState, SessionPhase,
    StartSessionRequest, StartSessionResponse,
    RespondRequest, RespondResponse,
    SessionReportResponse,
)
from services import get_session_store
from nodes import (
    parser_node,
    generate_opening_message,
    assessment_node,
    gap_analysis_node,
    learning_plan_node,
)

logger = structlog.get_logger(__name__)


class AgentRunner:
    """
    Stateless service — all state lives in Redis.
    Each method loads state → runs one graph step → saves state → returns response.
    """

    def __init__(self) -> None:
        self.store = get_session_store()

    async def start_session(self, request: StartSessionRequest) -> StartSessionResponse:
        """
        Initialise a new assessment session.
        Runs: parser_node → opening_message_node
        Returns the opening message to the candidate.
        """
        session_id = str(uuid4())
        logger.info("session_start", session_id=session_id)

        # Create initial state
        state = GraphState(
            session_id=session_id,
            phase=SessionPhase.PARSING,
            jd_raw=request.jd_text,
            resume_raw=request.resume_text,
        )
        # Store commitment for later use in learning plan
        # (attach as extra field via model_copy trick)
        state = state.model_copy(update={"_commitment": request.commitment_hours_per_week})

        # Step 1: Parse
        state = await parser_node(state)
        if state.phase == SessionPhase.ERROR:
            raise ValueError(state.error_message)

        # Step 2: Generate opening message
        state = await generate_opening_message(state)

        # Persist
        await self.store.save(state)

        return StartSessionResponse(
            session_id=session_id,
            message=state.pending_bot_message,
            phase=state.phase,
            candidate_name=state.parsed_resume.candidate_name if state.parsed_resume else "",
            skills_to_assess=[s.name for s in state.skills_to_assess],
        )

    async def respond(self, session_id: str, request: RespondRequest) -> RespondResponse:
        """
        Process a candidate's response.
        Runs one assessment step and returns the next bot message.
        May trigger gap analysis + learning plan if assessment is complete.
        """
        # Load state
        state = await self.store.load(session_id)
        if state is None:
            raise ValueError(f"Session {session_id} not found or expired")

        # Append candidate message to history
        updated_history = list(state.conversation_history) + [
            {"role": "human", "content": request.message}
        ]
        state = state.model_copy(update={
            "conversation_history": updated_history,
            "awaiting_human_input": False,
        })

        # Run assessment step
        state = await assessment_node(state)

        # Append bot message to history
        if state.pending_bot_message:
            updated_history = list(state.conversation_history) + [
                {"role": "assistant", "content": state.pending_bot_message}
            ]
            state = state.model_copy(update={"conversation_history": updated_history})

        # If assessment complete → run analysis + planning pipeline
        if state.phase == SessionPhase.ANALYSING:
            state = await gap_analysis_node(state)
            if state.phase != SessionPhase.ERROR:
                # Recover commitment from session
                commitment = getattr(state, "_commitment", 10) or 10
                state = state.model_copy()
                state = await learning_plan_node(state)

        is_complete = state.phase == SessionPhase.COMPLETE

        # Build progress info
        progress = self._build_progress(state)

        # Persist updated state
        await self.store.save(state)

        return RespondResponse(
            session_id=session_id,
            bot_message=state.pending_bot_message or "",
            phase=state.phase,
            progress=progress,
            is_complete=is_complete,
        )

    async def get_report(self, session_id: str) -> SessionReportResponse:
        """Return the full assessment report + learning plan."""
        state = await self.store.load(session_id)
        if state is None:
            raise ValueError(f"Session {session_id} not found")

        # Build assessed skills summary
        assessed_skills = []
        for skill_name, skill_state in state.skill_states.items():
            assessed_skills.append({
                "skill": skill_name,
                "claimed_level": skill_state.skill.claimed_level,
                "assessed_score": skill_state.final_score or skill_state.provisional_score,
                "level": skill_state.final_level.value if skill_state.final_level else "unknown",
                "tier": skill_state.skill.tier.value,
                "questions_asked": len(skill_state.questions_asked),
                "evidence": skill_state.evidence_notes[-1] if skill_state.evidence_notes else "",
            })

        # Calculate overall match %
        match_pct = self._calculate_match(state)

        return SessionReportResponse(
            session_id=session_id,
            candidate_name=state.parsed_resume.candidate_name if state.parsed_resume else "",
            job_title=state.parsed_jd.job_title if state.parsed_jd else "",
            phase=state.phase,
            assessed_skills=assessed_skills,
            skill_gaps=state.skill_gaps,
            learning_plan=state.learning_plan,
            overall_match_percent=match_pct,
        )

    def _build_progress(self, state: GraphState) -> dict:
        total = len(state.skills_to_assess)
        completed = sum(1 for s in state.skill_states.values() if s.is_complete)
        current = state.skills_to_assess[state.current_skill_index].name \
            if state.current_skill_index < total else None

        return {
            "total_skills": total,
            "completed_skills": completed,
            "current_skill": current,
            "percent_complete": round((completed / total * 100) if total > 0 else 0),
            "phase": state.phase.value,
        }

    def _calculate_match(self, state: GraphState) -> float:
        if not state.skill_states:
            return 0.0
        scores = [
            (s.final_score or s.provisional_score)
            for s in state.skill_states.values()
        ]
        if not scores:
            return 0.0
        # Match % = avg score / 5 * 100
        return round(sum(scores) / len(scores) / 5 * 100, 1)


# Singleton
_runner: AgentRunner | None = None


def get_agent_runner() -> AgentRunner:
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner