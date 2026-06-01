from .db import conn
def search_docs(query,limit=5):
    words=[w for w in query.lower().split() if len(w)>1]; rows=conn().execute("select path,content from documents").fetchall(); scored=[]
    for r in rows:
        text=r["content"].lower(); score=sum(text.count(w) for w in words)
        if score: scored.append((score,r["path"],r["content"][:1200]))
    scored.sort(reverse=True); return [{"score":s,"path":p,"snippet":sn} for s,p,sn in scored[:limit]]
