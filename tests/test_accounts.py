import pytest

from app.services.accounts import AccountService


def test_account_session_can_be_created_and_revoked(tmp_path):
    accounts = AccountService(tmp_path / "accounts.sqlite3")
    user = accounts.register("Reader@example.com", "correct horse battery")
    session = accounts.create_session("reader@example.com", "correct horse battery")

    assert user["email"] == "reader@example.com"
    assert accounts.get_user(session["token"]) == user

    accounts.revoke_session(session["token"])
    assert accounts.get_user(session["token"]) is None


def test_login_rejects_incorrect_password(tmp_path):
    accounts = AccountService(tmp_path / "accounts.sqlite3")
    accounts.register("reader@example.com", "correct horse battery")

    with pytest.raises(ValueError, match="Email or password is incorrect"):
        accounts.create_session("reader@example.com", "wrong password")


def test_duplicate_email_is_rejected_case_insensitively(tmp_path):
    accounts = AccountService(tmp_path / "accounts.sqlite3")
    accounts.register("reader@example.com", "correct horse battery")

    with pytest.raises(ValueError, match="already exists"):
        accounts.register("READER@example.com", "another password")


def test_gemini_key_is_encrypted_and_persists_for_its_account(tmp_path):
    database = tmp_path / "accounts.sqlite3"
    accounts = AccountService(database)
    user = accounts.register("reader@example.com", "correct horse battery")
    accounts.save_gemini_api_key(user["id"], "gemini-secret")

    with accounts._connect() as connection:
        stored = connection.execute(
            "SELECT gemini_api_key_encrypted FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()[0]

    assert b"gemini-secret" not in stored
    assert AccountService(database).get_gemini_api_key(user["id"]) == "gemini-secret"


def test_gemini_keys_are_isolated_between_accounts(tmp_path):
    accounts = AccountService(tmp_path / "accounts.sqlite3")
    reader = accounts.register("reader@example.com", "correct horse battery")
    writer = accounts.register("writer@example.com", "another secure password")
    accounts.save_gemini_api_key(reader["id"], "reader-key")

    assert accounts.get_gemini_api_key(writer["id"]) == ""


def test_gemini_key_encryption_key_can_be_configured(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet

    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("GEMINI_KEY_ENCRYPTION_KEY", encryption_key)
    accounts = AccountService(tmp_path / "accounts.sqlite3")

    assert not (tmp_path / ".gemini-key-encryption").exists()
    user = accounts.register("reader@example.com", "correct horse battery")
    accounts.save_gemini_api_key(user["id"], "gemini-secret")
    assert accounts.get_gemini_api_key(user["id"]) == "gemini-secret"
