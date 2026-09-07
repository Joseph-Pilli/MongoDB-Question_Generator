"""Write generated question packages to disk and zip for download."""

import io
import json
import os
import re
import stat
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
MANIFEST_NAME = ".generated-files.json"

DB_JS = """const mongoose = require('mongoose')
const {MongoMemoryServer} = require('mongodb-memory-server')

let mongod

const connectDB = async () => {
  mongod = await MongoMemoryServer.create()
  const uri = mongod.getUri()
  console.log('In-memory MongoDB URI:', uri)
  await mongoose.connect(uri)
}

const disconnectDB = async () => {
  await mongoose.disconnect()
  if (mongod) await mongod.stop()
}

module.exports = {connectDB, disconnectDB}
"""

GITIGNORE = """node_modules/
.results/
.env
"""

JEST_CONFIG = """module.exports = {
  moduleFileExtensions: ["js", "jsx", "mjs"],
  reporters: [
    ["ccbp-jest-reporter", {
      resultDir: ".results",
      resultHtml: "results.html",
      resultJson: "results.json",
    }],
  ],
};
"""

TESTS_PACKAGE_JSON = """{
  "scripts": { "preinstall": "pnpm install ~/.ccbp/ccbp-jest-reporter" },
  "dependencies": {
    "@babel/parser": "7.13.11",
    "supertest": "6.1.3",
    "ccbp-jest-reporter": "file:~/.ccbp/ccbp-jest-reporter"
  }
}
"""

ROOT_PACKAGE_JSON_TEMPLATE = """{{
  "name": "{slug}",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "pretest": "cd .tests && pnpm i",
    "test": "jest --config=.tests/jest.config.js --forceExit"
  }},
  "mongodbMemoryServer": {{ "version": "6.0.4" }},
  "dependencies": {{
    "express": "4.18.2",
    "mongodb": "5.9.2",
    "mongodb-memory-server": "9.4.1",
    "mongoose": "7.8.7"
  }},
  "devDependencies": {{
    "jest": "27.5.1",
    "supertest": "6.1.3"
  }}
}}"""


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "mongodb-question"


def _root_package_json(slug: str) -> str:
    return ROOT_PACKAGE_JSON_TEMPLATE.format(slug=slug)


