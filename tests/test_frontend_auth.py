from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest


def test_saved_browser_cookie_restores_login_after_refresh():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    app.run(timeout=15)
    assert any("Checking your saved sign-in session" in item.value for item in app.info)
    app.session_state["documind_auth_cookies"] = {"documind_session": "remembered-token"}

    account_response = Mock(ok=True, status_code=200)
    account_response.json.return_value = {
        "user": {"id": "reader-id", "email": "someoneverylong@gmail.com"}
    }
    key_response = Mock(ok=True, status_code=200)
    key_response.json.return_value = {"api_key": "saved-gemini-key"}
    documents_response = Mock(ok=True, status_code=200)
    documents_response.json.return_value = {"documents": []}

    with patch(
        "requests.request",
        side_effect=[account_response, key_response, documents_response],
    ) as request:
        app.run(timeout=15)

    assert not app.exception
    assert app.session_state["auth_token"] == "remembered-token"
    assert app.session_state["user"]["email"] == "someoneverylong@gmail.com"
    assert app.session_state["gemini_api_key"] == "saved-gemini-key"
    assert request.call_args_list[0].kwargs["headers"]["Authorization"] == "Bearer remembered-token"
    assert request.call_args_list[1].args == (
        "GET",
        "http://127.0.0.1:8000/account/gemini-key",
    )
    assert any("someone...@gmail.com" in str(element.value) for element in app.sidebar.markdown)


def test_successful_login_saves_a_thirty_day_cookie():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    app.session_state["documind_auth_cookies"] = {}
    app.run(timeout=15)
    app.text_input[0].set_value("reader@example.com")
    app.text_input[1].set_value("a secure password")

    login_response = Mock(ok=True, status_code=200)
    login_response.json.return_value = {
        "token": "new-session-token",
        "user": {"id": "reader-id", "email": "reader@example.com"},
    }

    with (
        patch("requests.request", return_value=login_response),
        patch("streamlit.html") as html,
    ):
        next(button for button in app.button if button.label == "Sign in").click().run(timeout=15)

    assert not app.exception
    assert app.session_state["auth_token"] == "new-session-token"
    assert "documind_session=new-session-token" in html.call_args.args[0]
    assert f"Max-Age={30 * 24 * 60 * 60}" in html.call_args.args[0]
    assert html.call_args.kwargs["unsafe_allow_javascript"] is True


def test_documents_dashboard_shows_searchable_file_table():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    app.session_state["documind_auth_cookies"] = {"documind_session": "remembered-token"}
    app.session_state["gemini_api_key"] = "session-gemini-key"

    account_response = Mock(ok=True, status_code=200)
    account_response.json.return_value = {
        "user": {"id": "reader-id", "email": "reader@example.com"}
    }
    key_response = Mock(ok=True, status_code=200)
    key_response.json.return_value = {"api_key": "session-gemini-key"}
    documents_response = Mock(ok=True, status_code=200)
    documents_response.json.return_value = {
        "documents": [
            {"id": "doc-1", "filename": "project-notes.pdf", "chunks": 4},
            {"id": "doc-2", "filename": "meeting.docx", "chunks": 2},
        ]
    }

    with patch("requests.request", side_effect=[account_response, key_response, documents_response]):
        app.run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "Documents"
    assert len(app.dataframe) == 1
    assert "project-notes.pdf" in str(app.dataframe[0].value)
    assert any("Upload documents" in button.label for button in app.button)


def test_edit_gemini_key_form_is_prefilled_from_saved_key():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    app.session_state["auth_token"] = "remembered-token"
    app.session_state["user"] = {"id": "reader-id", "email": "reader@example.com"}
    app.session_state["gemini_api_key"] = "saved-gemini-key"
    app.session_state["documind_auth_cookies"] = {"documind_session": "remembered-token"}
    documents_response = Mock(ok=True, status_code=200)
    documents_response.json.return_value = {"documents": []}

    with patch("requests.request", return_value=documents_response):
        app.run(timeout=15)
        next(button for button in app.sidebar.button if button.label == "Update Gemini key").click().run(timeout=15)

    assert not app.exception
    assert any(widget.value == "saved-gemini-key" for widget in app.text_input)


def test_waits_for_browser_cookie_before_showing_signed_out_page():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend" / "app.py")

    app.run(timeout=15)

    assert not app.exception
    assert not app.tabs
    assert any("Checking your saved sign-in session" in item.value for item in app.info)


def test_sidebar_document_can_be_confirmed_for_deletion():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    app.session_state["auth_token"] = "remembered-token"
    app.session_state["user"] = {"id": "reader-id", "email": "reader@example.com"}
    app.session_state["gemini_api_key"] = "session-gemini-key"
    app.session_state["documind_auth_cookies"] = {"documind_session": "remembered-token"}
    documents = {
        "documents": [
            {"id": "doc-1", "filename": "long_filename_that_is_truncated.pdf", "chunks": 3}
        ]
    }
    list_response = Mock(ok=True, status_code=200)
    list_response.json.return_value = documents
    delete_response = Mock(ok=True, status_code=200)
    delete_response.json.return_value = {
        "message": "Document deleted successfully.",
        "id": "doc-1",
        "filename": "long_filename_that_is_truncated.pdf",
    }
    empty_response = Mock(ok=True, status_code=200)
    empty_response.json.return_value = {"documents": []}

    with patch(
        "requests.request",
        side_effect=[
            list_response,
            list_response,
            list_response,
            delete_response,
            empty_response,
        ],
    ) as request:
        app.run(timeout=15)
        doc_button = next(
            button for button in app.sidebar.button if button.label.startswith("📄")
        )
        assert "long_filename_that_is_truncated.pdf" in doc_button.help
        assert "…" in doc_button.label
        next(
            button for button in app.sidebar.button
            if button.key == "delete_sidebar_document_doc-1"
        ).click().run(timeout=15)
        assert any("Delete" in button.label for button in app.sidebar.button)
        next(button for button in app.sidebar.button if button.label == "Delete").click().run(timeout=15)

    assert not app.exception
    delete_request = next(call for call in request.call_args_list if call.args[0] == "DELETE")
    assert delete_request.args == (
        "DELETE",
        "http://127.0.0.1:8000/documents/doc-1",
    )
    assert any("long_filename_that_is_truncated.pdf was deleted" in item.value for item in app.success)
