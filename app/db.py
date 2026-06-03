import os, sqlite3
from dotenv import load_dotenv
load_dotenv(); DB=os.getenv("DATABASE_URL","assistant.db")
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("create table if not exists documents(id integer primary key,path text unique,content text)")
    c.execute("create table if not exists embeddings(path text primary key,vector text)")
    return c
