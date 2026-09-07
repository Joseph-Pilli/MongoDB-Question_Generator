"""Question generation with JSON validation and retry."""

import json
import random
import re
import string
from pathlib import Path

from lib.file_spec_parser import FileConstraints, apply_file_constraints, merge_constraints
from lib.llm_client import LLMError, call_llm
from lib.syllabus import (
    ALLOWED_TOPIC_IDS,
    ALLOWED_SYLLABUS_TOPICS,
    FORBIDDEN_KEYWORDS,
    SYLLABUS_CONTENT_KEYWORDS,
    format_syllabus_for_prompt,
    validate_user_spec,
)

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system_prompt.md"
README_REFERENCE_PATH = ROOT / "prompts" / "readme_reference.md"

INJECTED_PATHS = {"db.js", "README.md", ".gitignore", "package.json"}
DEFAULT_SCAFFOLD_FILES = ("server.js", "app.http")

# Prefilled must be empty/comment-only for these paths (student implements everything).
EMPTY_PREFILLED_PREFIXES = (
    "models/", "controllers/", "routes/",
    "validators/", "middleware/", "services/", "utils/",
)
# Every file under these folders must be listed in student_files.
MANDATORY_STUDENT_PREFIXES = ("models/", "controllers/", "routes/")

IMPLEMENTABLE_PREFIXES = EMPTY_PREFILLED_PREFIXES

REQUIRED_TOP_KEYS = {
    "question_title",
    "readme_md",
    "syllabus_topics",
    "student_files",
    "file_structure_rationale",
    "prefilled",
    "solution",
    "tests",
}


class GenerationError(Exception):
    pass


def _load_system_prompt() -> str:
    template = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    readme_ref = README_REFERENCE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{SYLLABUS}}", format_syllabus_for_prompt())
        .replace("{{README_REFERENCE}}", readme_ref)
    )


def parse_file_list(raw: str | list | None) -> list[str]:
    """Parse comma- or newline-separated file paths."""
    if not raw:
        return []
    items = raw if isinstance(raw, list) else re.split(r"[\n,]+", str(raw))
    paths: list[str] = []
    seen: set[str] = set()
    for item in items:
        path = item.strip().replace("\\", "/")
        if not path or path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def _new_njscpa_id(used: set[str]) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        candidate = "NJSCPA" + "".join(random.choices(alphabet, k=5))
        if candidate not in used:
            used.add(candidate)
            return candidate


def _ensure_unique_test_ids(test_content: str) -> str:
    """Replace duplicate NJSCPA IDs in it() titles with fresh unique IDs."""
    used: set[str] = set()

    def repl(match: re.Match) -> str:
        quote, test_id, description = match.group(1), match.group(2), match.group(3)
        if test_id in used:
            test_id = _new_njscpa_id(used)
        else:
            used.add(test_id)
        return f'it({quote}:::{test_id}:::{description}{quote}'

    return re.sub(
        r'it\s*\(\s*(["\']):::(NJSCPA[A-Za-z0-9]{5}):::([^"\']*)\1',
        repl,
        test_content,
    )


def _normalize_test_file_ids(data: dict) -> None:
    tests = data.get("tests")
    if not isinstance(tests, dict):
        return
    for path, content in list(tests.items()):
        if "index.test.js" in path.replace("\\", "/") and isinstance(content, str):
            tests[path] = _ensure_unique_test_ids(content)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    candidates: list[str] = [text.strip()]
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidates.append(match.group())

    errors: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            errors.append(str(e))

    try:
        from json_repair import repair_json

        for candidate in candidates:
            if not candidate:
                continue
            repaired = repair_json(candidate)
            return json.loads(repaired)
    except Exception as e:
        errors.append(f"json-repair failed: {e}")

    detail = errors[0] if errors else "unknown parse error"
    raise GenerationError(f"Invalid JSON from model: {detail}")


def _normalize_paths(files: dict) -> set[str]:
    return {p.replace("\\", "/") for p in files.keys()}


def _is_empty_or_comment_only(content: str) -> bool:
    """True if file is blank or only // comment lines (allowed prefilled student stub)."""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        return False
    return True


def _validate_syllabus_topics(topics: list) -> None:
    if not isinstance(topics, list) or not topics:
        raise GenerationError("syllabus_topics must be a non-empty list")

    invalid = [t for t in topics if t not in ALLOWED_TOPIC_IDS]
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_TOPIC_IDS))
        raise GenerationError(
            f"Invalid syllabus_topics: {invalid}. Allowed: {allowed}"
        )


