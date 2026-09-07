"""Infer implement vs forbidden files from the user's assignment text."""

import re
from dataclasses import dataclass, field

LAYER_NAMES = ("models", "routes", "controllers", "validators", "services", "middleware", "utils")

LAYER_PATTERNS: dict[str, re.Pattern[str]] = {
    "models": re.compile(r"\bmodels?\b|\bschemas?\b", re.I),
    "routes": re.compile(r"\broutes?\b|\bendpoints?\b|\bapi routes?\b", re.I),
    "controllers": re.compile(r"\bcontrollers?\b", re.I),
    "validators": re.compile(r"\bvalidators?\b", re.I),
    "services": re.compile(r"\bservices?\b", re.I),
    "middleware": re.compile(r"\bmiddleware\b", re.I),
    "utils": re.compile(r"\butils?\b|\butilities\b", re.I),
}


@dataclass
class FileConstraints:
    student_files: list[str] = field(default_factory=list)
    forbidden_layers: set[str] = field(default_factory=set)
    mentioned_layers: set[str] = field(default_factory=set)
    model_entities: list[str] = field(default_factory=list)
    source: str = "none"  # explicit | inferred


STOP_ENTITIES = frozenset({
    "one", "another", "exactly", "model", "models", "schema", "schemas",
    "the", "a", "an", "with", "and", "or", "for", "two", "three", "between",
    "create", "also", "which", "shows", "relation", "mongodb", "inside",
    "folder", "define", "using", "node", "js", "post", "requests", "only",
    "add", "details", "database", "application", "mongoose", "routes",
    "route", "request", "requests",
})


def _normalize_entity(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "", name)
    if not name or name.isdigit() or name in STOP_ENTITIES:
        return ""
    return name


def _extract_model_entities(text: str) -> list[str]:
    entities: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        entity = _normalize_entity(raw)
        if entity and entity not in seen:
            seen.add(entity)
            entities.append(entity)

    def add_pair(first: str, second: str) -> None:
        add(first)
        add(second)

    pair_patterns = [
        r"one is (?:the )?(\w+) model[\s\S]{0,60}?another (?:one )?is (?:the )?(\w+)",
        r"(?:define|create)\s+(?:two|2|\d+)\s+models?,?\s+(\w+)\s+and\s+(\w+)",
        r"models?,?\s+(\w+)\s+and\s+(\w+)",
        r"(\w+)\s+and\s+(\w+)\s+models?",
        r"(\w+)\s+and\s+(\w+)(?:,|\s)+inside the models",
        r"add (\w+) and (\w+) details",
        r"models for (\w+) and (\w+)",
    ]
    for pattern in pair_patterns:
        for match in re.finditer(pattern, text, re.I):
            add_pair(match.group(1), match.group(2))

    comma_list = re.search(
        r"models?[:\s,]+((?:[A-Za-z]\w*(?:\s*,\s*[A-Za-z]\w*)+))",
        text,
        re.I,
    )
    if comma_list:
        for name in re.split(r"\s*,\s*", comma_list.group(1)):
            add(name)

    if not entities:
        for pattern in (
            r"one is (?:the )?(\w+) model",
            r"another (?:one )?is (?:the )?(\w+)(?:\s+model)?",
        ):
            for match in re.finditer(pattern, text, re.I):
                add(match.group(1))

    if not entities:
        for match in re.finditer(r"(\w+) model(?:s)?", text, re.I):
            add(match.group(1))

    if not entities:
        for match in re.finditer(r"define (?:a )?(\w+) schema", text, re.I):
            add(match.group(1))

    return entities


def _build_student_files(mentioned: set[str], entities: list[str]) -> list[str]:
    files: list[str] = []

    if "models" in mentioned:
        if entities:
            for entity in entities:
                files.append(f"models/{entity}.js")
        else:
            files.append("models/item.js")

    if "routes" in mentioned:
        if entities:
            for entity in entities:
                files.append(f"routes/{entity}Routes.js")
        else:
            files.append("routes/itemRoutes.js")

    for layer in ("controllers", "validators", "services", "middleware", "utils"):
        if layer in mentioned:
            if layer == "middleware":
                files.append("middleware/errorHandler.js")
            elif layer == "utils":
                files.append("utils/helpers.js")
            elif entities and layer == "controllers":
                for entity in entities:
                    files.append(f"controllers/{entity}Controller.js")
            elif entities and layer == "validators":
                for entity in entities:
                    files.append(f"validators/{entity}Validator.js")
            elif entities and layer == "services":
                files.append(f"services/{entities[0]}Service.js")
            elif layer == "controllers":
                files.append("controllers/itemController.js")
            elif layer == "validators":
                files.append("validators/itemValidator.js")
            elif layer == "services":
                files.append("services/itemService.js")

    return files


def infer_file_constraints(text: str) -> FileConstraints | None:
    """
    Parse assignment/spec text for explicit layer mentions.
    Returns None if the text does not mention any implementable layer.
    """
    text = (text or "").strip()
    if not text:
        return None

    mentioned = {layer for layer, pattern in LAYER_PATTERNS.items() if pattern.search(text)}
    if not mentioned:
        return None

    entities = _extract_model_entities(text)
    student_files = _build_student_files(mentioned, entities)
    forbidden = set(LAYER_NAMES) - mentioned

    return FileConstraints(
        student_files=student_files,
        forbidden_layers=forbidden,
        mentioned_layers=mentioned,
        model_entities=entities,
        source="inferred",
    )


def merge_constraints(
    explicit_files: list[str] | None,
    assignment_text: str | None,
    spec: str | None,
) -> FileConstraints | None:
    """Explicit UI file list wins; otherwise infer from assignment + spec."""
    if explicit_files:
        paths = [p.replace("\\", "/") for p in explicit_files if p.strip()]
        mentioned: set[str] = set()
        for path in paths:
            for layer in LAYER_NAMES:
                if path.startswith(f"{layer}/"):
                    mentioned.add(layer)
        return FileConstraints(
            student_files=paths,
            forbidden_layers=set(LAYER_NAMES) - mentioned,
            mentioned_layers=mentioned,
            source="explicit",
        )

    combined = "\n".join(p for p in (assignment_text, spec) if p and p.strip())
    return infer_file_constraints(combined)


def _strip_controller_imports(content: str) -> str:
    """Remove controller require lines from server.js or tests."""
    lines = []
    for line in content.splitlines():
        if re.search(r'require\s*\(\s*["\'].*controllers/', line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _path_forbidden(path: str, forbidden_layers: set[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(f"{layer}/") for layer in forbidden_layers)


def apply_file_constraints(data: dict, constraints: FileConstraints | None) -> None:
    """Remove forbidden folders from generated maps and enforce student file list."""
    if not constraints:
        return

    for map_key in ("prefilled", "solution"):
        file_map = data.get(map_key)
        if not isinstance(file_map, dict):
            continue
        for path in list(file_map.keys()):
            if _path_forbidden(path, constraints.forbidden_layers):
                del file_map[path]
            elif path == "server.js" and isinstance(file_map[path], str):
                file_map[path] = _strip_controller_imports(file_map[path])

    if constraints.student_files:
        data["student_files"] = list(constraints.student_files)

    tests = data.get("tests")
    if isinstance(tests, dict):
        for path, content in tests.items():
            if isinstance(content, str) and "controllers/" in content:
                tests[path] = _strip_controller_imports(content)
