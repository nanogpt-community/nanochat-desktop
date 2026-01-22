"""Repository for conversation data with intelligent sync.

Inspired by nanochat-android's ConversationRepository.
Provides local-first data access with smart background sync.
"""

import time
from typing import Optional

from nanochat.api.client import NanoChatClient
from nanochat.api.models import Conversation
from nanochat.data.database import Database


class SyncResult:
    """Result of a sync operation."""

    def __init__(
        self,
        success: bool,
        data: Optional[list[Conversation]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.success = success
        self.data = data
        self.error = error

    @classmethod
    def success_result(cls, data: list[Conversation]) -> "SyncResult":
        return cls(success=True, data=data)

    @classmethod
    def failure_result(cls, error: Exception) -> "SyncResult":
        return cls(success=False, error=error)


class ConversationRepository:
    """Central point for all conversation data operations.

    Provides:
    - Instant local cache access
    - Background sync with intelligent merging
    - Timestamp-based conflict resolution
    - Automatic cleanup of orphaned local data
    """

    def __init__(self, database: Database, backend_url: str, api_key: str) -> None:
        """Initialize the repository.

        Args:
            database: Local SQLite database
            backend_url: NanoChat API base URL
            api_key: NanoChat API key
        """
        self.db = database
        self._backend_url = backend_url
        self._api_key = api_key
        self._last_sync_time: float = 0
        self._sync_in_progress: bool = False

    def get_conversations(self) -> list[Conversation]:
        """Get conversations from local cache (instant).

        Returns:
            List of conversations sorted by updated_at (newest first)
        """
        return self.db.get_conversations()

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a single conversation from local cache.

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation or None if not found
        """
        return self.db.get_conversation(conversation_id)

    async def fetch_and_sync_conversations(self) -> SyncResult:
        """Fetch from API and intelligently merge with local data.

        Merge strategy (from Android):
        - If local.updated_at < remote.updated_at: use remote (server wins)
        - If local.updated_at >= remote.updated_at: keep local (local wins)
        - Delete local conversations not on server (orphan cleanup)

        Returns:
            SyncResult with success status and updated conversations
        """
        if self._sync_in_progress:
            # Already syncing, return current data
            return SyncResult.success_result(self.get_conversations())

        self._sync_in_progress = True

        try:
            # Create client and fetch from API
            async with NanoChatClient(self._backend_url, self._api_key) as client:
                remote_conversations = await client.get_conversations()

            local_conversations = self.db.get_conversations()

            local_ids = {c.id for c in local_conversations}
            remote_ids = {c.id for c in remote_conversations}

            # Merge: update local if remote is newer
            updated_count = 0
            for remote_conv in remote_conversations:
                local_conv = self.db.get_conversation(remote_conv.id)

                # New conversation or remote is newer
                if local_conv is None or local_conv.updated_at < remote_conv.updated_at:
                    self.db.save_conversation(remote_conv)
                    updated_count += 1

            # Delete conversations that don't exist on server
            orphaned_ids = local_ids - remote_ids
            for conv_id in orphaned_ids:
                self.db.delete_conversation(conv_id)

            self._last_sync_time = time.time()

            # Note: Don't call _notify_sync_complete() here because we're in a background thread
            # The caller (window.py) will handle UI updates via the result

            return SyncResult.success_result(self.get_conversations())

        except Exception as e:
            return SyncResult.failure_result(e)

        finally:
            self._sync_in_progress = False

    def is_sync_needed(self, freshness_seconds: int = 60) -> bool:
        """Check if a sync is needed based on time since last sync.

        Args:
            freshness_seconds: How long until data is considered stale (default 60s)

        Returns:
            True if sync is needed, False otherwise
        """
        if self._last_sync_time == 0:
            return True  # Never synced

        cache_age = time.time() - self._last_sync_time
        return cache_age > freshness_seconds

    def save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation to local cache.

        Args:
            conversation: The conversation to save
        """
        self.db.save_conversation(conversation)

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation from local cache.

        Args:
            conversation_id: The conversation ID to delete
        """
        self.db.delete_conversation(conversation_id)
