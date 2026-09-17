import logging
import os

import aiomysql

logger = logging.getLogger("fastapi_langchain_app")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "app")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "app_password")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "summarizer")

# Three columns the request is about, plus an id: the raw text the user sent,
# the summary the LLM produced, and when it happened. created_at defaults to
# the insert time server-side, so callers never need to pass a timestamp.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    input_text TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


async def create_pool() -> aiomysql.Pool:
    pool = await aiomysql.create_pool(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DATABASE,
        autocommit=True,
        minsize=1,
        maxsize=5,
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(CREATE_TABLE_SQL)
    return pool


async def save_summary(pool: aiomysql.Pool, input_text: str, summary_text: str) -> None:
    # Same "auxiliary service outage shouldn't fail the request" philosophy as
    # the Redis cache in this example's earlier version: history logging is a
    # side effect, not something worth a 502 over if MySQL hiccups.
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO summaries (input_text, summary_text) VALUES (%s, %s)",
                    (input_text, summary_text),
                )
    except Exception:
        logger.warning("Failed to save summary to MySQL - summary was still returned", exc_info=True)


async def fetch_recent(pool: aiomysql.Pool, limit: int) -> list[dict]:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, input_text, summary_text, created_at FROM summaries ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            return await cur.fetchall()
