"""
SmartDesk AI Service — FastAPI RAG Backend
==========================================
Endpoints
---------
GET  /                    Health check
GET  /health              Stats (chunks stored)
POST /process-document    Upload PDF → chunk → embed → store in ChromaDB
POST /chat                Question → retrieve top-3 chunks → return answer + sources
"""

import io
import uuid
import logging
import os
from typing import List

import chromadb
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SmartDesk AI Service",
    version="1.1.0",
    description="RAG service: upload PDFs, ask questions, get answers with sources.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHUNK_SIZE       = 500          # characters per chunk
CHUNK_OVERLAP    = 50           # overlapping characters between chunks
TOP_K            = 5            # similar chunks to retrieve per query
COLLECTION_NAME  = "documents"
CHROMA_PATH      = "./chroma_db"  # persisted to disk

# ---------------------------------------------------------------------------
# Models — initialized once at startup
# ---------------------------------------------------------------------------

logger.info("⏳ Loading embedding model (all-MiniLM-L6-v2)...")
_embedder = SentenceTransformer("all-MiniLM-L6-v2")

logger.info("⏳ Initializing Gemini model...")
# Configure Gemini using the API key
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY environment variable is not set!")
_generator = genai.GenerativeModel('gemini-1.5-flash')

_chroma = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _chroma.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
logger.info(f"✅ ChromaDB ready - {_collection.count()} chunk(s) stored at '{CHROMA_PATH}'")

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text_pdf(data: bytes) -> str:
    """Return concatenated text from all pages of a PDF byte-string (PyPDF2)."""
    reader = PdfReader(io.BytesIO(data))
    pages: List[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text using Langchain's RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        is_separator_regex=False,
    )
    return splitter.split_text(text)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {"message": "SmartDesk AI Service Running"}


@app.get("/health", tags=["Health"])
def health():
    """Liveness check + quick stats."""
    return {"status": "healthy", "chunks_stored": _collection.count()}


@app.post("/process-document", tags=["Documents"])
async def process_document(file: UploadFile = File(...)):
    """Upload a PDF and ingest it into ChromaDB."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    raw = await file.read()
    try:
        text = _extract_text_pdf(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {exc}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable text found in this PDF.")

    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Text extracted but produced no chunks.")

    embeddings = _embedder.encode(chunks, show_progress_bar=False).tolist()

    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": file.filename, "chunk_index": i, "doc_id": doc_id}
        for i in range(len(chunks))
    ]

    _collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "message": "Document processed successfully",
        "chunks": len(chunks),
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """Ask a question against the stored documents."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    total = _collection.count()
    if total == 0:
        raise HTTPException(
            status_code=404,
            detail="No documents ingested yet. Upload a PDF via POST /process-document first.",
        )

    # 1. Embed query
    query_vec = _embedder.encode([question], show_progress_bar=False).tolist()

    # 2. Retrieve
    results = _collection.query(
        query_embeddings=query_vec,
        n_results=min(TOP_K, total),
        include=["documents", "metadatas"],
    )

    retrieved_chunks: List[str] = results["documents"][0]
    
    # 3. Generate Answer
    # We use a structured prompt to guide the small T5 model
    context = "\n---\n".join(retrieved_chunks)
    
    prompt = (
        "Answer the question in a lively, engaging, and informative tone based ONLY on the following context. "
        "Make sure your response is helpful and energetic. "
        "If the answer is not in the context, say 'I do not have enough information'.\n"
        f"Context: {context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
    
    try:
        # Generate answer using Gemini API
        response = _generator.generate_content(prompt)
        answer = response.text.strip()
        
        if not answer:
            answer = "I'm sorry, I couldn't generate a clear answer from the document."
            
    except Exception as e:
        logger.error(f"Generation error: {e}")
        answer = "I'm sorry, I encountered an error while generating the answer."

    return ChatResponse(answer=answer, sources=retrieved_chunks)