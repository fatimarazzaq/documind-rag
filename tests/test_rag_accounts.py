from types import SimpleNamespace

import numpy as np
import pytest

from app.services import rag


def test_uploaded_documents_and_indexes_are_isolated_by_account(tmp_path, monkeypatch):
    monkeypatch.setattr(
        rag,
        "settings",
        SimpleNamespace(
            data_dir=tmp_path,
            chunk_size=1000,
            chunk_overlap=150,
            gemini_embedding_model="test-model",
            gemini_chat_model="test-model",
        ),
    )
    first_account = rag.RAGService("account-one", "")
    monkeypatch.setattr(
        first_account,
        "_embed",
        lambda texts, task_type: np.tile(np.array([[1.0, 0.0]], dtype="float32"), (len(texts), 1)),
    )

    result = first_account.add_document("private.txt", ".txt", b"Only account one can see this document.")
    second_account = rag.RAGService("account-two", "")
    restored_first_account = rag.RAGService("account-one", "")

    assert second_account.list_documents() == []
    assert restored_first_account.list_documents()[0]["id"] == result["id"]
    assert (tmp_path / "users" / "account-one" / "documents" / f"{result['id']}.bin").read_bytes() == (
        b"Only account one can see this document."
    )


def test_answers_retrieve_only_from_the_selected_document(tmp_path, monkeypatch):
    monkeypatch.setattr(
        rag,
        "settings",
        SimpleNamespace(
            data_dir=tmp_path,
            chunk_size=1000,
            chunk_overlap=150,
            gemini_embedding_model="test-model",
            gemini_chat_model="test-model",
        ),
    )
    service = rag.RAGService("account-filter", "test-key")

    def fake_embed(texts, task_type):
        if task_type == "RETRIEVAL_QUERY":
            return np.array([[1.0, 0.0]], dtype="float32")
        return np.array(
            [[0.0, 1.0] if "second" in text else [1.0, 0.0] for text in texts],
            dtype="float32",
        )

    service._embed = fake_embed
    service.add_document("first.txt", ".txt", b"first document content")
    second = service.add_document("second.txt", ".txt", b"second document content")
    service.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: SimpleNamespace(text="Answer from selected file.")
        )
    )

    result = service.answer("Question", document_id=second["id"])

    assert result["sources"]
    assert {source["filename"] for source in result["sources"]} == {"second.txt"}

    with pytest.raises(ValueError, match="not found in your library"):
        service.answer("Question", document_id="not-an-uploaded-document")


def test_delete_document_removes_original_and_rebuilds_user_index(tmp_path, monkeypatch):
    monkeypatch.setattr(
        rag,
        "settings",
        SimpleNamespace(
            data_dir=tmp_path,
            chunk_size=1000,
            chunk_overlap=150,
            gemini_embedding_model="test-model",
            gemini_chat_model="test-model",
        ),
    )
    service = rag.RAGService("account-delete", "")
    monkeypatch.setattr(
        service,
        "_embed",
        lambda texts, task_type: np.tile(np.array([[1.0, 0.0]], dtype="float32"), (len(texts), 1)),
    )
    first = service.add_document("remove.txt", ".txt", b"Remove this original document.")
    retained = service.add_document("keep.txt", ".txt", b"Keep this separate document.")
    removed_path = service.documents_dir / f"{first['id']}.bin"

    result = service.delete_document(first["id"])

    assert result["filename"] == "remove.txt"
    assert not removed_path.exists()
    assert [document["id"] for document in service.list_documents()] == [retained["id"]]
    assert service.index.ntotal == len(service.chunks)
    with pytest.raises(ValueError, match="Document not found"):
        service.delete_document(first["id"])

    service.delete_document(retained["id"])
    assert service.list_documents() == []
    assert rag.RAGService("account-delete", "").list_documents() == []
