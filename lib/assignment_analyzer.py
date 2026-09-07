"""Instant local + optional LLM assignment analysis."""

import os
import re

from lib.syllabus import (
    ALLOWED_SYLLABUS_TOPICS,
    ALLOWED_TOPIC_IDS,
    FORBIDDEN_KEYWORDS,
    SYLLABUS_TITLE,
)

TOPIC_ORDER = list(ALLOWED_SYLLABUS_TOPICS.keys())

# Keywords that suggest each syllabus topic in assignment text
TOPIC_SIGNALS: dict[str, list[str]] = {
    "schema_design": [
        "schema", "mongoose schema", "field type", "fields", "enum", "default value",
        "defaults", "model design", "define a schema", "schema with",
    ],
    "crud_operations": [
        "crud", "create", "read", "update", "delete", "post /", "get /", "put /",
        "patch /", "insert", "findbyid", "findone", "save()", "create document",
    ],
    "aggregation_pipeline": [
        "aggregation", "aggregate", "$lookup", "$group", "$match", "$project",
        "pipeline", "join collection", "joining collection", "combine collection",
    ],
    "indexing": [
        "index", "compound index", "index: true", "performance", "indexed field",
        "createindex", "ensureindex",
    ],
    "data_validation": [
        "validation", "validate", "required", "min", "max", "unique", "enum",
        "validator", "constraint", "minlength", "maxlength",
    ],
    "pagination_and_sorting": [
        "pagination", "paginate", "page", "limit", "skip", "sort", "sorting",
        "query param", "per page", ".skip(", ".limit(", ".sort(",
    ],
    "relationships": [
        "relationship", "populate", "ref:", "reference", "embedding", "embedded",
        "foreign key", "join", "related collection", "parent", "child document",
    ],
    "error_handling": [
        "error handling", "try/catch", "try catch", "status code", "400", "404",
        "500", "error message", "meaningful error", "handle error", "not found",
    ],
}

OUT_OF_SYLLABUS_SIGNALS: dict[str, str] = {
    "jwt": "Authentication (JWT) is not in the syllabus",
    "oauth": "Authentication (OAuth) is not in the syllabus",
    "authentication": "Authentication is not in the syllabus",
    "login": "Login/auth is not in the syllabus",
    "signup": "Signup/auth is not in the syllabus",
    "passport": "Passport auth is not in the syllabus",
    "websocket": "WebSockets are not in the syllabus",
    "socket.io": "WebSockets are not in the syllabus",
    "file upload": "File uploads are not in the syllabus",
    "multer": "File uploads are not in the syllabus",
    "redis": "Redis is not in the syllabus",
    "graphql": "GraphQL is not in the syllabus",
    "postgresql": "SQL databases are not in the syllabus",
    "mysql": "SQL databases are not in the syllabus",
    "prisma": "Non-Mongoose ORMs are not in the syllabus",
}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _sentence_matches(sentence: str, signals: list[str]) -> bool:
    lower = sentence.lower()
    return any(sig in lower for sig in signals)


def _concepts_for_topic(sentences: list[str], topic_id: str, limit: int = 4) -> list[str]:
    signals = TOPIC_SIGNALS[topic_id]
    concepts = []
    for sentence in sentences:
        if _sentence_matches(sentence, signals):
            concept = sentence.strip()
            if len(concept) > 120:
                concept = concept[:117] + "..."
            if concept not in concepts:
                concepts.append(concept)
        if len(concepts) >= limit:
            break
    if not concepts and sentences:
        label = ALLOWED_SYLLABUS_TOPICS[topic_id].split("(")[0].strip()
        concepts.append(f"Implement {label.lower()} requirements from the assignment")
    return concepts[:limit]


