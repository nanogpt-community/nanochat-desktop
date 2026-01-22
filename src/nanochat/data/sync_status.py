"""Sync status tracking for offline-first functionality."""

from enum import Enum


class SyncStatus(Enum):
    """Represents the synchronization state of local data.

    - SYNCED: Data exists on server and is up to date
    - PENDING: Local change not yet synced to server
    - FAILED: Sync attempted but failed (should retry)
    """

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
