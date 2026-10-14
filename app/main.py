from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.config import settings
from app.services.accounts import AccountService
from app.services.rag import RAGService

app = FastAPI(title=settings.app_name, version="0.1.0", description="Ask questions about your uploaded documents.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this before production deployment.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024
accounts = AccountService(settings.data_dir / "accounts.sqlite3")
bearer_auth = HTTPBearer(auto_error=False)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=10)
    document_id: str | None = None


class AccountCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class GeminiAPIKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=4096)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in to access your account.")
    user = accounts.get_user(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return user


def rag_for_user(
    user=Depends(current_user),
    api_key: str = Header(default="", alias="X-Gemini-API-Key"),
):
    return RAGService(user["id"], api_key.strip())


@app.get("/")
def root():
    return {"message": "DocuMind RAG API is running", "docs": "/docs"}


@app.post("/auth/register", status_code=201)
def register(request: AccountCredentials):
    email = request.email.strip()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(request.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")
    try:
        return accounts.register(email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/auth/login")
def login(request: AccountCredentials):
    try:
        return accounts.create_session(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/me")
def get_account(user=Depends(current_user)):
    return {"user": user}


@app.post("/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth)):
    if credentials:
        accounts.revoke_session(credentials.credentials)
    return {"message": "Signed out."}


@app.get("/account/gemini-key")
def get_gemini_api_key(user=Depends(current_user)):
    try:
        return {"api_key": accounts.get_gemini_api_key(user["id"])}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/account/gemini-key")
def save_gemini_api_key(request: GeminiAPIKeyRequest, user=Depends(current_user)):
    api_key = request.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="Gemini API key cannot be empty.")
    try:
        accounts.save_gemini_api_key(user["id"], api_key)
        return {"message": "Gemini API key saved."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents")
def list_documents(service: RAGService = Depends(rag_for_user)):
    return {"documents": service.list_documents()}


@app.post("/documents")
async def upload_document(file: UploadFile = File(...), service: RAGService = Depends(rag_for_user)):
    filename = file.filename or "uploaded-file"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Supported file types: PDF, DOCX, TXT, and Markdown.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit.")
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        result = service.add_document(filename, suffix, data)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.delete("/documents/{document_id}")
def delete_document(document_id: str, service: RAGService = Depends(rag_for_user)):
    try:
        return service.delete_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat")
def chat(request: QuestionRequest, service: RAGService = Depends(rag_for_user)):
    try:
        return service.answer(request.question.strip(), request.top_k, request.document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