def _build_result(enriched: list, out_of_syllabus: list, summary: str) -> dict:
    covered_concepts = []
    for topic in enriched:
        if topic["covered"]:
            for concept in topic["concepts"]:
                covered_concepts.append({
                    "topic_id": topic["topic_id"],
                    "topic_label": topic["label"],
                    "concept": concept,
                })
    uncovered = [t for t in enriched if not t["covered"]]
    return {
        "summary": summary,
        "syllabus_coverage": enriched,
        "out_of_syllabus_concepts": out_of_syllabus,
        "covered_concepts": covered_concepts,
        "uncovered_topics": [
            {"topic_id": t["topic_id"], "label": t["label"]} for t in uncovered
        ],
        "covered_topic_count": sum(1 for t in enriched if t["covered"]),
        "uncovered_topic_count": len(uncovered),
        "analysis_mode": "local",
    }


def analyze_assignment_local(text: str) -> dict:
    """Instant keyword-based syllabus mapping (no API call)."""
    text = (text or "").strip()
    if len(text) < 30:
        from lib.claude_client import GenerationError
        raise GenerationError("Assignment text is too short to analyze (minimum ~30 characters).")

    lower = text.lower()
    sentences = _sentences(text)
    enriched = []

    for topic_id in TOPIC_ORDER:
        signals = TOPIC_SIGNALS[topic_id]
        hit_count = sum(1 for sig in signals if sig in lower)
        covered = hit_count >= 1
        concepts = _concepts_for_topic(sentences, topic_id) if covered else []
        enriched.append({
            "topic_id": topic_id,
            "label": ALLOWED_SYLLABUS_TOPICS[topic_id],
            "covered": covered,
            "concepts": concepts,
        })

    out_of_syllabus = []
    for kw, reason in OUT_OF_SYLLABUS_SIGNALS.items():
        if kw in lower:
            for sentence in sentences:
                if kw in sentence.lower():
                    out_of_syllabus.append({"concept": sentence[:120], "reason": reason})
                    break
            else:
                out_of_syllabus.append({"concept": kw, "reason": reason})

    covered_n = sum(1 for t in enriched if t["covered"])
    summary = (
        f"Local scan of the assignment against {SYLLABUS_TITLE}: "
        f"{covered_n} of {len(TOPIC_ORDER)} syllabus topics detected."
    )
    return _build_result(enriched, out_of_syllabus, summary)


def analyze_assignment(text: str) -> dict:
    """Analyze assignment — local (instant) unless LLM_ANALYZE=true."""
    use_llm = (os.getenv("LLM_ANALYZE") or "").strip().lower() in ("1", "true", "yes")
    result = analyze_assignment_local(text)
    result["assignment_text"] = text.strip()
    if use_llm:
        from lib.assignment_analyzer_llm import analyze_assignment_llm
        result = analyze_assignment_llm(text)
        result["analysis_mode"] = "llm"
    return result


def build_spec_from_selection(
    selected_concepts: list[dict],
    assignment_text: str | None = None,
) -> tuple[str, list[str]]:
    """Build generation spec from user-selected concepts."""
    from lib.claude_client import GenerationError

    if not selected_concepts:
        raise GenerationError("Select at least one covered concept to generate a question.")

    topic_ids = []
    lines = [
        "Build one MongoDB/Mongoose examination question that assesses ALL of the "
        "following concepts extracted from a company assignment:",
        "",
    ]

    for i, item in enumerate(selected_concepts, 1):
        topic_id = item.get("topic_id", "")
        concept = (item.get("concept") or "").strip()
        if topic_id not in ALLOWED_TOPIC_IDS:
            raise GenerationError(f"Invalid topic in selection: {topic_id}")
        if not concept:
            raise GenerationError("Selected concept text is empty.")
        if topic_id not in topic_ids:
            topic_ids.append(topic_id)
        label = ALLOWED_SYLLABUS_TOPICS.get(topic_id, topic_id)
        lines.append(f"{i}. [{label}] {concept}")

    if assignment_text and assignment_text.strip():
        excerpt = assignment_text.strip()[:3000]
        lines.extend([
            "",
            "Original assignment context (for scenario/domain inspiration only):",
            excerpt,
        ])

    return "\n".join(lines), topic_ids
