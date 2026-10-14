from fastapi.testclient import TestClient

from app import main
from app.services.accounts import AccountService


def test_account_endpoints_register_authenticate_and_revoke(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "accounts", AccountService(tmp_path / "accounts.sqlite3"))
    client = TestClient(main.app)
    credentials = {"email": "reader@example.com", "password": "a secure password"}

    registered = client.post("/auth/register", json=credentials)
    assert registered.status_code == 201

    login = client.post("/auth/login", json=credentials)
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/me", headers=headers).json()["user"]["email"] == credentials["email"]
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_protected_account_endpoint_rejects_anonymous_requests():
    client = TestClient(main.app)

    assert client.get("/auth/me").status_code == 401
    assert client.get("/account/gemini-key").status_code == 401
    assert client.put("/account/gemini-key", json={"api_key": "secret"}).status_code == 401


def test_gemini_key_endpoints_persist_key_per_authenticated_account(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "accounts", AccountService(tmp_path / "accounts.sqlite3"))
    client = TestClient(main.app)
    users = [
        {"email": "reader@example.com", "password": "a secure password"},
        {"email": "writer@example.com", "password": "another secure password"},
    ]
    tokens = []
    for credentials in users:
        client.post("/auth/register", json=credentials)
        tokens.append(client.post("/auth/login", json=credentials).json()["token"])

    reader_headers = {"Authorization": f"Bearer {tokens[0]}"}
    writer_headers = {"Authorization": f"Bearer {tokens[1]}"}
    assert client.get("/account/gemini-key", headers=reader_headers).json() == {"api_key": ""}
    saved = client.put(
        "/account/gemini-key",
        headers=reader_headers,
        json={"api_key": "reader-gemini-secret"},
    )

    assert saved.status_code == 200
    assert client.get("/account/gemini-key", headers=reader_headers).json() == {
        "api_key": "reader-gemini-secret"
    }
    assert client.get("/account/gemini-key", headers=writer_headers).json() == {"api_key": ""}


def test_document_delete_route_requires_login_and_removes_document(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "accounts", AccountService(tmp_path / "accounts.sqlite3"))
    deleted = []

    class DocumentService:
        def delete_document(self, document_id):
            deleted.append(document_id)
            return {"message": "Document deleted successfully.", "id": document_id, "filename": "notes.pdf"}

    monkeypatch.setattr(main, "RAGService", lambda user_id, api_key: DocumentService())
    client = TestClient(main.app)
    document_id = "document-to-remove"

    assert client.delete(f"/documents/{document_id}").status_code == 401

    client.post(
        "/auth/register",
        json={"email": "reader@example.com", "password": "a secure password"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "reader@example.com", "password": "a secure password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    response = client.delete(f"/documents/{document_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["filename"] == "notes.pdf"
    assert deleted == [document_id]
