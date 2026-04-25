"""
Domain models — the single source of truth for all data shapes
flowing through the agent graph.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class SkillTier(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    BONUS = "bonus"


class ProficiencyLevel(str, Enum):
    NO_KNOWLEDGE = "no_knowledge"          # 1
    SURFACE_AWARENESS = "surface_awareness"  # 2
    WORKING_KNOWLEDGE = "working_knowledge"  # 3
    PROFICIENT = "proficient"              # 4
    EXPERT = "expert"                      # 5


class SessionPhase(str, Enum):
    INITIALISED = "initialised"
    PARSING = "parsing"
    ASSESSING = "assessing"
    ANALYSING = "analysing"
    PLANNING = "planning"
    COMPLETE = "complete"
    ERROR = "error"


class ResourceType(str, Enum):
    COURSE = "course"
    BOOK = "book"
    VIDEO = "video"
    ARTICLE = "article"
    DOCUMENTATION = "documentation"
    PROJECT = "project"
    PRACTICE = "practice"


# ─────────────────────────────────────────────
# Skill models
# ─────────────────────────────────────────────

class Skill(BaseModel):
    name: str
    category: str = ""           # e.g. "Backend", "ML", "DevOps"
    tier: SkillTier = SkillTier.MUST_HAVE
    claimed_level: int | None = None   # 1-5 from resume; None if not on resume
    years_mentioned: float | None = None


class AssessmentQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    skill_name: str
    difficulty: int = Field(ge=1, le=5)   # 1=conceptual, 5=expert edge-case


class AssessmentAnswer(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    score: int = Field(ge=1, le=5)        # LLM-evaluated score
    reasoning: str                         # LLM explanation
    flags: list[str] = Field(default_factory=list)  # e.g. ["contradicts_earlier_answer"]


class SkillAssessmentState(BaseModel):
    """Live state for one skill being assessed."""
    skill: Skill
    questions_asked: list[AssessmentQuestion] = Field(default_factory=list)
    answers: list[AssessmentAnswer] = Field(default_factory=list)
    current_confidence: float = 0.0       # 0.0 – 1.0
    provisional_score: int = 0            # 1-5
    final_score: int | None = None
    final_level: ProficiencyLevel | None = None
    evidence_notes: list[str] = Field(default_factory=list)
    is_complete: bool = False


# ─────────────────────────────────────────────
# Gap & Learning Plan models
# ─────────────────────────────────────────────

class SkillGap(BaseModel):
    skill_name: str
    required_level: int              # From JD analysis
    assessed_level: int              # From assessment (1-5); 0 = not assessed / absent
    gap_size: int                    # required - assessed
    is_adjacent: bool = False        # Can be realistically acquired given current skills
    priority: int = 1                # 1 = highest


class LearningResource(BaseModel):
    title: str
    url: str
    resource_type: ResourceType
    platform: str = ""
    estimated_hours: float
    difficulty: int = Field(ge=1, le=5)
    is_free: bool = True
    description: str = ""


class SkillLearningPath(BaseModel):
    skill_name: str
    gap: SkillGap
    why_prioritised: str
    prerequisite_skills: list[str] = Field(default_factory=list)
    resources: list[LearningResource] = Field(default_factory=list)
    estimated_hours: float
    estimated_weeks: float           # At 10hrs/week
    milestones: list[str] = Field(default_factory=list)


class LearningPlan(BaseModel):
    total_estimated_hours: float
    total_estimated_weeks: float
    commitment_hours_per_week: int = 10
    executive_summary: str
    skill_paths: list[SkillLearningPath] = Field(default_factory=list)
    quick_wins: list[str] = Field(default_factory=list)     # Skills completable in < 1 week
    recommended_sequence: list[str] = Field(default_factory=list)  # Ordered skill names


# ─────────────────────────────────────────────
# Parsed resume / JD
# ─────────────────────────────────────────────

class ParsedJD(BaseModel):
    job_title: str
    company: str = ""
    required_skills: list[Skill] = Field(default_factory=list)
    preferred_skills: list[Skill] = Field(default_factory=list)
    seniority_level: str = ""
    domain: str = ""
    raw_text: str = ""


class ParsedResume(BaseModel):
    candidate_name: str = "Candidate"
    current_role: str = ""
    years_experience: float = 0
    skills: list[Skill] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    raw_text: str = ""


# ─────────────────────────────────────────────
# Master Graph State (passed through LangGraph)
# ─────────────────────────────────────────────

class GraphState(BaseModel):
    """
    The single state object that flows through every LangGraph node.
    Immutable fields set at init; mutable fields updated by nodes.
    """
    # Identity
    session_id: str
    phase: SessionPhase = SessionPhase.INITIALISED

    # Inputs (set once)
    jd_raw: str = ""
    resume_raw: str = ""

    # Parsed (set by parser node)
    parsed_jd: ParsedJD | None = None
    parsed_resume: ParsedResume | None = None
    skills_to_assess: list[Skill] = Field(default_factory=list)

    # Assessment state (updated each turn)
    skill_states: dict[str, SkillAssessmentState] = Field(default_factory=dict)
    current_skill_index: int = 0
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    pending_bot_message: str = ""       # Next message to stream to candidate
    awaiting_human_input: bool = False

    # Analysis & Plan (set at end)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    learning_plan: LearningPlan | None = None

    # Meta
    error_message: str = ""
    total_tokens_used: int = 0

    class Config:
        arbitrary_types_allowed = True


# ─────────────────────────────────────────────
# API Request / Response schemas
# ─────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    jd_text: str = Field(..., min_length=50, description="Full job description text")
    resume_text: str = Field(..., min_length=50, description="Full resume text")
    commitment_hours_per_week: int = Field(default=10, ge=1, le=40)


class StartSessionResponse(BaseModel):
    session_id: str
    message: str
    phase: SessionPhase
    candidate_name: str = ""
    skills_to_assess: list[str] = Field(default_factory=list)


class RespondRequest(BaseModel):
    message: str = Field(..., min_length=1)


class RespondResponse(BaseModel):
    session_id: str
    bot_message: str
    phase: SessionPhase
    progress: dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = False


class SessionReportResponse(BaseModel):
    session_id: str
    candidate_name: str
    job_title: str
    phase: SessionPhase
    assessed_skills: list[dict[str, Any]] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    learning_plan: LearningPlan | None = None
    overall_match_percent: float = 0.0