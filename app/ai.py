import os, httpx
async def answer(question, docs):
    context="\n\n".join(f"[{d['path']}]\n{d['snippet']}" for d in docs)
    if os.getenv("AI_PROVIDER","echo")=="echo": return "Echo answer. Retrieved context:\n"+(context or "No matching docs.")
    payload={"model":os.getenv("MODEL_NAME","gpt-4o-mini"),"messages":[{"role":"system","content":"Answer using company context. If unknown, say so."},{"role":"user","content":f"Context:\n{context}\n\nQuestion: {question}"}]}
    async with httpx.AsyncClient(timeout=60) as c:
        r=await c.post(os.getenv("HTTP_LLM_ENDPOINT"),headers={"Authorization":"Bearer "+os.getenv("HTTP_LLM_API_KEY","")},json=payload); r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]
