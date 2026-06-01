import sys
from pathlib import Path
from .db import conn
def ingest(root):
    c=conn()
    for p in Path(root).rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md",".txt"}:
            c.execute("insert or replace into documents(path,content) values(?,?)",(str(p),p.read_text(encoding="utf-8",errors="ignore"))); print("ingested",p)
    c.commit()
if __name__=="__main__": ingest(sys.argv[1] if len(sys.argv)>1 else "sample_docs")
