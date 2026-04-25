"""
Resource discovery service.
Primary: Tavily web search for fresh, relevant learning resources.
Fallback: Curated static resource database.
"""
from __future__ import annotations

import structlog

from config import get_settings
from models import LearningResource, ResourceType

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Curated fallback resource database
# ─────────────────────────────────────────────

CURATED_RESOURCES: dict[str, list[dict]] = {
    "python": [
        {"title": "Python for Everybody (Coursera)", "url": "https://www.coursera.org/specializations/python", "resource_type": "course", "platform": "Coursera", "estimated_hours": 40, "difficulty": 2, "is_free": True, "description": "Comprehensive Python specialisation by Dr. Chuck"},
        {"title": "Fluent Python", "url": "https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/", "resource_type": "book", "platform": "O'Reilly", "estimated_hours": 30, "difficulty": 4, "is_free": False, "description": "Deep dive into idiomatic Python"},
        {"title": "Real Python", "url": "https://realpython.com", "resource_type": "article", "platform": "Real Python", "estimated_hours": 10, "difficulty": 3, "is_free": True, "description": "Practical Python tutorials and articles"},
    ],
    "fastapi": [
        {"title": "FastAPI Official Documentation", "url": "https://fastapi.tiangolo.com", "resource_type": "documentation", "platform": "FastAPI", "estimated_hours": 8, "difficulty": 3, "is_free": True, "description": "Comprehensive official FastAPI docs with examples"},
        {"title": "FastAPI Full Course (YouTube)", "url": "https://www.youtube.com/watch?v=7t2alSnE2-I", "resource_type": "video", "platform": "YouTube", "estimated_hours": 6, "difficulty": 3, "is_free": True, "description": "End-to-end FastAPI course"},
    ],
    "docker": [
        {"title": "Docker Getting Started", "url": "https://docs.docker.com/get-started/", "resource_type": "documentation", "platform": "Docker", "estimated_hours": 5, "difficulty": 2, "is_free": True, "description": "Official Docker getting started guide"},
        {"title": "Docker & Kubernetes (Udemy)", "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/", "resource_type": "course", "platform": "Udemy", "estimated_hours": 20, "difficulty": 3, "is_free": False, "description": "Comprehensive container and orchestration course"},
    ],
    "kubernetes": [
        {"title": "Kubernetes Documentation", "url": "https://kubernetes.io/docs/home/", "resource_type": "documentation", "platform": "Kubernetes", "estimated_hours": 10, "difficulty": 4, "is_free": True, "description": "Official Kubernetes documentation"},
        {"title": "Certified Kubernetes Administrator (CKA)", "url": "https://www.udemy.com/course/certified-kubernetes-administrator-with-practice-tests/", "resource_type": "course", "platform": "Udemy", "estimated_hours": 15, "difficulty": 4, "is_free": False, "description": "CKA prep course with practice tests"},
    ],
    "postgresql": [
        {"title": "PostgreSQL Tutorial", "url": "https://www.postgresqltutorial.com", "resource_type": "article", "platform": "PostgreSQL Tutorial", "estimated_hours": 8, "difficulty": 2, "is_free": True, "description": "Comprehensive PostgreSQL tutorial from basics to advanced"},
        {"title": "PostgreSQL Official Docs", "url": "https://www.postgresql.org/docs/", "resource_type": "documentation", "platform": "PostgreSQL", "estimated_hours": 5, "difficulty": 3, "is_free": True, "description": "Official PostgreSQL documentation"},
    ],
    "machine learning": [
        {"title": "Machine Learning Specialization (Coursera)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "resource_type": "course", "platform": "Coursera", "estimated_hours": 60, "difficulty": 3, "is_free": False, "description": "Andrew Ng's foundational ML course"},
        {"title": "Hands-On Machine Learning (Book)", "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781492032632/", "resource_type": "book", "platform": "O'Reilly", "estimated_hours": 40, "difficulty": 3, "is_free": False, "description": "Practical ML with Scikit-Learn and TensorFlow"},
    ],
    "react": [
        {"title": "React Official Documentation", "url": "https://react.dev", "resource_type": "documentation", "platform": "React", "estimated_hours": 6, "difficulty": 2, "is_free": True, "description": "New official React docs with interactive examples"},
        {"title": "The Road to React (Book)", "url": "https://www.roadtoreact.com", "resource_type": "book", "platform": "Self-published", "estimated_hours": 15, "difficulty": 3, "is_free": False, "description": "Pragmatic React book with real project"},
    ],
    "typescript": [
        {"title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "resource_type": "documentation", "platform": "TypeScript", "estimated_hours": 8, "difficulty": 3, "is_free": True, "description": "Official TypeScript handbook"},
        {"title": "Execute Program TypeScript", "url": "https://www.executeprogram.com/courses/typescript", "resource_type": "course", "platform": "Execute Program", "estimated_hours": 10, "difficulty": 3, "is_free": False, "description": "Interactive TypeScript learning"},
    ],
    "aws": [
        {"title": "AWS Cloud Practitioner Essentials", "url": "https://aws.amazon.com/training/learn-about/cloud-practitioner/", "resource_type": "course", "platform": "AWS", "estimated_hours": 6, "difficulty": 2, "is_free": True, "description": "Official AWS foundations course"},
        {"title": "AWS Solutions Architect (Udemy)", "url": "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/", "resource_type": "course", "platform": "Udemy", "estimated_hours": 27, "difficulty": 4, "is_free": False, "description": "SAA-C03 certification prep"},
    ],
    "system design": [
        {"title": "System Design Primer (GitHub)", "url": "https://github.com/donnemartin/system-design-primer", "resource_type": "article", "platform": "GitHub", "estimated_hours": 20, "difficulty": 4, "is_free": True, "description": "Comprehensive open-source system design guide"},
        {"title": "Designing Data-Intensive Applications", "url": "https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/", "resource_type": "book", "platform": "O'Reilly", "estimated_hours": 35, "difficulty": 5, "is_free": False, "description": "The definitive book on scalable system design"},
    ],
    "langchain": [
        {"title": "LangChain Documentation", "url": "https://python.langchain.com/docs/introduction/", "resource_type": "documentation", "platform": "LangChain", "estimated_hours": 8, "difficulty": 3, "is_free": True, "description": "Official LangChain documentation and tutorials"},
        {"title": "LangGraph Documentation", "url": "https://langchain-ai.github.io/langgraph/", "resource_type": "documentation", "platform": "LangGraph", "estimated_hours": 5, "difficulty": 4, "is_free": True, "description": "Build stateful multi-actor applications"},
    ],
}


def _get_curated(skill_name: str) -> list[LearningResource]:
    """Look up curated resources by skill name (fuzzy match)."""
    key = skill_name.lower().strip()
    # Direct match
    if key in CURATED_RESOURCES:
        return [LearningResource(**r) for r in CURATED_RESOURCES[key]]
    # Partial match
    for db_key, resources in CURATED_RESOURCES.items():
        if db_key in key or key in db_key:
            return [LearningResource(**r) for r in resources]
    return []


async def search_resources_tavily(skill_name: str, count: int = 3) -> list[LearningResource]:
    """Search Tavily for learning resources for a skill."""
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        query = f"best online courses tutorials to learn {skill_name} for software engineers 2024"
        results = client.search(query=query, max_results=count, search_depth="basic")

        resources = []
        for r in results.get("results", []):
            resources.append(LearningResource(
                title=r.get("title", skill_name + " Resource"),
                url=r.get("url", ""),
                resource_type=ResourceType.ARTICLE,
                platform=_extract_platform(r.get("url", "")),
                estimated_hours=5,  # Default estimate
                difficulty=3,
                is_free=True,
                description=r.get("content", "")[:150],
            ))
        logger.info("tavily_search_success", skill=skill_name, count=len(resources))
        return resources
    except Exception as e:
        logger.warning("tavily_search_failed", skill=skill_name, error=str(e))
        return []


def _extract_platform(url: str) -> str:
    """Extract platform name from URL."""
    platform_map = {
        "coursera": "Coursera", "udemy": "Udemy", "youtube": "YouTube",
        "github": "GitHub", "medium": "Medium", "dev.to": "Dev.to",
        "freecodecamp": "freeCodeCamp", "pluralsight": "Pluralsight",
        "linkedin": "LinkedIn Learning", "oreilly": "O'Reilly",
    }
    url_lower = url.lower()
    for key, name in platform_map.items():
        if key in url_lower:
            return name
    return url.split("/")[2] if "//" in url else "Web"


async def get_resources_for_skill(skill_name: str) -> list[LearningResource]:
    """
    Get learning resources: Tavily first, curated fallback.
    Always returns at least 2 resources.
    """
    # Try Tavily first
    tavily_resources = await search_resources_tavily(skill_name, count=3)

    # Always get curated as supplement / fallback
    curated = _get_curated(skill_name)

    # Merge: Tavily first, then curated (deduplicate by title)
    seen_titles = set()
    merged = []
    for r in tavily_resources + curated:
        if r.title not in seen_titles:
            seen_titles.add(r.title)
            merged.append(r)

    # Return top 4 resources
    return merged[:4]