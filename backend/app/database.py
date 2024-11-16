import sqlite3
from contextlib import contextmanager
from typing import List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Note:
    id: Optional[int]
    title: str
    note: str
    tags: List[str]
    quiz: Optional[str]
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: Tuple):
        return cls(
            id=row[0],
            title=row[1],
            note=row[2],
            tags=row[3].split(',') if row[3] else [],
            quiz=row[4],
            created_at=datetime.fromisoformat(row[5])
        )

class Database:
    def __init__(self, db_path: str = 'app.db'):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    note TEXT NOT NULL,
                    tags TEXT,
                    quiz TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def insert_note(self, title: str, note: str, tags: List[str], quiz: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO notes (title, note, tags, quiz) VALUES (?, ?, ?, ?)',
                (title, note, ','.join(tags), quiz)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_notes(self, limit: int = 50, offset: int = 0) -> List[Note]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM notes ORDER BY created_at DESC LIMIT ? OFFSET ?',
                (limit, offset)
            )
            return [Note.from_row(row) for row in cursor.fetchall()]
    
    def get_note_by_id(self, note_id: int) -> Optional[Note]:
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
            row = cursor.fetchone()
            return Note.from_row(row) if row else None
    
    def search_notes(self, query: str, tags: List[str] = None) -> List[Note]:
        with self.get_connection() as conn:
            sql = 'SELECT * FROM notes WHERE note LIKE ?'
            params = [f'%{query}%']
            
            if tags:
                tag_conditions = ' OR '.join(['tags LIKE ?' for _ in tags])
                sql += f' AND ({tag_conditions})'
                params.extend([f'%{tag}%' for tag in tags])
            
            cursor = conn.execute(sql, params)
            return [Note.from_row(row) for row in cursor.fetchall()]
            
    def save_template(self, name: str, content: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO templates (name, content) VALUES (?, ?)',
                (name, content)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_templates(self) -> List[Tuple[str, str]]:
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT name, content FROM templates')
            return cursor.fetchall()