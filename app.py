import traceback
import os
from pathlib import Path

from dotenv import load_dotenv, set_key

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH, override=True)

from flask import Flask, jsonify, render_template, request, send_file
from lib.assignment_analyzer import analyze_assignment, build_spec_from_selection
from lib.claude_client import GenerationError, generate_question
from lib.document_parser import DocumentParseError, extract_text
from lib.file_writer import build_preview, write_question_package, zip_question
from lib.syllabus import ALLOWED_SYLLABUS_TOPICS, SYLLABUS_DESCRIPTION, SYLLABUS_TITLE
from lib.llm_client import provider_label

app = Flask(__name__)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@app.route("/")
def index():
    return render_template(
        "index.html",
        syllabus_title=SYLLABUS_TITLE,
        syllabus_description=SYLLABUS_DESCRIPTION,
        syllabus_topics=ALLOWED_SYLLABUS_TOPICS,
        llm_provider_label=provider_label(),
    )


@app.route("/settings/api-key", methods=["POST"])
def save_api_key():
    """Persist the user's OpenAI API key without returning or logging it."""
    body = request.get_json(silent=True) or {}
    api_key = (body.get("api_key") or "").strip()

    if not api_key:
        return jsonify({"error": "Enter an OpenAI API key."}), 400
    if not api_key.startswith("sk-"):
        return jsonify({"error": "OpenAI API keys must start with sk-."}), 400

    try:
        set_key(str(ENV_PATH), "OPENAI_API_KEY", api_key)
        os.environ["OPENAI_API_KEY"] = api_key
    except OSError as e:
        return jsonify({"error": f"Could not update {ENV_PATH.name}: {e}"}), 500

    return jsonify({"message": "API key saved."})


@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze pasted text or uploaded document against the syllabus."""
    text = ""

    if request.content_type and "multipart/form-data" in request.content_type:
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            data = uploaded.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                return jsonify({"error": "File too large (max 5 MB)."}), 400
            try:
                text = extract_text(uploaded.filename, data)
            except DocumentParseError as e:
                return jsonify({"error": str(e)}), 400
        else:
            text = (request.form.get("text") or "").strip()
    else:
        body = request.get_json(silent=True) or {}
        text = (body.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Paste assignment text or upload a document."}), 400

    try:
        result = analyze_assignment(text)
        result["assignment_text"] = text
        return jsonify(result)
    except GenerationError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@app.route("/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    domain = (body.get("domain") or "").strip() or None
    question_title = (body.get("question_title") or "").strip() or None
    student_files = body.get("student_files") or body.get("files_to_implement")
    scaffold_files = body.get("scaffold_files") or body.get("files_scaffold")
    spec = (body.get("spec") or "").strip()
    selected_concepts = body.get("selected_concepts") or []
    assignment_text = (body.get("assignment_text") or "").strip() or None

    if selected_concepts:
        try:
            spec, _topic_ids = build_spec_from_selection(selected_concepts, assignment_text)
        except GenerationError as e:
            return jsonify({"error": str(e)}), 400
    elif not spec:
        return jsonify({
            "error": "Analyze an assignment and select concepts, or provide a concept spec.",
        }), 400

    try:
        data = generate_question(
            spec,
            domain,
            question_title=question_title,
            student_files=student_files,
            scaffold_files=scaffold_files,
            assignment_text=assignment_text,
        )
        slug = write_question_package(data)
        preview = build_preview(slug, data)

        return jsonify({
            "slug": slug,
            "title": data.get("question_title", slug),
            "domain": data.get("domain", domain or ""),
            "student_files": data.get("student_files", []),
            "scaffold_files": data.get("scaffold_files", []),
            "syllabus_topics": data.get("syllabus_topics", []),
            "syllabus_topic_labels": data.get("syllabus_topic_labels", []),
            "file_structure_rationale": data.get("file_structure_rationale", ""),
            "preview": preview,
        })
    except GenerationError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@app.route("/download/<slug>")
def download(slug):
    slug = slug.strip().lower()
    if not slug or not all(c.isalnum() or c == "-" for c in slug):
        return jsonify({"error": "Invalid slug."}), 400

    try:
        buf = zip_question(slug)
        return send_file(
            buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{slug}.zip",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
