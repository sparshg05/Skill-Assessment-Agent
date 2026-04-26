"""
Assessment API routes.
Supports both regular JSON responses and SSE streaming.
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse

from agents import get_agent_runner, AgentRunner
from models import (
    StartSessionRequest, StartSessionResponse,
    RespondRequest, RespondResponse,
    SessionReportResponse,
)
from services import extract_text

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/assessment", tags=["assessment"])


def get_runner() -> AgentRunner:
    return get_agent_runner()


# ─────────────────────────────────────────────
# Start session — text input
# ─────────────────────────────────────────────

@router.post("/sessions", response_model=StartSessionResponse, status_code=201)
async def start_session(
    request: StartSessionRequest,
    runner: AgentRunner = Depends(get_runner),
) -> StartSessionResponse:
    """
    Start a new assessment session with raw text JD and resume.
    Returns the opening message and session ID.
    """
    try:
        logger.info("start_session_request")
        return await runner.start_session(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("start_session_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


# ─────────────────────────────────────────────
# Start session — file upload (PDF/DOCX)
# ─────────────────────────────────────────────

@router.post("/sessions/upload", response_model=StartSessionResponse, status_code=201)
async def start_session_upload(
    jd_file: UploadFile = File(..., description="Job description file (PDF/DOCX/TXT)"),
    resume_file: UploadFile = File(..., description="Resume file (PDF/DOCX/TXT)"),
    commitment_hours_per_week: int = Form(default=10),
    runner: AgentRunner = Depends(get_runner),
) -> StartSessionResponse:
    """
    Start an assessment session by uploading JD and resume files.
    Supports PDF, DOCX, and TXT formats.
    """
    try:
        jd_bytes = await jd_file.read()
        resume_bytes = await resume_file.read()

        jd_text = extract_text(jd_bytes, jd_file.filename or "jd.txt")
        resume_text = extract_text(resume_bytes, resume_file.filename or "resume.txt")

        request = StartSessionRequest(
            jd_text=jd_text,
            resume_text=resume_text,
            commitment_hours_per_week=commitment_hours_per_week,
        )
        return await runner.start_session(request)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("upload_session_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process files: {str(e)}")


# ─────────────────────────────────────────────
# Submit response (regular JSON)
# ─────────────────────────────────────────────

@router.post("/sessions/{session_id}/respond", response_model=RespondResponse)
async def respond(
    session_id: str,
    request: RespondRequest,
    runner: AgentRunner = Depends(get_runner),
) -> RespondResponse:
    """
    Submit a candidate's response to the current assessment question.
    Returns the next bot message and current progress.
    """
    try:
        return await runner.respond(session_id, request)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("respond_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Assessment error: {str(e)}")


# ─────────────────────────────────────────────
# Submit response — SSE streaming
# ─────────────────────────────────────────────

@router.post("/sessions/{session_id}/respond/stream")
async def respond_stream(
    session_id: str,
    request: RespondRequest,
    runner: AgentRunner = Depends(get_runner),
) -> StreamingResponse:
    """
    Submit a response and stream the bot reply via Server-Sent Events.
    Useful for real-time UX while the LLM generates the response.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send "thinking" event immediately
            yield _sse_event("status", {"status": "thinking"})

            response = await runner.respond(session_id, request)

            # Stream the message word by word for effect
            words = response.bot_message.split(" ")
            accumulated = []
            for word in words:
                accumulated.append(word)
                yield _sse_event("token", {"token": word + " "})

            # Send final complete event
            yield _sse_event("complete", {
                "message": response.bot_message,
                "phase": response.phase.value,
                "progress": response.progress,
                "is_complete": response.is_complete,
            })

        except ValueError as e:
            yield _sse_event("error", {"error": str(e), "code": 404})
        except Exception as e:
            logger.error("stream_error", session_id=session_id, error=str(e))
            yield _sse_event("error", {"error": "Internal error", "code": 500})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────────────
# Get session report
# ─────────────────────────────────────────────

@router.get("/sessions/{session_id}/report", response_model=SessionReportResponse)
async def get_report(
    session_id: str,
    runner: AgentRunner = Depends(get_runner),
) -> SessionReportResponse:
    """
    Retrieve the full assessment report and personalised learning plan.
    Available once the session phase is 'complete'.
    """
    try:
        return await runner.get_report(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("report_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# Health / session status
# ─────────────────────────────────────────────

@router.get("/sessions/{session_id}/status")
async def get_status(session_id: str, runner: AgentRunner = Depends(get_runner)):
    """Quick status check for a session."""
    from services import get_session_store
    store = get_session_store()
    state = await store.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "phase": state.phase.value,
        "progress": runner._build_progress(state),
        "awaiting_input": state.awaiting_human_input,
    }


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"