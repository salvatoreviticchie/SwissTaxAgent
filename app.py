"""
SwissTaxAgent — Streamlit UI
"""

import os
import tempfile

import streamlit as st
from openai import OpenAI
from pinecone import Pinecone

from agents.orchestrator import Orchestrator
from retrieval.document_ingestion import ingest_file

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SwissTaxAgent",
    page_icon="🇨🇭",
    layout="wide",
)

# ── Secrets ───────────────────────────────────────────────────────────────────
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", st.secrets.get("PINECONE_API_KEY", ""))
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", st.secrets.get("PINECONE_INDEX_NAME", "swiss-tax"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", st.secrets.get("OPENROUTER_API_KEY", ""))
MODEL = os.getenv("MODEL", st.secrets.get("MODEL", "openai/gpt-4o"))


# ── Cached resources ──────────────────────────────────────────────────────────
@st.cache_resource
def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX_NAME)


@st.cache_resource
def get_openrouter_client():
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


@st.cache_resource
def get_orchestrator():
    return Orchestrator(
        pinecone_index=get_pinecone_index(),
        openrouter_client=get_openrouter_client(),
        model=MODEL,
    )


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🇨🇭 SwissTaxAgent")
    st.caption("Canton Vaud · ICC / IFD")
    st.divider()

    st.subheader("Upload Documents")
    uploaded_files = st.file_uploader(
        "PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files and st.button("Ingest Documents"):
        index = get_pinecone_index()
        retriever_module = __import__(
            "retrieval.pinecone_retriever", fromlist=["PineconeRetriever"]
        )
        retriever = retriever_module.PineconeRetriever(index)

        with st.spinner("Ingesting…"):
            total = 0
            for uf in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=uf.name) as tmp:
                    tmp.write(uf.read())
                    tmp_path = tmp.name
                chunks = ingest_file(tmp_path, source_name=uf.name)
                retriever.upsert_chunks(chunks)
                total += len(chunks)
        st.success(f"Ingested {total} chunks from {len(uploaded_files)} file(s).")

    st.divider()
    if st.button("Clear conversation"):
        st.session_state.messages = []
        get_orchestrator().memory.clear()
        st.rerun()


# ── Main chat UI ──────────────────────────────────────────────────────────────
st.title("SwissTaxAgent")
st.caption("Ask me anything about your Swiss tax declaration (Canton Vaud, ICC/IFD).")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask a tax question…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = get_orchestrator().run(prompt)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
