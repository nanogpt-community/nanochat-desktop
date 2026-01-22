"""Local database using SQLite."""

import sqlite3
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from nanochat.api.models import Conversation, Message
from .xdg import get_data_dir
from .sync_status import SyncStatus


class Database:
    """SQLite database for caching with thread-local connections."""

    def __init__(self) -> None:
        self.db_path = get_data_dir() / "cache.db"
        # Thread-local storage for connections
        self._local = threading.local()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self.connection as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    assistant_id TEXT,
                    project_id TEXT,
                    model_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    pinned BOOLEAN DEFAULT 0,
                    generating BOOLEAN DEFAULT 0,
                    cost_usd REAL,
                    sync_status TEXT DEFAULT 'synced',
                    raw_data TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    reasoning TEXT,
                    model_id TEXT,
                    created_at TEXT NOT NULL,
                    token_count INTEGER,
                    cost_usd REAL,
                    starred BOOLEAN,
                    sync_status TEXT DEFAULT 'synced',
                    local_id TEXT,
                    response_time_ms INTEGER,
                    raw_data TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )
            # Run migrations for existing databases
            self._migrate(conn)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
                ON conversations(updated_at DESC)
                """
            )

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Run database migrations for existing databases.

        Adds new columns if they don't exist. Safe to run multiple times.
        """
        # Get current column info for conversations table
        cursor = conn.execute("PRAGMA table_info(conversations)")
        conv_columns = {row["name"] for row in cursor.fetchall()}

        # Add sync_status to conversations if missing
        if "sync_status" not in conv_columns:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN sync_status TEXT DEFAULT 'synced'"
            )

        # Get current column info for messages table
        cursor = conn.execute("PRAGMA table_info(messages)")
        msg_columns = {row["name"] for row in cursor.fetchall()}

        # Add sync_status to messages if missing
        if "sync_status" not in msg_columns:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN sync_status TEXT DEFAULT 'synced'"
            )

        # Add local_id to messages if missing
        if "local_id" not in msg_columns:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN local_id TEXT"
            )

        # Add response_time_ms to messages if missing
        if "response_time_ms" not in msg_columns:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN response_time_ms INTEGER"
            )

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn

    def close(self) -> None:
        """Close the current thread's connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # Conversations

    def save_conversation(self, conversation: Conversation) -> None:
        """Save or update a conversation."""
        data = conversation.model_dump(mode='json', by_alias=True)
        with self.connection as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO conversations (
                    id, title, user_id, assistant_id, project_id, model_id,
                    created_at, updated_at, message_count, pinned, generating,
                    cost_usd, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation.id,
                    conversation.title,
                    conversation.user_id,
                    conversation.assistant_id,
                    conversation.project_id,
                    conversation.model_id,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                    conversation.message_count,
                    conversation.pinned,
                    conversation.generating,
                    conversation.cost_usd,
                    json.dumps(data),
                ),
            )

    def save_conversations(self, conversations: List[Conversation]) -> None:
        """Save multiple conversations in a transaction."""
        with self.connection as conn:
            for conv in conversations:
                data = conv.model_dump(mode='json', by_alias=True)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO conversations (
                        id, title, user_id, assistant_id, project_id, model_id,
                        created_at, updated_at, message_count, pinned, generating,
                        cost_usd, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conv.id,
                        conv.title,
                        conv.user_id,
                        conv.assistant_id,
                        conv.project_id,
                        conv.model_id,
                        conv.created_at.isoformat(),
                        conv.updated_at.isoformat(),
                        conv.message_count,
                        conv.pinned,
                        conv.generating,
                        conv.cost_usd,
                        json.dumps(data),
                    ),
                )

    def get_conversations(self) -> List[Conversation]:
        """Get all conversations sorted by updated_at."""
        with self.connection as conn:
            cursor = conn.execute(
                "SELECT raw_data FROM conversations ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()
            return [Conversation.model_validate(json.loads(row["raw_data"])) for row in rows]

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a single conversation."""
        with self.connection as conn:
            cursor = conn.execute(
                "SELECT raw_data FROM conversations WHERE id = ?", (conversation_id,)
            )
            row = cursor.fetchone()
            if row:
                return Conversation.model_validate(json.loads(row["raw_data"]))
            return None

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation."""
        with self.connection as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    # Messages

    def save_message(self, message: Message) -> None:
        """Save or update a message."""
        data = message.model_dump(mode='json', by_alias=True)
        with self.connection as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages (
                    id, conversation_id, role, content, reasoning, model_id,
                    created_at, token_count, cost_usd, starred, response_time_ms, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role,
                    message.content,
                    message.reasoning,
                    message.model_id,
                    message.created_at.isoformat(),
                    message.token_count,
                    message.cost_usd,
                    message.starred,
                    message.response_time_ms,
                    json.dumps(data),
                ),
            )

    def save_messages(self, messages: List[Message]) -> None:
        """Save multiple messages in a transaction."""
        with self.connection as conn:
            for msg in messages:
                data = msg.model_dump(mode='json', by_alias=True)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO messages (
                        id, conversation_id, role, content, reasoning, model_id,
                        created_at, token_count, cost_usd, starred, response_time_ms, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg.id,
                        msg.conversation_id,
                        msg.role,
                        msg.content,
                        msg.reasoning,
                        msg.model_id,
                        msg.created_at.isoformat(),
                        msg.token_count,
                        msg.cost_usd,
                        msg.starred,
                        msg.response_time_ms,
                        json.dumps(data),
                    ),
                )

    def get_messages(self, conversation_id: str) -> List[Message]:
        """Get messages for a conversation sorted by created_at."""
        with self.connection as conn:
            cursor = conn.execute(
                """
                SELECT raw_data FROM messages 
                WHERE conversation_id = ? 
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            rows = cursor.fetchall()
            return [Message.model_validate(json.loads(row["raw_data"])) for row in rows]
