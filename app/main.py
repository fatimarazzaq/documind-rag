from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.services.rag import rag_service

app = FastAPI(title=settings.app_name, version="0.1.0", description="Ask questions about your uploaded documents.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this before production deployment.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=10)


@app.get("/")
def root():
    return {"message": "DocuMind RAG API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "documents": rag_service.document_count}


@app.get("/documents")
def list_documents():
    return {"documents": rag_service.list_documents()}


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded-file"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Supported file types: PDF, TXT, MD.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit.")
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        result = rag_service.add_document(filename, suffix, data)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/chat")
def chat(request: QuestionRequest):
    if not rag_service.has_chunks:
        raise HTTPException(status_code=400, detail="Upload a document before asking a question.")
    try:
        return rag_service.answer(request.question.strip(), request.top_k)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
