"""Extract plain text from uploaded assignment documents."""

from io import BytesIO
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class DocumentParseError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentParseError(
            f"Unsupported file type: {ext or '(none)'}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if not data:
        raise DocumentParseError("Uploaded file is empty.")

    if ext in {".txt", ".md"}:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return data.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        raise DocumentParseError("Could not decode text file.")

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise DocumentParseError("PDF support requires pypdf.") from e

        reader = PdfReader(BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise DocumentParseError("No text could be extracted from the PDF.")
        return text

    if ext == ".docx":
        try:
            from docx import Document
        except ImportError as e:
            raise DocumentParseError("DOCX support requires python-docx.") from e

        document = Document(BytesIO(data))
        text = "\n".join(p.text for p in document.paragraphs if p.text).strip()
        if not text:
            raise DocumentParseError("No text could be extracted from the DOCX file.")
        return text

    raise DocumentParseError(f"Unsupported file type: {ext}")