def _make_writable(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _safe_delete(path: Path, retries: int = 5) -> bool:
    """Delete a file or directory, retrying on Windows/OneDrive locks."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            if path.is_file() or path.is_symlink():
                _make_writable(path)
                path.unlink(missing_ok=True)
                return True
            if path.is_dir():
                for child in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                    if child.is_file() or child.is_symlink():
                        _make_writable(child)
                        child.unlink(missing_ok=True)
                    elif child.is_dir():
                        try:
                            child.rmdir()
                        except OSError:
                            pass
                path.rmdir()
                return True
            return True
        except OSError as exc:
            last_error = exc
            time.sleep(0.25 * (attempt + 1))
    return False


def _write_manifest(base: Path, keep: set[str]) -> None:
    manifest = sorted(keep)
    (base / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")


def _read_manifest(base: Path) -> set[str] | None:
    manifest_path = base / MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        return set(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None


def _collect_keep_paths(files: dict[str, str], extra: set[str]) -> set[str]:
    keep = {p.replace("\\", "/") for p in files.keys()}
    keep.update(extra)
    return keep


def _should_keep(rel: str, keep: set[str]) -> bool:
    if rel in keep:
        return True
    return any(k.startswith(rel + "/") for k in keep)


def _prune_stale_entries(base: Path, keep: set[str]) -> None:
    """Remove files/folders not present in the new package manifest."""
    if not base.exists():
        return
    for path in sorted(base.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.name == MANIFEST_NAME:
            continue
        rel = path.relative_to(base).as_posix()
        if _should_keep(rel, keep):
            continue
        _safe_delete(path)


def _write_folder(base: Path, files: dict[str, str], slug: str, readme_md: str | None = None):
    base.mkdir(parents=True, exist_ok=True)
    keep = _collect_keep_paths(files, {".gitignore", "db.js", "README.md", "package.json"})
    _prune_stale_entries(base, keep)

    (base / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (base / "db.js").write_text(DB_JS, encoding="utf-8")

    if readme_md is not None:
        (base / "README.md").write_text(readme_md, encoding="utf-8")

    for rel_path, content in files.items():
        if rel_path in ("db.js", "README.md", ".gitignore"):
            continue
        if rel_path == "package.json":
            content = _root_package_json(slug)
        dest = base / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    _write_manifest(base, keep)


def _write_tests_folder(base: Path, files: dict[str, str], slug: str):
    base.mkdir(parents=True, exist_ok=True)

    tests_files = dict(files)
    tests_files["package.json"] = _root_package_json(slug)
    tests_files[".tests/jest.config.js"] = JEST_CONFIG
    tests_files[".tests/package.json"] = TESTS_PACKAGE_JSON
    keep = _collect_keep_paths(
        tests_files,
        {".gitignore", "package.json", ".tests/jest.config.js", ".tests/package.json"},
    )
    _prune_stale_entries(base, keep)

    for rel_path, content in tests_files.items():
        if rel_path == ".tests/jest.config.js":
            content = JEST_CONFIG
        elif rel_path == ".tests/package.json":
            content = TESTS_PACKAGE_JSON
        elif rel_path == "package.json":
            content = _root_package_json(slug)
        dest = base / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    _write_manifest(base, keep)


def build_preview(slug: str, data: dict) -> dict:
    """Build a nested preview structure for the UI."""
    preview = {
        "prefilled": {},
        "solution": {},
        "tests": {},
    }

    prefilled_base = f"{slug}_prefilled"
    solution_base = f"{slug}_solution"
    tests_base = f"{slug}_tests"

    for rel_path, content in data.get("prefilled", {}).items():
        preview["prefilled"][f"{prefilled_base}/{rel_path}"] = content
    preview["prefilled"][f"{prefilled_base}/db.js"] = DB_JS
    preview["prefilled"][f"{prefilled_base}/.gitignore"] = GITIGNORE
    preview["prefilled"][f"{prefilled_base}/README.md"] = data.get("readme_md", "")
    preview["prefilled"][f"{prefilled_base}/package.json"] = _root_package_json(slug)

    for rel_path, content in data.get("solution", {}).items():
        preview["solution"][f"{solution_base}/{rel_path}"] = content
    preview["solution"][f"{solution_base}/db.js"] = DB_JS
    preview["solution"][f"{solution_base}/.gitignore"] = GITIGNORE
    preview["solution"][f"{solution_base}/package.json"] = _root_package_json(slug)

    for rel_path, content in data.get("tests", {}).items():
        preview["tests"][f"{tests_base}/{rel_path}"] = content
    preview["tests"][f"{tests_base}/.tests/jest.config.js"] = JEST_CONFIG
    preview["tests"][f"{tests_base}/.tests/package.json"] = TESTS_PACKAGE_JSON
    preview["tests"][f"{tests_base}/package.json"] = _root_package_json(slug)

    return preview


def write_question_package(data: dict) -> str:
    """Write all three folders. Returns the question slug."""
    slug = data.get("question_slug") or slugify(data.get("question_title", "question"))
    slug = re.sub(r"[^a-z0-9-]", "", slug.lower())

    prefilled_dir = OUTPUT_DIR / f"{slug}_prefilled"
    solution_dir = OUTPUT_DIR / f"{slug}_solution"
    tests_dir = OUTPUT_DIR / f"{slug}_tests"

    _write_folder(prefilled_dir, data.get("prefilled", {}), slug, data.get("readme_md"))
    _write_folder(solution_dir, data.get("solution", {}), slug)
    _write_tests_folder(tests_dir, data.get("tests", {}), slug)

    return slug


def zip_question(slug: str) -> io.BytesIO:
    """Zip the three output folders into a BytesIO buffer."""
    folders = [
        OUTPUT_DIR / f"{slug}_prefilled",
        OUTPUT_DIR / f"{slug}_solution",
        OUTPUT_DIR / f"{slug}_tests",
    ]

    for folder in folders:
        if not folder.exists():
            raise FileNotFoundError(f"Output folder not found: {folder}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in folders:
            manifest = _read_manifest(folder)
            for file_path in folder.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.name == MANIFEST_NAME:
                    continue
                rel_in_folder = file_path.relative_to(folder).as_posix()
                if manifest is not None and rel_in_folder not in manifest:
                    continue
                arcname = str(file_path.relative_to(OUTPUT_DIR))
                zf.write(file_path, arcname)
    buf.seek(0)
    return buf


def read_package_for_preview(slug: str) -> dict:
    """Read written files back for preview (fallback)."""
    preview = {"prefilled": {}, "solution": {}, "tests": {}}
    mapping = {
        "prefilled": f"{slug}_prefilled",
        "solution": f"{slug}_solution",
        "tests": f"{slug}_tests",
    }
    for key, folder_name in mapping.items():
        folder = OUTPUT_DIR / folder_name
        if not folder.exists():
            continue
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                rel = f"{folder_name}/{file_path.relative_to(folder).as_posix()}"
                preview[key][rel] = file_path.read_text(encoding="utf-8")
    return preview
