import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class AccountService:
    SESSION_SECONDS = 30 * 24 * 60 * 60

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(self._load_encryption_key())
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    gemini_api_key_encrypted BLOB,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                """
            )
            user_columns = {
                column["name"]
                for column in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "gemini_api_key_encrypted" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN gemini_api_key_encrypted BLOB")

    def _load_encryption_key(self) -> bytes:
        configured_key = os.getenv("GEMINI_KEY_ENCRYPTION_KEY")
        if configured_key:
            try:
                key = configured_key.encode("ascii")
                Fernet(key)
            except (UnicodeEncodeError, ValueError, TypeError) as exc:
                raise RuntimeError(
                    "GEMINI_KEY_ENCRYPTION_KEY must be a valid Fernet key."
                ) from exc
            return key

        key_path = self.database_path.parent / ".gemini-key-encryption"
        try:
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            key = key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(key)
        os.chmod(key_path, 0o600)
        try:
            Fernet(key)
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"Invalid Gemini key encryption key at {key_path}.") from exc
        return key

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def register(self, email: str, password: str):
        email = email.strip().lower()
        salt = secrets.token_bytes(16)
        user_id = str(uuid.uuid4())
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO users (id, email, password_salt, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, email, salt, self._password_hash(password, salt), int(time.time())),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email already exists.") from exc
        return {"id": user_id, "email": email}

    def create_session(self, email: str, password: str):
        email = email.strip().lower()
        with self._connect() as connection:
            user = connection.execute(
                "SELECT id, email, password_salt, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        if user is None or not hmac.compare_digest(
            self._password_hash(password, user["password_salt"]), user["password_hash"]
        ):
            raise ValueError("Email or password is incorrect.")

        token = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (self._token_hash(token), user["id"], int(time.time()) + self.SESSION_SECONDS),
            )
        return {"token": token, "user": {"id": user["id"], "email": user["email"]}}

    def get_user(self, token: str):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.email
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (self._token_hash(token), int(time.time())),
            ).fetchone()
        return dict(row) if row else None

    def revoke_session(self, token: str):
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (self._token_hash(token),))

    def save_gemini_api_key(self, user_id: str, api_key: str):
        encrypted_key = self.cipher.encrypt(api_key.encode("utf-8"))
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE users SET gemini_api_key_encrypted = ? WHERE id = ?",
                (encrypted_key, user_id),
            )
            if result.rowcount != 1:
                raise ValueError("Account not found.")

    def get_gemini_api_key(self, user_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT gemini_api_key_encrypted FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Account not found.")
        encrypted_key = row["gemini_api_key_encrypted"]
        if encrypted_key is None:
            return ""
        try:
            return self.cipher.decrypt(encrypted_key).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise RuntimeError("Could not decrypt this account's saved Gemini API key.") from exc
