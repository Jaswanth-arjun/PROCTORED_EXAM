import aiosqlite
import json
from datetime import datetime
from app.config import settings

DB_PATH = settings.DATABASE_PATH


async def init_db():
    """Initialize the SQLite database with the required schema."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                options TEXT DEFAULT '[]',
                topic TEXT DEFAULT 'General',
                correct_answer TEXT NOT NULL,
                answer_text TEXT DEFAULT '',
                reasoning TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                source TEXT DEFAULT 'upload',
                processing_time_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_topic
            ON questions(topic)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_created
            ON questions(created_at DESC)
        """)
        await db.commit()


async def save_question(result: dict) -> int:
    """Save an analysis result to the database. Returns the inserted row ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO questions
                (question_text, options, topic, correct_answer, answer_text,
                 reasoning, confidence, source, processing_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.get("question", ""),
                json.dumps(result.get("options", [])),
                result.get("topic", "General"),
                result.get("correct_answer", ""),
                result.get("answer_text", ""),
                result.get("reasoning", ""),
                result.get("confidence", 0.0),
                result.get("source", "upload"),
                result.get("processing_time_ms", 0),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_history(limit: int = 50, offset: int = 0) -> list[dict]:
    """Retrieve question history ordered by most recent first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM questions
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["options"] = json.loads(item.get("options", "[]"))
            results.append(item)
        return results


async def get_stats() -> dict:
    """Get aggregate statistics about stored questions."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM questions")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT topic, COUNT(*) as count FROM questions GROUP BY topic ORDER BY count DESC"
        )
        topics = [{"topic": r[0], "count": r[1]} for r in await cursor.fetchall()]

        cursor = await db.execute("SELECT AVG(confidence) FROM questions")
        avg_confidence = (await cursor.fetchone())[0] or 0.0

        return {
            "total_questions": total,
            "topics": topics,
            "average_confidence": round(avg_confidence, 1),
        }
