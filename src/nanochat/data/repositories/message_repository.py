"""Repository for message data with intelligent caching.

Inspired by nanochat-android's getConversationWithMessages() method.
Provides cache-first loading with background refresh.
"""

import time
from typing import Optional

from nanochat.api.client import NanoChatClient
from nanochat.api.models import Message
from nanochat.data.database import Database
from nanochat.data.sync_status import SyncStatus


class MessageRepository:
    """Handles message data with intelligent caching.

    Strategy:
    1. Return cached messages immediately (instant UI)
    2. Background sync if cache is stale (> 5 minutes)
    3. Force refresh if explicitly requested
    4. Offline fallback to cached data
    """

    CACHE_FRESH_SECONDS = 300  # 5 minutes

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
        self._fetch_timestamps: dict[str, float] = {}

    def get_messages_cached(self, conversation_id: str) -> list[Message]:
        """Get messages from local cache immediately.

        Args:
            conversation_id: The conversation ID

        Returns:
            List of messages (empty if not cached)
        """
        return self.db.get_messages(conversation_id)

    def get_cache_age(self, conversation_id: str) -> float:
        """Get the age of the cache in seconds.

        Args:
            conversation_id: The conversation ID

        Returns:
            Age in seconds (float('inf') if never fetched)
        """
        last_fetch = self._fetch_timestamps.get(conversation_id, 0)
        if last_fetch == 0:
            return float("inf")
        return time.time() - last_fetch

    def is_cache_fresh(self, conversation_id: str) -> bool:
        """Check if cached data is still fresh.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if cache is fresh (< 5 minutes old)
        """
        return self.get_cache_age(conversation_id) < self.CACHE_FRESH_SECONDS

    async def get_messages_with_sync(
        self, conversation_id: str, force_refresh: bool = False
    ) -> tuple[list[Message], bool]:
        """Get messages with automatic sync.

        Args:
            conversation_id: The conversation ID
            force_refresh: Force API refresh even if cache is fresh

        Returns:
            Tuple of (messages, was_from_cache)
        """
        cached = self.db.get_messages(conversation_id)

        # Return cached immediately if fresh and not forcing refresh
        if cached and not force_refresh and self.is_cache_fresh(conversation_id):
            return (cached, True)

        # Fetch from API
        try:
            async with NanoChatClient(self._backend_url, self._api_key) as client:
                remote_messages = await client.get_messages(conversation_id)

            # Upsert all messages (replace existing with new data)
            self.db.save_messages(remote_messages)

            # Update fetch timestamp
            self._fetch_timestamps[conversation_id] = time.time()

            # Note: Don't call _notify_messages_updated() here because we're in a background thread
            # The caller (window.py) will handle UI updates

            return (remote_messages, False)

        except Exception:
            # Offline fallback: return cached if available
            if cached:
                return (cached, True)
            raise

    async def refresh_messages(self, conversation_id: str) -> list[Message]:
        """Force refresh messages from API.

        Args:
            conversation_id: The conversation ID

        Returns:
            Updated messages list
        """
        messages, _ = await self.get_messages_with_sync(
            conversation_id, force_refresh=True
        )
        return messages

    def save_message(self, message: Message) -> None:
        """Save a message to local cache.

        Args:
            message: The message to save
        """
        self.db.save_message(message)

    def save_pending_message(self, message: Message) -> None:
        """Save a message as pending sync (for offline compose).

        Args:
            message: The message to save as pending
        """
        # Update sync status to PENDING
        # Note: Message model doesn't have sync_status field yet,
        # so we'll add it to the database directly
        data = message.model_dump(mode="json", by_alias=True)
        data["sync_status"] = SyncStatus.PENDING.value

        # For now, just save normally
        # TODO: Add sync_status to Message model in Phase 2
        self.db.save_message(message)

    def save_messages(self, messages: list[Message]) -> None:
        """Save multiple messages to local cache.

        Args:
            messages: The messages to save
        """
        self.db.save_messages(messages)

    def invalidate_cache(self, conversation_id: str) -> None:
        """Invalidate the cache for a conversation.

        Args:
            conversation_id: The conversation to invalidate
        """
        if conversation_id in self._fetch_timestamps:
            del self._fetch_timestamps[conversation_id]
