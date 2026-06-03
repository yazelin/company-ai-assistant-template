import os
from fastapi import FastAPI
from pydantic import BaseModel
from .search import search_docs
from .ai import answer
app=FastAPI(title="Company AI Assistant Template")
class AskRequest(BaseModel): question:str
def _retrieve(query):
    # SEARCH_BACKEND=semantic uses the Part 2 embedding retrieval (needs the
    # `semantic` extra); the default keeps the zero-extra keyword baseline so
    # the base import chain never touches fastembed.
    if os.getenv("SEARCH_BACKEND","keyword")=="semantic":
        from .search_semantic import search_semantic
        return search_semantic(query)
    return search_docs(query)
@app.get("/health")
def health(): return {"ok":True}
@app.post("/ask")
async def ask(req:AskRequest):
    docs=_retrieve(req.question); return {"answer":await answer(req.question,docs),"sources":docs}
