import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="DocuMind RAG", page_icon="📚", layout="wide")
st.title("📚 DocuMind RAG")
st.caption("Upload documents and ask questions grounded in their contents.")

with st.sidebar:
    st.subheader("Backend status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        health.raise_for_status()
        st.success("FastAPI connected")
        st.metric("Indexed documents", health.json().get("documents", 0))
    except requests.RequestException:
        st.error("Cannot connect to FastAPI")
        st.caption(f"Expected API at {API_URL}")
    st.divider()
    st.markdown("**Supported formats**")
    st.write("PDF, TXT, Markdown")

st.subheader("1. Upload documents")
uploads = st.file_uploader(
    "Choose one or more files",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True,
)
if st.button("Index selected documents", type="primary", disabled=not uploads):
    progress = st.empty()
    for uploaded in uploads:
        progress.info(f"Indexing {uploaded.name}…")
        try:
            response = requests.post(
                f"{API_URL}/documents",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")},
                timeout=180,
            )
            if response.ok:
                result = response.json()
                st.success(f"{result['filename']}: indexed {result['chunks_added']} chunks")
            else:
                st.error(f"{uploaded.name}: {response.text}")
        except requests.RequestException as exc:
            st.error(f"Upload failed: {exc}")
    progress.empty()
    st.rerun()

st.subheader("2. Ask a question")
question = st.text_area("Question", placeholder="What are the main points in my documents?")
top_k = st.slider("Number of passages to retrieve", min_value=1, max_value=10, value=4)
if st.button("Ask DocuMind", disabled=not question.strip()):
    with st.spinner("Searching documents and asking Gemini…"):
        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"question": question, "top_k": top_k},
                timeout=180,
            )
            if response.ok:
                result = response.json()
                st.markdown("### Answer")
                st.write(result["answer"])
                with st.expander("Retrieved source passages"):
                    for i, source in enumerate(result.get("sources", []), start=1):
                        st.markdown(f"**Source {i}: {source['filename']} — chunk {source['chunk_id']}**")
                        st.caption(f"Similarity score: {source['score']}")
                        st.write(source["text"])
                        st.divider()
            else:
                st.error(response.text)
        except requests.RequestException as exc:
            st.error(f"Could not reach the API: {exc}")

st.subheader("Indexed documents")
try:
    response = requests.get(f"{API_URL}/documents", timeout=5)
    response.raise_for_status()
    documents = response.json().get("documents", [])
    if documents:
        st.dataframe(documents, use_container_width=True, hide_index=True)
    else:
        st.info("No documents indexed yet. Upload a file above to begin.")
except requests.RequestException:
    st.info("Start the FastAPI backend to see indexed documents.")
