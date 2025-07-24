import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'results.db')

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_name TEXT,
                quiz_name TEXT,
                score INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

async def save_result(user_id, user_name, quiz_name, score):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO results (user_id, user_name, quiz_name, score) VALUES (?, ?, ?, ?)',
            (user_id, user_name, quiz_name, score)
        )
        await db.commit()

async def get_top_results(quiz_name, limit=5):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT user_name, MAX(score) FROM results WHERE quiz_name = ? GROUP BY user_id ORDER BY MAX(score) DESC LIMIT ?',
            (quiz_name, limit)
        ) as cursor:
            return await cursor.fetchall()

async def get_attempt_count(user_id, quiz_name):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT COUNT(*) FROM results WHERE user_id = ? AND quiz_name = ?',
            (user_id, quiz_name)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0