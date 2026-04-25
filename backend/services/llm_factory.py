"""
LLM Factory — provider-agnostic abstraction.
Swap between OpenAI and Anthropic via config without touching agent code.
"""
from __future__ import annotations

import json
import re
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

logger = structlog.get_logger(__name__)


def get_llm(model_override: str | None = None, temperature: float = 0.3) -> BaseChatModel:
    """
    Return the configured chat model.
    Falls back gracefully if one provider is not configured.
    """
    settings = get_settings()
    provider = settings.llm_provider
    model = model_override

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or settings.assessor_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "claude-3-5-sonnet-20241022",
            temperature=temperature,
            api_key=settings.anthropic_api_key,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_parser_llm() -> BaseChatModel:
    settings = get_settings()
    return get_llm(model_override=settings.parser_model, temperature=0.0)


def get_assessor_llm() -> BaseChatModel:
    settings = get_settings()
    return get_llm(model_override=settings.assessor_model, temperature=0.4)


def get_planner_llm() -> BaseChatModel:
    settings = get_settings()
    return get_llm(model_override=settings.planner_model, temperature=0.5)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm_json(
    llm: BaseChatModel,
    system_prompt: str,
    user_prompt: str,
    context: str = "",
) -> dict[str, Any] | list[Any]:
    """
    Call LLM and parse JSON response. Retries up to 3× on failure.
    Strips markdown fences before parsing.
    """
    messages = [SystemMessage(content=system_prompt)]
    if context:
        messages.append(HumanMessage(content=f"Context:\n{context}"))
    messages.append(HumanMessage(content=user_prompt))

    response = await llm.ainvoke(messages)
    raw = response.content

    # Track token usage if available
    usage = getattr(response, "usage_metadata", None)
    if usage:
        logger.debug("llm_tokens", input=usage.get("input_tokens"), output=usage.get("output_tokens"))

    return _parse_json(raw)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm_text(
    llm: BaseChatModel,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Call LLM and return plain text response."""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = await llm.ainvoke(messages)
    return response.content.strip()


def _parse_json(raw: str) -> dict[str, Any] | list[Any]:
    """Strip markdown fences and parse JSON robustly."""
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("json_parse_failed", raw=raw[:200], error=str(e))
        raise ValueError(f"LLM returned invalid JSON: {e}") from e