def _validate_file_maps(
    prefilled: dict,
    solution: dict,
    student_files: list,
    user_student_files: list[str] | None = None,
    user_scaffold_files: list[str] | None = None,
    forbidden_layers: set[str] | None = None,
) -> None:
    if not isinstance(prefilled, dict) or not prefilled:
        raise GenerationError("Empty or invalid 'prefilled' file map")
    if not isinstance(solution, dict) or not solution:
        raise GenerationError("Empty or invalid 'solution' file map")

    pre_paths = _normalize_paths(prefilled)
    sol_paths = _normalize_paths(solution)

    if pre_paths != sol_paths:
        only_pre = pre_paths - sol_paths
        only_sol = sol_paths - pre_paths
        raise GenerationError(
            f"prefilled and solution file paths must match. "
            f"Only in prefilled: {only_pre or '{}'}, only in solution: {only_sol or '{}'}"
        )

    for required in ("server.js", "app.http"):
        if required not in pre_paths:
            raise GenerationError(f"Missing required file: {required}")

    if forbidden_layers:
        for path in pre_paths:
            for layer in forbidden_layers:
                if path.startswith(f"{layer}/"):
                    raise GenerationError(
                        f"User query did not request `{layer}/` but package includes: {path}"
                    )

    if not isinstance(student_files, list) or not student_files:
        raise GenerationError("student_files must be a non-empty list")

    normalized_student = {p.replace("\\", "/") for p in student_files}
    for path in normalized_student:
        if path in INJECTED_PATHS:
            raise GenerationError(f"student_files cannot include injected path: {path}")
        if path not in pre_paths:
            raise GenerationError(f"student_files path not in file maps: {path}")

    if user_student_files is not None:
        expected = {p.replace("\\", "/") for p in user_student_files}
        if normalized_student != expected:
            raise GenerationError(
                f"student_files must match user specification. "
                f"Expected: {sorted(expected)}, got: {sorted(normalized_student)}"
            )

    scaffold_in_package = {
        p for p in pre_paths
        if p not in normalized_student and p not in INJECTED_PATHS
    }
    if user_scaffold_files is not None:
        expected_scaffold = {p.replace("\\", "/") for p in user_scaffold_files}
        if scaffold_in_package != expected_scaffold:
            raise GenerationError(
                f"Scaffold files must match user specification. "
                f"Expected: {sorted(expected_scaffold)}, got: {sorted(scaffold_in_package)}"
            )

    if user_scaffold_files is not None:
        overlap = normalized_student & {p.replace("\\", "/") for p in user_scaffold_files}
        if overlap:
            raise GenerationError(f"Files cannot be both student and scaffold: {sorted(overlap)}")

    if not normalized_student:
        raise GenerationError("student_files must be a non-empty list")

    if not any(p.startswith(MANDATORY_STUDENT_PREFIXES) for p in normalized_student):
        raise GenerationError(
            "student_files must include at least one file under models/, controllers/, or routes/"
        )

    for path in pre_paths:
        if not path.startswith(IMPLEMENTABLE_PREFIXES):
            continue
        content = prefilled.get(path, "")
        if path in normalized_student:
            if not _is_empty_or_comment_only(content):
                raise GenerationError(
                    f"Prefilled must be empty or comment-only for student file: {path}"
                )
            if not (solution.get(path) or "").strip():
                raise GenerationError(f"Solution is empty for student file: {path}")
        elif _is_empty_or_comment_only(content):
            raise GenerationError(
                f"Scaffold file must be complete in prefilled (not empty): {path}"
            )

    for path in normalized_student:
        if path.startswith(IMPLEMENTABLE_PREFIXES):
            continue
        stub = prefilled.get(path, "")
        solution_content = solution.get(path, "")
        if stub.strip() == solution_content.strip():
            raise GenerationError(
                f"Prefilled and solution are identical for student file: {path}"
            )


def _validate_readme(readme_md: str, student_files: list[str]) -> None:
    readme = (readme_md or "").strip()
    if len(readme) < 200:
        raise GenerationError("readme_md is missing or too short")

    required_markers = [
        "## Database",
        "## API Endpoints",
        "## Folder Structure",
        "<MultiLineNote>",
        "Pre-filled files",
        "Files students must write",
    ]
    missing = [m for m in required_markers if m not in readme]
    if missing:
        raise GenerationError(f"README missing required sections: {missing}")

    for path in student_files:
        if path not in readme:
            raise GenerationError(f"README must mention student file: {path}")


