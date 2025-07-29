# 📁 db/postgres.py
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL)
    async with _pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                user_name TEXT,
                quiz_name TEXT,
                score INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS question_results (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                quiz_name TEXT,
                question_index INT,
                elapsed_seconds INT,
                points INT,
                is_correct BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

async def save_result(user_id, user_name, quiz_name, score):
    async with _pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO results (user_id, user_name, quiz_name, score)
            VALUES ($1, $2, $3, $4)
        ''', user_id, user_name, quiz_name, score)

async def save_question_result(user_id, quiz_name, question_index, elapsed_seconds, points, is_correct):
    async with _pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO question_results (user_id, quiz_name, question_index, elapsed_seconds, points, is_correct)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', user_id, quiz_name, question_index, elapsed_seconds, points, is_correct)

async def get_top_results(quiz_name, limit=5):
    async with _pool.acquire() as conn:
        return await conn.fetch('''
            SELECT user_name, MAX(score) FROM results
            WHERE quiz_name = $1
            GROUP BY user_id, user_name
            ORDER BY MAX(score) DESC
            LIMIT $2
        ''', quiz_name, limit)

async def get_attempt_count(user_id, quiz_name):
    async with _pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT COUNT(*) FROM results WHERE user_id = $1 AND quiz_name = $2
        ''', user_id, quiz_name)
        return row[0] if row else 0

async def get_all_question_results():
    async with _pool.acquire() as conn:
        return await conn.fetch('''
            SELECT user_id, quiz_name, question_index, elapsed_seconds, points, is_correct, timestamp
            FROM question_results
        ''')
