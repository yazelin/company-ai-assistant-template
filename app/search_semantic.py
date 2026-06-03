"""Semantic retrieval — the Part 2 upgrade to app/search.py's keyword baseline.

Same interface as search_docs: (query, limit) -> [{score, path, snippet}], but
ranks by embedding cosine similarity (fastembed, local, no API key) instead of
keyword counts. Requires the `semantic` extra: uv sync --extra semantic."""
import json
import numpy as np
from fastembed import TextEmbedding
from .db import conn

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_model_cache = None


def _model():
    global _model_cache
    if _model_cache is None:
        _model_cache = TextEmbedding(model_name=MODEL_NAME)
    return _model_cache


def index_semantic():
    """Embed and store any documents that lack an embedding. Idempotent."""
    c = conn()
    done = {r["path"] for r in c.execute("select path from embeddings")}
    rows = [r for r in c.execute("select path, content from documents") if r["path"] not in done]
    if not rows:
        return 0
    vectors = list(_model().embed([r["content"] for r in rows]))
    for r, v in zip(rows, vectors):
        c.execute("insert or replace into embeddings(path, vector) values(?, ?)",
                  (r["path"], json.dumps([float(x) for x in v])))
    c.commit()
    return len(rows)


def _cosine(a, b):
    a = np.array(a); b = np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_semantic(query, limit=5):
    index_semantic()
    c = conn()
    qv = list(_model().embed([query]))[0]
    contents = {r["path"]: r["content"] for r in c.execute("select path, content from documents")}
    scored = []
    for r in c.execute("select path, vector from embeddings"):
        scored.append((_cosine(qv, json.loads(r["vector"])), r["path"], contents[r["path"]][:1200]))
    scored.sort(reverse=True)
    return [{"score": s, "path": p, "snippet": sn} for s, p, sn in scored[:limit]]
