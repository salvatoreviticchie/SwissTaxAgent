"""
Document ingestion — parse uploaded PDFs/DOCX and split into chunks for Pinecone.
"""

import uuid
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument


def ingest_file(file_path: str | Path, source_name: str = "") -> list[dict]:
    """Parse a file and return a list of chunks ready for upsert."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix in (".docx", ".doc"):
        text = _extract_docx(path)
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return _chunk_text(text, source=source_name or path.name)


def _extract_pdf(path: Path) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _chunk_text(text: str, source: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "id": str(uuid.uuid4()),
            "text": chunk_text,
            "metadata": {"source": source, "chunk_index": len(chunks)},
        })
        start += chunk_size - overlap
    return chunks
