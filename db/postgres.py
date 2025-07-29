# 📁 db/postgres.py
import asyncpg
import os
import logging
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

async def init_db():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")

    _pool = await asyncpg.create_pool(DATABASE_URL)
    async with _pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                quiz_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logging.info("✅ Підключення до PostgreSQL успішне та таблиця створена.")

async def save_result(user_id, user_name, quiz_name, score):
    async with _pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO results (user_id, user_name, quiz_name, score) VALUES ($1, $2, $3, $4)',
            user_id, user_name, quiz_name, score
        )

async def get_top_results(quiz_name, limit=5):
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT user_name, MAX(score) as max_score
            FROM results
            WHERE quiz_name = $1
            GROUP BY user_id, user_name
            ORDER BY max_score DESC
            LIMIT $2
            ''',
            quiz_name, limit
        )
        return [(r["user_name"], r["max_score"]) for r in rows]

async def get_attempt_count(user_id, quiz_name):
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT COUNT(*) FROM results WHERE user_id = $1 AND quiz_name = $2',
            user_id, quiz_name
        )
        return row["count"] if row else 0
