"""Canonical syllabus for MongoDB Integration & Data Management questions."""

SYLLABUS_TITLE = "MongoDB Integration & Data Management"

SYLLABUS_DESCRIPTION = (
    "Understanding how to use MongoDB in a Node.js application for storing and "
    "managing application data. Includes schema design, CRUD operations, aggregation "
    "pipeline (for joining collections), indexing for performance, data validation, "
    "pagination and sorting, handling relationships between collections, and basic "
    "error handling for reliable database operations."
)

# Canonical topic IDs — every question must use only these
ALLOWED_SYLLABUS_TOPICS: dict[str, str] = {
    "schema_design": "Schema design (Mongoose schemas, field types, defaults, enums)",
    "crud_operations": "CRUD operations (Create, Read, Update, Delete via Mongoose)",
    "aggregation_pipeline": (
        "Aggregation pipeline for joining/combining collections "
        "($lookup, $group, $match, $project)"
    ),
    "indexing": "Indexing for performance (index: true, compound indexes)",
    "data_validation": (
        "Data validation (required, min/max, enum, custom validators, unique constraints)"
    ),
    "pagination_and_sorting": (
        "Pagination and sorting (.skip(), .limit(), .sort(), query params)"
    ),
    "relationships": (
        "Relationships between collections (refs, populate(), embedding vs referencing)"
    ),
    "error_handling": (
        "Basic error handling (try/catch, status codes, meaningful messages, 400/404)"
    ),
}

ALLOWED_TOPIC_IDS = frozenset(ALLOWED_SYLLABUS_TOPICS.keys())

# Technologies / topics outside syllabus — reject in generated output and user specs
FORBIDDEN_KEYWORDS = [
    "postgresql",
    "postgres",
    "mysql",
    "sqlite",
    "prisma",
    "sequelize",
    "typeorm",
    "graphql",
    "redis",
    "dynamodb",
    "firebase",
    "supabase",
    "jwt",
    "oauth",
    "passport.js",
    "passport",
    "websocket",
    "socket.io",
    "multer",
    "aws s3",
    "file upload",
    "nodemailer",
    "bcrypt",
    "authentication",
    "authorization",
    "login",
    "signup",
    "session store",
]

# Keywords suggesting syllabus-aligned content (used in response validation)
SYLLABUS_CONTENT_KEYWORDS = [
    "mongoose",
    "schema",
    "express",
    "mongodb",
    "aggregate",
    "lookup",
    "populate",
    "index",
    "pagination",
    "sort",
    "skip",
    "limit",
    "validation",
    "required",
    "enum",
    "crud",
    "router",
    "supertest",
    "400",
    "404",
]


def format_syllabus_for_prompt() -> str:
    lines = [
        f"## {SYLLABUS_TITLE}",
        "",
        SYLLABUS_DESCRIPTION,
        "",
        "Every question MUST assess one or more of these topics ONLY:",
        "",
    ]
    for i, (topic_id, description) in enumerate(ALLOWED_SYLLABUS_TOPICS.items(), 1):
        lines.append(f"{i}. `{topic_id}` — {description}")
    lines.extend([
        "",
        "Do NOT generate questions about: authentication, JWT/OAuth, file uploads, "
        "WebSockets, caching, email, cloud storage, SQL/NoSQL databases other than "
        "MongoDB via Mongoose, or any ORM other than Mongoose.",
    ])
    return "\n".join(lines)


def validate_user_spec(spec: str) -> None:
    """Raise ValueError if the user's concept is clearly outside syllabus."""
    lower = spec.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in lower:
            raise ValueError(
                f"Concept is outside the syllabus (matched: '{kw}'). "
                f"Questions must stay within {SYLLABUS_TITLE} only."
            )
