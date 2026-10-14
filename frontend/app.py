import json
import os

import requests
import streamlit as st
from streamlit_cookies_controller import CookieController

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
SUPPORTED_TYPES = ["pdf", "docx", "txt", "md"]
AUTH_COOKIE = "documind_session"
AUTH_SESSION_SECONDS = 30 * 24 * 60 * 60


class AuthenticationError(RuntimeError):
    pass

st.set_page_config(page_title="DocuMind | Your document workspace", page_icon="📄", layout="wide")
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
      :root { --ink: #20252d; --muted: #69727e; --blue: #336ef3; --blue-dark: #2458d3;
        --blue-pale: #edf3ff; --blue-border: #c9d8ff; --line: #e5e8eb;
        --primary-color: #336ef3; }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
      .stApp { background: #f8f9fb; }
      [data-testid="stAppViewContainer"] > .main { background: #f8f9fb; }
      [data-testid="stAppViewContainer"] { accent-color: var(--blue); }
      [data-testid="stHeader"] { background: transparent; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; letter-spacing: -0.035em; color: var(--ink); }
      h1 { font-size: 2.15rem !important; }
      h2, h3 { letter-spacing: -0.025em; }
      [data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--line); }
      [data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #414955; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 9px; padding: .25rem .4rem; }
      [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { gap: .35rem; }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"] {
        background: #f0f1f3; border-radius: 12px; padding: .2rem .35rem; margin-bottom: .3rem;
        transition: background .15s ease;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"]:hover {
        background: #e9ebef;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"]:has(button[kind="primary"]) {
        background: #336ef3;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"] [data-testid="stHorizontalBlock"] {
        align-items: center; gap: .1rem;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"] [data-testid="stHorizontalBlock"] > div:first-child {
        min-width: 0;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"] [data-testid="stHorizontalBlock"] > div:first-child button[kind="secondary"] {
        background: transparent; border-color: transparent;
      }
      [data-testid="stSidebar"] button[kind="primary"] {
        background: #336ef3 !important; border-color: #336ef3 !important; color: #fff !important;
      }
      [data-testid="stSidebar"] button[kind="primary"] *,
      [data-testid="stSidebar"] button[kind="primary"] p { color: #fff !important; }
      [data-testid="stSidebar"] button[kind="secondary"] {
        background: transparent; border-color: transparent; color: #353d49;
      }
      [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background: #edf3ff; border-color: #edf3ff; color: #2458d3;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-update-gemini-key"] button,
      [data-testid="stSidebar"] [class*="st-key-sidebar-sign-out"] button {
        background: #fff; border: 1px solid #d5dbe5; color: #353d49;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-update-gemini-key"] button:hover,
      [data-testid="stSidebar"] [class*="st-key-sidebar-sign-out"] button:hover {
        background: #f7f9fc; border-color: #aebbd0; color: #2458d3;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"] [data-testid="stHorizontalBlock"] > div:last-child button {
        width: 2.25rem; min-height: 2.25rem; padding: 0; margin: 0; opacity: 0; pointer-events: none;
        background: transparent; border-color: transparent; color: #69727e;
        transition: opacity .15s ease, background .15s ease, color .15s ease;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"]:hover [data-testid="stHorizontalBlock"] > div:last-child button,
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"]:focus-within [data-testid="stHorizontalBlock"] > div:last-child button {
        opacity: 1; pointer-events: auto;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"] [data-testid="stHorizontalBlock"] > div:last-child button:hover {
        background: #fff0f0; border-color: #fff0f0; color: #d14343;
      }
      [data-testid="stSidebar"] [class*="st-key-sidebar-document-row-"]:has(button[kind="primary"]) [data-testid="stHorizontalBlock"] > div:last-child button {
        color: #fff;
      }
      .sidebar-document-name {
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left;
      }
      [data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom: 1px solid var(--line); gap: 1.25rem; }
      [data-testid="stTabs"] button[role="tab"] { color: var(--muted); border-bottom-color: transparent !important; }
      [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: var(--blue-dark) !important; border-bottom-color: var(--blue) !important; }
      [data-testid="stTabs"] button[role="tab"]::after { background-color: var(--blue) !important; }
      [data-testid="stRadio"] input:checked + div,
      [data-testid="stRadio"] [data-checked="true"] { color: var(--blue-dark) !important; }
      [data-testid="stRadio"] [role="radio"][aria-checked="true"] > div:first-child {
        border-color: var(--blue) !important; background-color: var(--blue) !important; }
      [data-testid="stRadio"] [role="radio"] svg { color: var(--blue) !important; fill: var(--blue) !important; }
      [data-testid="stRadio"] label:has(input:checked) { color: var(--blue-dark) !important; }
      [data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 14px 17px; }
      [data-testid="stMetricLabel"] { color: var(--muted); font-size: .88rem; }
      [data-testid="stMetricValue"] { color: var(--ink); font-family: 'Manrope', sans-serif; }
      .eyebrow { color: var(--blue-dark); font-weight: 700; font-size: .76rem; letter-spacing: .1em; text-transform: uppercase; }
      .muted { color: var(--muted); }
      .brand-mark { display: inline-flex; width: 36px; height: 36px; border-radius: 10px; background: var(--blue-pale);
        color: var(--blue); align-items: center; justify-content: center; font-weight: 800; margin-right: 9px; }
      .welcome-banner { background: linear-gradient(105deg, #e9f0ff 0%, #f3f6ff 100%); border-radius: 16px;
        padding: 22px 26px; margin: 12px 0 28px; border: 1px solid #e0e9ff; }
      .welcome-banner strong { font-family: 'Manrope', sans-serif; font-size: 1.1rem; }
      .welcome-banner span { color: #59677f; }
      .dashboard-notice { display:flex; align-items:flex-start; gap:14px; padding:16px 18px; margin:10px 0 20px;
        background:#fff; border:1px solid #dfe3e8; border-radius:9px; box-shadow:0 2px 5px rgba(23,32,51,.05); }
      .dashboard-notice-icon { color:var(--blue); font-size:1.15rem; line-height:1.2; }
      .dashboard-notice strong { font-weight:600; }
      .dashboard-notice span { color:var(--muted); }
      .dashboard-toolbar { border-bottom:1px solid var(--line); padding-bottom:10px; }
      .dashboard-section-title { font:700 1.35rem 'Manrope',sans-serif; margin:26px 0 12px; color:var(--ink); }
      [data-testid="stDataFrame"] { background:#fff; }
      .document-table-heading { color:#5d6673; font-size:.84rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }
      div[data-testid="stFileUploader"] section { border: 1px dashed var(--blue-border); border-radius: 12px; background: #fff; }
      div[data-testid="stFileUploader"] section:hover { border-color: var(--blue); background: #fbfcff; }
      div[data-testid="stFileUploader"] svg { color: var(--blue); }
      .stButton > button[kind="primary"], button[kind="primaryFormSubmit"] {
        background: var(--blue); border-color: var(--blue); color: #fff; font-weight: 600; }
      .stButton > button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
        background: var(--blue-dark); border-color: var(--blue-dark); color: #fff; }
      .stButton > button { border-radius: 9px; }
      [data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border-color: var(--line); border-radius: 12px; }
      [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
      div[data-testid="stChatMessage"] { border: 1px solid var(--line); border-radius: 12px; background: #fff; }
      [data-testid="stChatInput"] { border-color: #dce4f5; border-radius: 12px; }
      [data-testid="stProgressBar"] [role="progressbar"] > div { background-color: var(--blue) !important; }
      [data-baseweb="slider"] [role="slider"] { background-color: var(--blue) !important; border-color: var(--blue) !important; }
      [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
        border-color: var(--blue) !important; box-shadow: 0 0 0 1px var(--blue) !important; }
      [data-baseweb="select"] > div:focus-within { border-color: var(--blue) !important; box-shadow: 0 0 0 1px var(--blue) !important; }
      a { color: var(--blue-dark) !important; }
      .auth-hero {
        min-height: 580px; height: 100%; padding: 34px 34px; box-sizing: border-box; border-radius: 18px;
        color: white; display: flex; flex-direction: column; justify-content: space-between;
        background-color: #173caa;
        background-image: linear-gradient(145deg, rgba(51,110,243,.97), rgba(14,43,135,.98)),
          linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
        background-size: cover, 28px 28px, 28px 28px;
      }
      .auth-brand { font: 800 1.2rem 'Manrope', sans-serif; letter-spacing: -.04em; }
      .auth-brand-mark { display:inline-flex; width:34px; height:34px; align-items:center; justify-content:center;
        background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.23); border-radius:10px; margin-right:10px; }
      .auth-hero h2 { color:#fff; font:800 clamp(2rem, 3vw, 2.7rem) 'Manrope',sans-serif; letter-spacing:-.055em; margin:0 0 14px; }
      .auth-hero p { color:#dbe6ff; font-size:1.05rem; line-height:1.65; }
      .auth-features { display:grid; gap:14px; margin-top:28px; color:#eef3ff; }
      .auth-feature::before { content:'✓'; color:#63d8ff; font-weight:800; margin-right:12px; }
      .auth-footnote { color:#c5d5ff; font-size:.83rem; }
      .auth-form-title { font:800 2rem 'Manrope',sans-serif; letter-spacing:-.05em; color:var(--ink); margin:0; }
      .auth-form-caption { color:var(--muted); margin:4px 0 22px; }
      div[data-testid="stColumn"]:has(.auth-form-title) [data-testid="stTextInput"] input {
        border: 1px solid #d5dbe5 !important; border-radius: 9px; background: #fff;
        transition: border-color .15s ease, box-shadow .15s ease;
      }
      div[data-testid="stColumn"]:has(.auth-form-title) [data-testid="stTextInput"] input:hover {
        border-color: #aeb8c8 !important;
      }
      div[data-testid="stColumn"]:has(.auth-form-title) [data-testid="stTextInput"] input:focus {
        border-color: var(--blue) !important; box-shadow: 0 0 0 1px var(--blue) !important;
      }
      div[data-testid="stColumn"]:has(.auth-hero) { background:#163aa7; border-radius:18px; }
      div[data-testid="stColumn"]:has(.auth-form-title) { background:#fff; border-radius:18px; padding:34px 4vw; }
      @media (max-width: 760px) { .auth-hero { min-height:360px; padding:26px; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(method, path, *, authenticated=True, include_key=False, auth_token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    token = auth_token or st.session_state.get("auth_token")
    if authenticated and token:
        headers["Authorization"] = f"Bearer {token}"
    if include_key and st.session_state.get("gemini_api_key"):
        headers["X-Gemini-API-Key"] = st.session_state.gemini_api_key
    try:
        response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=180, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to DocuMind. Check that the API is running at {API_URL}.") from exc
    if response.status_code == 401 and authenticated:
        st.session_state.pop("auth_token", None)
        st.session_state.pop("user", None)
        st.session_state.pop("gemini_api_key", None)
        raise AuthenticationError("Your session has expired. Please sign in again.")
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not response.ok:
        message = payload.get("detail", response.text or "The request failed.")
        raise RuntimeError(str(message))
    return payload


def write_browser_session_cookie(token, max_age):
    app_url = st.context.url or ""
    cookie = (
        f"{AUTH_COOKIE}={token}; Path=/; Max-Age={max_age}; SameSite=Lax"
        f"{'; Secure' if app_url.startswith('https://') else ''}"
    )
    st.html(
        f"<script>document.cookie = {json.dumps(cookie)};"
        "window.setTimeout(() => window.location.reload(), 150);</script>",
        unsafe_allow_javascript=True,
    )


def persist_login(result):
    st.session_state.auth_token = result["token"]
    st.session_state.user = result["user"]
    write_browser_session_cookie(result["token"], AUTH_SESSION_SECONDS)


def restore_login(cookie_controller):
    if st.session_state.get("auth_token"):
        return
    token = cookie_controller.get(AUTH_COOKIE)
    if not token:
        return
    try:
        result = api_request("GET", "/auth/me", auth_token=token)
    except AuthenticationError:
        write_browser_session_cookie("", 0)
        return
    st.session_state.auth_token = token
    st.session_state.user = result["user"]
    key_result = api_request("GET", "/account/gemini-key", auth_token=token, include_key=False)
    if key_result.get("api_key"):
        st.session_state.gemini_api_key = key_result["api_key"]
    else:
        st.session_state.pop("gemini_api_key", None)


def sign_out():
    try:
        api_request("POST", "/auth/logout")
    except RuntimeError as exc:
        st.error(f"Could not revoke the server session: {exc}")
        st.stop()
    st.session_state.clear()
    write_browser_session_cookie("", 0)
    st.stop()


def get_documents():
    return api_request("GET", "/documents", include_key=False).get("documents", [])


def sync_workspace_page():
    st.session_state.workspace_page = st.session_state.workspace_navigation


def select_sidebar_document(document_id):
    st.session_state.selected_document_id = document_id
    st.session_state.workspace_page = "Ask a question"
    st.session_state.workspace_navigation = "Ask a question"


def request_document_deletion(document_id):
    st.session_state.pending_delete_document_id = document_id


def display_filename(filename, max_stem_length=18):
    if "." not in filename:
        return filename if len(filename) <= max_stem_length else f"{filename[:max_stem_length]}…"
    stem, suffix = filename.rsplit(".", 1)
    suffix = f".{suffix}"
    if len(stem) <= max_stem_length:
        return filename
    return f"{stem[:max_stem_length]}…{suffix}"


def display_email(email, max_local_length=7):
    local_part, separator, domain = email.partition("@")
    if separator and len(local_part) > max_local_length:
        return f"{local_part[:max_local_length]}...@{domain}"
    return email


def delete_sidebar_document(document_id):
    try:
        result = api_request("DELETE", f"/documents/{document_id}")
    except RuntimeError as exc:
        st.error(f"Could not delete document: {exc}")
        return

    if st.session_state.get("selected_document_id") == document_id:
        st.session_state.pop("selected_document_id", None)
    st.session_state.get("document_chats", {}).pop(document_id, None)
    st.session_state.pop("pending_delete_document_id", None)
    st.session_state.document_action_notice = f"{result.get('filename', 'Document')} was deleted."
    st.rerun()


def open_upload_panel():
    st.session_state.show_upload_panel = True


def show_document_sidebar(documents, *, show_workspace_navigation):
    st.markdown('<span class="brand-mark">D</span><span style="font-weight:800;font-size:1.08rem">DocuMind</span>', unsafe_allow_html=True)
    st.caption("YOUR PRIVATE DOCUMENT WORKSPACE")
    st.divider()
    if show_workspace_navigation:
        st.session_state.setdefault("workspace_page", "Documents")
        st.session_state.setdefault(
            "workspace_navigation",
            st.session_state.workspace_page,
        )
        st.radio(
            "Workspace",
            ["Documents", "Ask a question"],
            key="workspace_navigation",
            on_change=sync_workspace_page,
            label_visibility="collapsed",
        )
        st.divider()
    st.caption("YOUR DOCUMENTS")
    if not documents:
        st.caption("Uploaded documents will appear here.")
    else:
        selected_id = st.session_state.get("selected_document_id")
        for document in documents:
            with st.container(key=f"sidebar-document-row-{document['id']}"):
                document_col, delete_col = st.columns([1, 0.14], gap="small")
                with document_col:
                    st.button(
                        f"📄　{display_filename(document['filename'])}",
                        key=f"sidebar_document_{document['id']}",
                        type="primary" if selected_id == document["id"] else "secondary",
                        use_container_width=True,
                        help=f"{document['filename']} · {document['chunks']} passages",
                        on_click=select_sidebar_document,
                        args=(document["id"],),
                    )
                with delete_col:
                    st.button(
                        " ",
                        key=f"delete_sidebar_document_{document['id']}",
                        type="secondary",
                        icon=":material/delete:",
                        help=f"Delete {document['filename']}",
                        on_click=request_document_deletion,
                        args=(document["id"],),
                    )

        pending_id = st.session_state.get("pending_delete_document_id")
        pending_document = next((item for item in documents if item["id"] == pending_id), None)
        if pending_document:
            st.warning(f"Delete {display_filename(pending_document['filename'], 14)}?")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(
                    "Delete",
                    key=f"confirm_delete_document_{pending_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    delete_sidebar_document(pending_id)
            with cancel_col:
                st.button(
                    "Cancel",
                    key="cancel_delete_document",
                    use_container_width=True,
                    on_click=lambda: st.session_state.pop("pending_delete_document_id", None),
                )
    st.divider()


def show_auth(cookie_controller):
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    left, right = st.columns([1.05, 0.95], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            """
            <div class="auth-hero">
              <div class="auth-brand"><span class="auth-brand-mark">D</span>DocuMind</div>
              <div>
                <h2>Your documents,<br>understood.</h2>
                <p>Ask questions in plain language. Get useful answers grounded in the documents you trust.</p>
                <div class="auth-features">
                  <div class="auth-feature">Keep your files organized in one private library</div>
                  <div class="auth-feature">Get answers with relevant source passages</div>
                  <div class="auth-feature">Your documents stay separated by account</div>
                </div>
              </div>
              <div class="auth-footnote">Private by design · Powered by your Gemini API key</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="auth-form-title">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-form-caption">Sign in to your DocuMind workspace</div>', unsafe_allow_html=True)
        sign_in, create_account = st.tabs(["Sign in", "Create account"])
        with sign_in:
            with st.form("sign_in_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                try:
                    result = api_request(
                        "POST", "/auth/login", authenticated=False,
                        json={"email": email, "password": password},
                    )
                    persist_login(result)
                    st.stop()
                except (RuntimeError, KeyError) as exc:
                    st.error(str(exc) or "Could not sign in.")
        with create_account:
            with st.form("create_account_form"):
                email = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Create a password", type="password", help="Use at least 8 characters.")
                submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted:
                try:
                    api_request(
                        "POST", "/auth/register", authenticated=False,
                        json={"email": email, "password": password},
                    )
                    result = api_request(
                        "POST", "/auth/login", authenticated=False,
                        json={"email": email, "password": password},
                    )
                    persist_login(result)
                    st.stop()
                except (RuntimeError, KeyError) as exc:
                    st.error(str(exc) or "Could not create your account.")


def show_key_setup(cookie_controller):
    try:
        documents = get_documents()
    except RuntimeError as exc:
        documents = []
        st.error(str(exc))
    with st.sidebar:
        show_document_sidebar(documents, show_workspace_navigation=False)
        st.caption("SIGNED IN AS")
        st.markdown(f"**{display_email(st.session_state.user['email'])}**")
        if st.button("Sign out", key="sidebar-sign-out", use_container_width=True):
            sign_out()
    _, center, _ = st.columns([1, 1.1, 1])
    with center:
        st.write("")
        st.write("")
        st.markdown('<span class="eyebrow">Secure account setup</span>', unsafe_allow_html=True)
        st.title("Connect your Gemini key")
        st.markdown(
            "Add your Google AI Studio API key to start asking questions. "
            "Your key is encrypted before it is saved to your account."
        )
        st.link_button("Get a Gemini API key ↗", "https://aistudio.google.com/app/apikey")
        with st.form("gemini_key_form"):
            key = st.text_input("Gemini API key", type="password", placeholder="Paste your API key")
            submitted = st.form_submit_button("Continue to DocuMind", type="primary")
        if submitted:
            if not key.strip():
                st.error("Enter a Gemini API key to continue.")
            else:
                try:
                    api_request("PUT", "/account/gemini-key", json={"api_key": key.strip()}, include_key=False)
                    st.session_state.gemini_api_key = key.strip()
                    st.rerun()
                except RuntimeError as exc:
                    st.error(f"Could not save your Gemini API key: {exc}")


def show_workspace(cookie_controller):
    user = st.session_state.user
    try:
        documents = get_documents()
    except RuntimeError as exc:
        st.error(str(exc))
        return
    with st.sidebar:
        show_document_sidebar(documents, show_workspace_navigation=True)
        page = st.session_state.workspace_page
        st.caption("SIGNED IN AS")
        st.markdown(f"**{display_email(user['email'])}**")
        if st.button("Update Gemini key", key="sidebar-update-gemini-key", use_container_width=True):
            st.session_state.editing_gemini_key = True
            st.rerun()
        if st.button("Sign out", key="sidebar-sign-out", use_container_width=True):
            sign_out()

    if notice := st.session_state.pop("document_action_notice", None):
        st.success(notice)

    if st.session_state.get("editing_gemini_key"):
        st.markdown('<span class="eyebrow">Account settings</span>', unsafe_allow_html=True)
        st.title("Update Gemini key")
        st.caption("Your current key is prefilled and will be encrypted when saved.")
        with st.form("edit_gemini_key_form"):
            key = st.text_input(
                "Gemini API key",
                value=st.session_state.get("gemini_api_key", ""),
                type="password",
            )
            save_key = st.form_submit_button("Save Gemini key", type="primary")
        cancel_col, _ = st.columns([1, 5])
        with cancel_col:
            cancel = st.button("Cancel")
        if cancel:
            st.session_state.editing_gemini_key = False
            st.rerun()
        if save_key:
            if not key.strip():
                st.error("Enter a Gemini API key.")
            else:
                try:
                    api_request("PUT", "/account/gemini-key", json={"api_key": key.strip()}, include_key=False)
                    st.session_state.gemini_api_key = key.strip()
                    st.session_state.editing_gemini_key = False
                    st.success("Gemini API key updated.")
                    st.rerun()
                except RuntimeError as exc:
                    st.error(f"Could not update your Gemini API key: {exc}")
        return

    if page == "Documents":
        title_col, search_col, upload_col = st.columns([1.15, 2.2, 1], vertical_alignment="center")
        with title_col:
            st.title("Documents")
        with search_col:
            search_query = st.text_input(
                "Search documents",
                placeholder="⌕  Search documents…",
                label_visibility="collapsed",
                key="document_search_query",
            )
        with upload_col:
            st.button(
                "＋  Upload documents",
                type="primary",
                use_container_width=True,
                on_click=open_upload_panel,
            )

        st.markdown(
            '<div class="dashboard-notice"><div class="dashboard-notice-icon">●</div><div>'
            '<strong>Your private document library</strong><br>'
            '<span>Uploaded files are saved to your account. Select a document from the sidebar to ask questions about it.</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        if st.session_state.get("show_upload_panel", False):
            with st.expander("Upload and index documents", expanded=True):
                uploads = st.file_uploader(
                    "Choose PDF, Word, TXT, or Markdown documents",
                    type=SUPPORTED_TYPES,
                    accept_multiple_files=True,
                    help="Up to 15 MB per file.",
                    key="library_file_uploader",
                )
                upload_col, close_col = st.columns([1, 5])
                with upload_col:
                    upload_clicked = st.button(
                        "Upload and index",
                        type="primary",
                        disabled=not uploads,
                        key="library_upload_submit",
                    )
                with close_col:
                    st.button(
                        "Close",
                        key="library_upload_close",
                        on_click=lambda: st.session_state.update(show_upload_panel=False),
                    )
                if upload_clicked:
                    progress = st.progress(0, text="Preparing your documents…")
                    for position, uploaded in enumerate(uploads, start=1):
                        try:
                            result = api_request(
                                "POST",
                                "/documents",
                                include_key=True,
                                files={
                                    "file": (
                                        uploaded.name,
                                        uploaded.getvalue(),
                                        uploaded.type or "application/octet-stream",
                                    )
                                },
                            )
                            progress.progress(position / len(uploads), text=f"Added {result['filename']}")
                        except (RuntimeError, KeyError) as exc:
                            st.error(f"{uploaded.name}: {exc}")
                            progress.empty()
                            return
                    st.session_state.show_upload_panel = False
                    st.success("Your documents are ready to search.")
                    st.rerun()

        st.markdown('<div class="dashboard-section-title">My documents</div>', unsafe_allow_html=True)
        control_col, count_col = st.columns([3, 1], vertical_alignment="center")
        with control_col:
            all_types = sorted({
                document["filename"].rsplit(".", 1)[-1].lower()
                for document in documents
                if "." in document["filename"]
            })
            filter_col, sort_col = st.columns([1, 1])
            with filter_col:
                selected_type = st.selectbox(
                    "Filter by file type",
                    ["All file types", *all_types],
                    label_visibility="collapsed",
                    key="document_type_filter",
                )
            with sort_col:
                st.selectbox(
                    "Sort documents",
                    ["Name (A–Z)", "Name (Z–A)"],
                    label_visibility="collapsed",
                    key="document_sort_order",
                )
        filtered_documents = [
            document for document in documents
            if (selected_type == "All file types" or document["filename"].rsplit(".", 1)[-1].lower() == selected_type)
            and search_query.strip().casefold() in document["filename"].casefold()
        ]
        if st.session_state.document_sort_order == "Name (Z–A)":
            filtered_documents.reverse()
        with count_col:
            st.caption(f"{len(filtered_documents)} of {len(documents)} documents")

        if not documents:
            with st.container(border=True):
                st.markdown("**No documents yet**")
                st.caption("Upload a PDF, Word, TXT, or Markdown file to add it to your personal library.")
        elif not filtered_documents:
            st.info("No documents match the current search and file type filter.")
        else:
            st.markdown(
                '<div class="document-table-heading">Name　　　　　　　　　　　　　 File type　　　　　　　　 Passages　　　　　　　　 Status</div>',
                unsafe_allow_html=True,
            )
            table_rows = [
                {
                    "Name": document["filename"],
                    "File type": document["filename"].rsplit(".", 1)[-1].upper(),
                    "Passages": document["chunks"],
                    "Status": "Indexed",
                }
                for document in filtered_documents
            ]
            st.dataframe(
                table_rows,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Name": st.column_config.TextColumn("Name", width="large"),
                    "File type": st.column_config.TextColumn("File type", width="small"),
                    "Passages": st.column_config.NumberColumn("Passages", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                },
            )
            st.caption("Select a document from the sidebar to open its private question-and-answer chat.")
    else:
        st.markdown('<span class="eyebrow">Grounded answers</span>', unsafe_allow_html=True)
        st.title("Ask your documents")
        st.markdown('<p class="muted">Get a clear answer with source passages from your personal library.</p>', unsafe_allow_html=True)
        if not documents:
            st.info("Upload a document first to start a conversation.")
            st.caption("Choose Documents in the workspace menu to add files.")
            return
        document_ids = [document["id"] for document in documents]
        if st.session_state.get("selected_document_id") not in document_ids:
            st.session_state.selected_document_id = document_ids[0]
        document_by_id = {document["id"]: document for document in documents}
        selected_document_id = st.selectbox(
            "Ask about",
            options=document_ids,
            format_func=lambda document_id: document_by_id[document_id]["filename"],
            key="selected_document_id",
        )
        st.caption("Answers will use passages from this document only.")
        document = document_by_id[selected_document_id]
        st.session_state.setdefault("document_chats", {})
        messages = st.session_state.document_chats.setdefault(selected_document_id, [])
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("sources"):
                    with st.expander("View source passages"):
                        for source in message["sources"]:
                            st.markdown(f"**{source['filename']} · Passage {source['chunk_id']}**")
                            st.write(source["text"])
        question = st.chat_input("Ask something about your documents…")
        if question:
            messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Searching your library…"):
                    try:
                        result = api_request(
                            "POST", "/chat", include_key=True,
                            json={
                                "question": question,
                                "top_k": 4,
                                "document_id": selected_document_id,
                            },
                        )
                        st.markdown(result["answer"])
                        if result.get("sources"):
                            with st.expander("View source passages"):
                                for source in result["sources"]:
                                    st.markdown(f"**{source['filename']} · Passage {source['chunk_id']}**")
                                    st.write(source["text"])
                        messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": result.get("sources", []),
                        })
                    except (RuntimeError, KeyError) as exc:
                        st.error(str(exc))


cookie_controller = CookieController(key="documind_auth_cookies")
if st.session_state.get("documind_auth_cookies") is None:
    st.info("Checking your saved sign-in session…")
    st.stop()

try:
    restore_login(cookie_controller)
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if not st.session_state.get("auth_token"):
    show_auth(cookie_controller)
elif not st.session_state.get("gemini_api_key"):
    show_key_setup(cookie_controller)
else:
    show_workspace(cookie_controller)
