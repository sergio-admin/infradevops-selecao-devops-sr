import os
from contextlib import asynccontextmanager

import pymysql
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr, Field

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    comment TEXT NOT NULL,
    content_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_content_id (content_id)
)
"""


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
        ssl={"check_hostname": False},
    )


@asynccontextmanager
async def lifespan(app):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(CREATE_TABLE)
    yield


app = FastAPI(title="Comments API", lifespan=lifespan)
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app)


class CommentIn(BaseModel):
    email: EmailStr
    comment: str = Field(min_length=1, max_length=5000)
    content_id: int


@app.post("/api/comment/new", status_code=201)
def create_comment(data: CommentIn):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO comments (email, comment, content_id) VALUES (%s, %s, %s)",
            (data.email, data.comment, data.content_id),
        )
        return {"id": cur.lastrowid, **data.model_dump()}


@app.get("/api/comment/list/{content_id}")
def list_comments(content_id: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, comment, content_id, created_at "
            "FROM comments WHERE content_id = %s ORDER BY id",
            (content_id,),
        )
        return cur.fetchall()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