def validate_response(
    data: dict,
    user_student_files: list[str] | None = None,
    user_scaffold_files: list[str] | None = None,
    user_title: str | None = None,
    forbidden_layers: set[str] | None = None,
) -> None:
    if "error" in data and "question_title" not in data:
        raise GenerationError(data["error"])

    missing = REQUIRED_TOP_KEYS - set(data.keys())
    if missing:
        raise GenerationError(f"Missing top-level keys: {missing}")

    _validate_syllabus_topics(data.get("syllabus_topics", []))

    rationale = (data.get("file_structure_rationale") or "").strip()
    if len(rationale) < 20:
        raise GenerationError("file_structure_rationale is missing or too short")

    _validate_file_maps(
        data.get("prefilled", {}),
        data.get("solution", {}),
        data.get("student_files", []),
        user_student_files=user_student_files,
        user_scaffold_files=user_scaffold_files,
        forbidden_layers=forbidden_layers,
    )

    student_files = [p.replace("\\", "/") for p in data.get("student_files", [])]
    _validate_readme(data.get("readme_md", ""), student_files)

    if user_title:
        data["question_title"] = user_title.strip()

    tests = data.get("tests", {})
    if not isinstance(tests, dict) or not tests:
        raise GenerationError("Empty or invalid 'tests' file map")

    test_content = ""
    for path, content in tests.items():
        if "index.test.js" in path.replace("\\", "/"):
            test_content = content
            break

    if not test_content:
        raise GenerationError("No .tests/index.test.js found in tests")

    combined = json.dumps(data).lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in combined:
            raise GenerationError(f"Response contains out-of-syllabus keyword: {kw}")

    syllabus_hits = sum(1 for kw in SYLLABUS_CONTENT_KEYWORDS if kw in combined)
    if syllabus_hits < 3:
        raise GenerationError("Response does not appear to cover syllabus topics")

    if not re.search(r":::NJSCPA[A-Za-z0-9]{5}_TEST_SUITE:::", test_content):
        raise GenerationError(
            "Test file missing suite tag in format :::NJSCPA<5_ALNUM>_TEST_SUITE:::"
        )

    it_tags = re.findall(r'it\s*\(\s*["\']:::(NJSCPA[A-Za-z0-9]{5}):::', test_content)
    if len(it_tags) < 2:
        raise GenerationError(
            "Test file needs at least 2 it() blocks with :::NJSCPA<5_ALNUM>::: tags"
        )

    if len(set(it_tags)) != len(it_tags):
        raise GenerationError("Duplicate test IDs found in it() titles")


def _build_user_message(
    spec: str,
    domain: str | None,
    question_title: str | None = None,
    student_files: list[str] | None = None,
    scaffold_files: list[str] | None = None,
    file_constraints: FileConstraints | None = None,
) -> str:
    parts = [f"Concept / Spec:\n{spec.strip()}"]

    if question_title and question_title.strip():
        parts.append(f"Question title (use exactly): {question_title.strip()}")
    else:
        parts.append("Question title: (not provided — choose a suitable title for the scenario)")

    if domain and domain.strip():
        parts.append(f"Domain: {domain.strip()}")
    else:
        parts.append("Domain: (not specified — pick an appropriate business domain)")

    if student_files:
        parts.append(
            "Files students MUST implement (empty in prefilled, full code in solution):\n"
            + "\n".join(f"- {p}" for p in student_files)
            + "\n\nDo NOT add any other implementable files or folders beyond this list."
        )
    elif file_constraints and file_constraints.student_files:
        parts.append(
            "Files students MUST implement (parsed from user query — use exactly these paths):\n"
            + "\n".join(f"- {p}" for p in file_constraints.student_files)
            + "\n\nDo NOT add any other implementable files or folders beyond this list."
        )
        if file_constraints.model_entities:
            names = ", ".join(file_constraints.model_entities)
            parts.append(
                f"Required model/domain entities from the user query: {names}. "
                f"Create exactly these entities — do NOT invent others (e.g. no generic `item` model)."
            )
    else:
        parts.append(
            "Files to implement: infer ONLY from what the user explicitly mentions "
            "(models, routes, controllers, etc.). Do not add controllers unless the user says controllers."
        )

    if file_constraints and file_constraints.forbidden_layers:
        forbidden = sorted(file_constraints.forbidden_layers)
        parts.append(
            "FORBIDDEN — user did NOT request these folders. Do NOT create any files under:\n"
            + "\n".join(f"- {layer}/" for layer in forbidden)
            + "\nIf routes are requested without controllers, put handler logic directly in route files."
        )

    scaffold = scaffold_files if scaffold_files else list(DEFAULT_SCAFFOLD_FILES)
    parts.append(
        "Pre-filled scaffold files (complete in prefilled, do NOT put in student_files):\n"
        + "\n".join(f"- {p}" for p in scaffold)
        + "\nNote: db.js and package.json are always injected by the app."
    )

    parts.append(
        "Write readme_md using the reference README format from the system prompt. "
        "Folder structure and MultiLineNote must list ONLY the files you actually generate. "
        "Stay strictly within the MongoDB Integration & Data Management syllabus."
    )
    return "\n\n".join(parts)


