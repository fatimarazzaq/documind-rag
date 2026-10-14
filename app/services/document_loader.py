from io import BytesIO


def extract_text(filename: str, suffix: str, data: bytes) -> str:
    """Extract text from supported document formats."""
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
        except Exception as exc:
            raise ValueError(f"Could not read this PDF: {exc}") from exc
        if not text.strip():
            raise ValueError("No selectable text found in this PDF. Scanned PDFs need OCR.")
        return text
    if suffix == ".docx":
        try:
            from docx import Document

            document = Document(BytesIO(data))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            text += "\n" + "\n".join(
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            )
        except Exception as exc:
            raise ValueError(f"Could not read this Word document: {exc}") from exc
        if not text.strip():
            raise ValueError("No text was found in this Word document.")
        return text
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Text files must be encoded as UTF-8.") from exc


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Prefer a word boundary near the end of the chunk.
            boundary = text.rfind(" ", start + int(chunk_size * 0.7), end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks
