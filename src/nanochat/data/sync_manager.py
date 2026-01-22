"""Event bus for data synchronization events.

Inspired by nanochat-android's ConversationSyncManager with SharedFlow.
Provides a centralized event system for loose coupling between components.
"""

from enum import Enum
from collections.abc import Callable
from typing import Any

from gi.repository import GLib


class SyncEvent(Enum):
    """Types of synchronization events."""

    CONVERSATION_CREATED = "conversation_created"
    CONVERSATION_UPDATED = "conversation_updated"
    CONVERSATION_DELETED = "conversation_deleted"
    CONVERSATIONS_REFRESHED = "conversations_refreshed"
    MESSAGES_UPDATED = "messages_updated"


class SyncManager:
    """Central event bus for data synchronization.

    This is a singleton that manages event subscriptions and emissions.
    All events are dispatched on the main thread via GLib.idle_add()
    to ensure thread-safe UI updates.

    Usage:
        # Subscribe to events
        sync_manager = SyncManager()
        sync_manager.subscribe(SyncEvent.CONVERSATIONS_REFRESHED, callback)

        # Emit events from anywhere
        sync_manager.notify_conversations_refreshed()
    """

    _instance: "SyncManager | None" = None

    def __new__(cls) -> "SyncManager":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners: dict[SyncEvent, list[Callable[[dict[str, Any]], None]]] = {}
        return cls._instance

    def subscribe(self, event: SyncEvent, callback: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe to an event.

        Args:
            event: The event to listen for
            callback: Function to call when event is emitted (receives data dict)
        """
        if event not in self._listeners:
            self._listeners[event] = []
        if callback not in self._listeners[event]:
            self._listeners[event].append(callback)

    def unsubscribe(self, event: SyncEvent, callback: Callable[[dict[str, Any]], None]) -> None:
        """Unsubscribe from an event.

        Args:
            event: The event to stop listening for
            callback: The callback to remove
        """
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def emit(self, event: SyncEvent, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all subscribers on the main thread.

        Args:
            event: The event to emit
            data: Optional data to pass to subscribers
        """
        if event in self._listeners:
            for callback in self._listeners[event]:
                # Ensure callbacks run on the main thread
                GLib.idle_add(callback, data if data is not None else {})

    # Convenience methods for common events

    def notify_conversation_created(self, conversation_id: str) -> None:
        """Notify that a new conversation was created.

        Args:
            conversation_id: The new conversation's ID
        """
        self.emit(SyncEvent.CONVERSATION_CREATED, {"conversation_id": conversation_id})

    def notify_conversation_updated(self, conversation_id: str) -> None:
        """Notify that a conversation was updated.

        Args:
            conversation_id: The updated conversation's ID
        """
        self.emit(SyncEvent.CONVERSATION_UPDATED, {"conversation_id": conversation_id})

    def notify_conversation_deleted(self, conversation_id: str) -> None:
        """Notify that a conversation was deleted.

        Args:
            conversation_id: The deleted conversation's ID
        """
        self.emit(SyncEvent.CONVERSATION_DELETED, {"conversation_id": conversation_id})

    def notify_conversations_refreshed(self) -> None:
        """Notify that the conversation list was refreshed."""
        self.emit(SyncEvent.CONVERSATIONS_REFRESHED, {})

    def notify_messages_updated(self, conversation_id: str) -> None:
        """Notify that messages were updated for a conversation.

        Args:
            conversation_id: The conversation whose messages were updated
        """
        self.emit(SyncEvent.MESSAGES_UPDATED, {"conversation_id": conversation_id})


# Global instance for easy access
_sync_manager: SyncManager | None = None


def get_sync_manager() -> SyncManager:
    """Get the global SyncManager instance.

    Returns:
        The singleton SyncManager instance
    """
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager
