from fastapi import FastAPI
from pydantic import BaseModel
from .search import search_docs
from .ai import answer
app=FastAPI(title="Company AI Assistant Template")
class AskRequest(BaseModel): question:str
@app.get("/health")
def health(): return {"ok":True}
@app.post("/ask")
async def ask(req:AskRequest):
    docs=search_docs(req.question); return {"answer":await answer(req.question,docs),"sources":docs}
