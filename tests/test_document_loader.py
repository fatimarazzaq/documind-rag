from io import BytesIO

from docx import Document

from app.services.document_loader import extract_text, split_text


def test_split_text_returns_chunks():
    text = " ".join(f"word{i}" for i in range(100))
    chunks = split_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(chunks)


def test_split_text_empty():
    assert split_text("   ", chunk_size=100, overlap=10) == []


def test_extract_text_from_word_document():
    file = BytesIO()
    document = Document()
    document.add_paragraph("A private document.")
    document.save(file)

    assert "A private document." in extract_text("notes.docx", ".docx", file.getvalue())