def _call_api(
    spec: str,
    domain: str | None,
    question_title: str | None = None,
    student_files: list[str] | None = None,
    scaffold_files: list[str] | None = None,
    file_constraints: FileConstraints | None = None,
    json_retry: bool = False,
    structure_retry: bool = False,
) -> dict:
    user_message = _build_user_message(
        spec, domain, question_title, student_files, scaffold_files, file_constraints
    )
    if json_retry:
        user_message += (
            "\n\nIMPORTANT — previous response was INVALID JSON (e.g. unterminated string). "
            "Return ONLY valid JSON. Escape double quotes and backslashes inside all string "
            "values. Use \\n for newlines inside code strings. No markdown fences."
        )
    if structure_retry:
        user_message += (
            "\n\nIMPORTANT — previous response added folders/files the user did NOT request "
            "(e.g. controllers/ when only models and routes were asked). "
            "Generate ONLY the requested files. Remove any forbidden folders completely."
        )
    return call_llm_json(_load_system_prompt(), user_message, max_tokens=16000)


def call_llm_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 16000,
) -> dict:
    try:
        text = call_llm(system_prompt, user_message, max_tokens=max_tokens)
    except LLMError as e:
        raise GenerationError(str(e)) from e
    return _extract_json(text)


def generate_question(
    spec: str,
    domain: str | None = None,
    question_title: str | None = None,
    student_files: list[str] | None = None,
    scaffold_files: list[str] | None = None,
    assignment_text: str | None = None,
) -> dict:
    """Generate and validate a question package. Retries once on failure."""
    user_title = (question_title or "").strip() or None
    explicit_student = parse_file_list(student_files) if student_files else None
    constraints = merge_constraints(explicit_student, assignment_text, spec)
    user_student = explicit_student or (constraints.student_files if constraints else None)
    user_scaffold = parse_file_list(scaffold_files) if scaffold_files else None
    if user_scaffold is None and user_student is not None:
        user_scaffold = list(DEFAULT_SCAFFOLD_FILES)
    forbidden_layers = constraints.forbidden_layers if constraints else None

    try:
        validate_user_spec(spec)
    except ValueError as e:
        raise GenerationError(str(e)) from e

    last_error = None
    json_retry = False
    structure_retry = False
    for attempt in range(2):
        try:
            data = _call_api(
                spec,
                domain,
                user_title,
                user_student,
                user_scaffold,
                file_constraints=constraints,
                json_retry=json_retry,
                structure_retry=structure_retry,
            )
            if user_title:
                data["question_title"] = user_title
            apply_file_constraints(data, constraints)
            _normalize_test_file_ids(data)
            validate_response(
                data,
                user_student_files=user_student,
                user_scaffold_files=user_scaffold,
                user_title=user_title,
                forbidden_layers=forbidden_layers,
            )
            if not data.get("question_slug"):
                slug = data["question_title"].lower().strip()
                slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
                data["question_slug"] = slug or "mongodb-question"
            data["student_files"] = [p.replace("\\", "/") for p in data["student_files"]]
            if user_scaffold:
                data["scaffold_files"] = user_scaffold
            else:
                pre_paths = _normalize_paths(data.get("prefilled", {}))
                student_set = set(data["student_files"])
                data["scaffold_files"] = sorted(
                    p for p in pre_paths
                    if p not in student_set and p not in INJECTED_PATHS
                )
            data["syllabus_topic_labels"] = [
                ALLOWED_SYLLABUS_TOPICS[t] for t in data["syllabus_topics"]
            ]
            return data
        except (GenerationError, json.JSONDecodeError) as e:
            last_error = e
            if attempt == 0:
                err = str(e).lower()
                if "invalid json" in err or "unterminated" in err or isinstance(
                    e, json.JSONDecodeError
                ):
                    json_retry = True
                if "did not request" in err or "must match user specification" in err:
                    structure_retry = True
                continue
            raise GenerationError(f"Generation failed after retry: {last_error}") from e

    raise GenerationError(f"Generation failed: {last_error}")
