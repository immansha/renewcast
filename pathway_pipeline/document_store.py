"""
document_store.py
Live RAG document store. Watches /docs for new/changed files,
re-chunks and re-indexes automatically within seconds.
"""

import hashlib, os, struct, threading, time
from typing import Dict, List, Optional

try:
    import faiss
    import numpy as np
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

from pathway_pipeline.config import DOCS_DIR

CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80
EMBED_DIM     = 384


def _hash_embed(text: str, dim: int = EMBED_DIM) -> List[float]:
    """Deterministic hash-based embedding (replace with sentence-transformers in prod)."""
    vec = []
    for i in range(dim):
        h   = hashlib.md5(f"{text}{i}".encode()).digest()
        val = struct.unpack("f", h[:4])[0]
        vec.append(val)
    norm = sum(v ** 2 for v in vec) ** 0.5
    return [v / (norm + 1e-8) for v in vec]


class LiveDocumentStore:
    def __init__(self, docs_dir: str = DOCS_DIR):
        self.docs_dir   = docs_dir
        self.chunks:     List[Dict]        = []
        self.embeddings: List[List[float]] = []
        self.index                         = None
        self.file_hashes: Dict[str, str]   = {}
        self._lock = threading.Lock()
        os.makedirs(docs_dir, exist_ok=True)
        self._build_index()

    def _file_hash(self, path: str) -> str:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _extract_text(self, path: str) -> str:
        if path.endswith(".pdf"):
            if not HAS_PDF:
                return f"[PDF: {os.path.basename(path)}]"
            try:
                return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
            except Exception as e:
                return f"[Error reading PDF: {e}]"
        elif path.endswith(".txt"):
            with open(path) as f:
                return f.read()
        return ""

    def _chunk_text(self, text: str, source: str) -> List[Dict]:
        chunks, i = [], 0
        while i < len(text):
            chunk = text[i:i + CHUNK_SIZE]
            if chunk.strip():
                chunks.append({"text": chunk, "source": source, "chunk_idx": len(chunks)})
            i += CHUNK_SIZE - CHUNK_OVERLAP
        return chunks

    def _build_index(self):
        all_chunks, all_embeddings = [], []
        if not os.path.exists(self.docs_dir):
            return
        for fname in os.listdir(self.docs_dir):
            if not (fname.endswith(".pdf") or fname.endswith(".txt")):
                continue
            fpath = os.path.join(self.docs_dir, fname)
            self.file_hashes[fname] = self._file_hash(fpath)
            text   = self._extract_text(fpath)
            chunks = self._chunk_text(text, fname)
            embeds = [_hash_embed(c["text"]) for c in chunks]
            all_chunks.extend(chunks)
            all_embeddings.extend(embeds)
            print(f"[DocumentStore] Indexed {fname} → {len(chunks)} chunks")

        with self._lock:
            self.chunks     = all_chunks
            self.embeddings = all_embeddings
            if HAS_FAISS and all_embeddings:
                mat        = np.array(all_embeddings, dtype=np.float32)
                self.index = faiss.IndexFlatIP(EMBED_DIM)
                self.index.add(mat)
                print(f"[DocumentStore] FAISS index ready: {self.index.ntotal} vectors")

    def watch_forever(self, poll_sec: int = 5):
        print(f"[DocumentStore] Watching {self.docs_dir} ...")
        while True:
            time.sleep(poll_sec)
            if not os.path.exists(self.docs_dir):
                continue
            for fname in os.listdir(self.docs_dir):
                if not (fname.endswith(".pdf") or fname.endswith(".txt")):
                    continue
                fpath = os.path.join(self.docs_dir, fname)
                if self.file_hashes.get(fname) != self._file_hash(fpath):
                    print(f"[DocumentStore] Change detected in {fname} — re-indexing...")
                    self._build_index()
                    break

    def query(self, question: str, top_k: int = 3) -> List[Dict]:
        with self._lock:
            if not self.chunks:
                return [{"text": "No documents indexed.", "source": "none"}]
            if HAS_FAISS and self.index and self.index.ntotal > 0:
                import numpy as np
                q   = np.array([_hash_embed(question)], dtype=np.float32)
                scores, idxs = self.index.search(q, min(top_k, len(self.chunks)))
                return [
                    {**self.chunks[i], "score": float(s)}
                    for s, i in zip(scores[0], idxs[0]) if 0 <= i < len(self.chunks)
                ]
            return self.chunks[:top_k]


_STORE: Optional[LiveDocumentStore] = None

def get_store() -> LiveDocumentStore:
    global _STORE
    if _STORE is None:
        _STORE = LiveDocumentStore()
    return _STORE
