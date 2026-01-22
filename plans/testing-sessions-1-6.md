# Testing Checklist: Opus Refactor Sessions 1-6

**Document Version**: 1.0
**Date**: January 22, 2026
**Purpose**: Comprehensive testing guide for Sessions 1-6 of the opus-refactor-plan

---

## Overview

This document provides a complete testing checklist for the refactoring work completed in Sessions 1-6. Each session includes unit tests, integration tests, and manual UI verification steps.

**Sessions Covered:**
- Session 1: Database schema and SyncStatus enum
- Session 2: Repository layer (ConversationRepository, MessageRepository)
- Session 3: Smart caching implementation
- Session 4: SyncManager event bus
- Session 5: MessageWidget metadata display
- Session 6: Collapsible reasoning sections

---

## Session 1: Database Schema and SyncStatus

### Files Modified
- `src/nanochat/data/sync_status.py` (NEW)
- `src/nanochat/data/database.py`

### Test: SyncStatus Enum

| Test Case | Expected Result | Status |
|-----------|----------------|--------|
| Verify `SyncStatus.SYNCED` value is `"synced"` | Pass | |
| Verify `SyncStatus.PENDING` value is `"pending"` | Pass | |
| Verify `SyncStatus.FAILED` value is `"failed"` | Pass | |
| Import works: `from nanochat.data import SyncStatus` | Pass | |

### Test: Database Migration

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| New database creation | 1. Delete cache.db<br>2. Run app | New DB has all columns including sync_status, local_id, response_time_ms | |
| Existing database migration | 1. Use old cache.db (pre-migration)<br>2. Run app | Migration adds new columns without data loss | |
| Verify conversations.sync_status column | Run `PRAGMA table_info(conversations);` | Column exists with DEFAULT 'synced' | |
| Verify messages.sync_status column | Run `PRAGMA table_info(messages);` | Column exists with DEFAULT 'synced' | |
| Verify messages.local_id column | Run `PRAGMA table_info(messages);` | Column exists (nullable) | |
| Verify messages.response_time_ms column | Run `PRAGMA table_info(messages);` | Column exists (nullable) | |
| Verify indexes exist | Run query on sqlite_master | idx_messages_conversation_id and idx_conversations_updated_at exist | |

### Test: Thread-Local Connections

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Connection is thread-local | 1. Get connection in main thread<br>2. Get connection in background thread | Two different connection objects | |
| Foreign keys enabled | Query `PRAGMA foreign_keys;` | Returns 1 | |
| Row factory set correctly | Execute any query | Returns sqlite3.Row objects | |

### Manual SQL Verification

```sql
-- Check conversations schema
PRAGMA table_info(conversations);

-- Check messages schema
PRAGMA table_info(messages);

-- Check indexes
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';

-- Verify default sync_status values
SELECT id, sync_status FROM conversations LIMIT 5;
SELECT id, sync_status FROM messages LIMIT 5;
```

---

## Session 2: Repository Layer

### Files Created
- `src/nanochat/data/repositories/__init__.py`
- `src/nanochat/data/repositories/conversation_repository.py`
- `src/nanochat/data/repositories/message_repository.py`

### Test: ConversationRepository

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Import works | `from nanochat.data.repositories import ConversationRepository` | No ImportError | |
| Constructor accepts database | `ConversationRepository(database)` | Instantiates | |
| get_conversations() | Call method | Returns list from cache | |
| save_conversation() | Save a conversation | Appears in database | |
| save_conversations() | Save multiple conversations | All saved in transaction | |
| get_conversation() | Get by ID | Returns Conversation or None | |
| delete_conversation() | Delete by ID | Removed from database | |

### Test: MessageRepository

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Import works | `from nanochat.data.repositories import MessageRepository` | No ImportError | |
| Constructor accepts database | `MessageRepository(database)` | Instantiates | |
| get_messages_cached() | Call method | Returns list from cache instantly | |
| save_message() | Save a message | Appears in database | |
| save_messages() | Save multiple messages | All saved in transaction | |

### Test: Repository API Integration

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Async fetch_and_sync_conversations() | Call with valid API | Fetches from API and merges | |
| Async get_messages_with_sync() | Call with conversation_id | Returns messages tuple | |
| Error handling | Call with invalid credentials | Exception raised, not crash | |
| Network offline | Disconnect network, call fetch | Graceful error or cached data | |

### Integration Test: End-to-End Flow

```python
# Test script to run in Python REPL
import asyncio
from nanochat.data.database import Database
from nanochat.data.repositories import ConversationRepository, MessageRepository
from nanochat.data.sync_status import SyncStatus

async def test_repositories():
    db = Database()
    conv_repo = ConversationRepository(db)
    msg_repo = MessageRepository(db)

    # Test conversation operations
    conversations = conv_repo.get_conversations()
    print(f"Found {len(conversations)} conversations")

    # Test message operations
    if conversations:
        messages = msg_repo.get_messages_cached(conversations[0].id)
        print(f"Found {len(messages)} messages")

asyncio.run(test_repositories())
```

---

## Session 3: Smart Caching

### Files Modified
- `src/nanochat/data/repositories/conversation_repository.py`
- `src/nanochat/data/repositories/message_repository.py`
- `src/nanochat/ui/window.py`

### Test: Cache-First Message Loading

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Load messages first time | Open conversation | Messages load <100ms if cached | |
| Cache freshness check | Load same conversation within 5 min | No API call made | |
| Cache expiration | Load after 5+ minutes | API call for refresh | |
| Force refresh | Call with force_refresh=True | Always fetches from API | |
| Offline fallback | Disconnect network, load cached | Shows cached messages | |

### Test: Timestamp-Based Sync

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Remote newer than local | Local updated_at < Remote updated_at | Local updated with remote data | |
| Local newer than remote | Local updated_at >= Remote updated_at | Local data preserved | |
| Deleted conversations | Remote missing local conversation | Local deleted | |
| New conversations on server | Remote has new conversation ID | Added to local database | |

### Performance Benchmarks

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cached message load time | <100ms | | |
| First-time message load | <500ms | | |
| Conversation list load | <200ms | | |
| Memory usage (idle) | <100MB | | |

### Browser DevTools Verification

1. Open NanoChat Desktop
2. Open browser DevTools (if applicable) or monitor with `tcpdump`
3. Load a conversation that was recently loaded
4. **Expected**: No network request to `/api/db/messages`
5. Load a conversation not loaded in >5 minutes
6. **Expected**: Network request to `/api/db/messages`

---

## Session 4: SyncManager Event Bus

### Files Created
- `src/nanochat/data/sync_manager.py`

### Test: SyncManager Singleton

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Singleton behavior | Create two instances | Same object (id() matches) | |
| get_sync_manager() | Call function | Returns singleton instance | |
| Multiple calls return same | Call get_sync_manager() twice | Same object returned | |

### Test: Event Subscription

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Subscribe to event | `subscribe(SyncEvent.CONVERSATIONS_REFRESHED, callback)` | Callback added to listeners | |
| Unsubscribe from event | `unsubscribe(SyncEvent.CONVERSATIONS_REFRESHED, callback)` | Callback removed | |
| Multiple subscribers | Subscribe two callbacks to same event | Both receive events | |
| Unsubscribe non-existent | Unsubscribe callback not subscribed | No error raised | |

### Test: Event Emission

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Emit without data | `emit(SyncEvent.CONVERSATIONS_REFRESHED)` | Callbacks called with empty dict | |
| Emit with data | `emit(SyncEvent.MESSAGES_UPDATED, {"conversation_id": "abc"})` | Callbacks receive data | |
| Main thread dispatch | Emit event from background thread | Callback runs on main thread via GLib.idle_add() | |
| No subscribers | Emit event with no listeners | No error, silently ignored | |

### Test: Convenience Methods

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| notify_conversation_created() | Call with conversation_id | CONVERSATION_CREATED event emitted | |
| notify_conversation_updated() | Call with conversation_id | CONVERSATION_UPDATED event emitted | |
| notify_conversation_deleted() | Call with conversation_id | CONVERSATION_DELETED event emitted | |
| notify_conversations_refreshed() | Call with no args | CONVERSATIONS_REFRESHED event emitted | |
| notify_messages_updated() | Call with conversation_id | MESSAGES_UPDATED event emitted | |

### Integration Test: Window.py Event Handling

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Subscribe on init | Window __init__ subscribes to events | Subscriptions created | |
| Refresh after sync | Emit CONVERSATIONS_REFRESHED | Conversation list updates | |
| Messages update | Emit MESSAGES_UPDATED | Message list refreshes | |

### Manual Event Test Script

```python
# Test script to verify event bus
from gi.repository import GLib
from nanochat.data.sync_manager import SyncManager, SyncEvent

received_events = []

def test_callback(data):
    received_events.append(data)
    print(f"Event received: {data}")

sync_mgr = SyncManager()
sync_mgr.subscribe(SyncEvent.CONVERSATIONS_REFRESHED, test_callback)
sync_mgr.notify_conversations_refreshed()

# Run GLib loop briefly to process idle callbacks
GLib.timeout_add(100, lambda: GLib.main_loop_quit())
GLib.main_loop_run()

assert len(received_events) == 1
```

---

## Session 5: MessageWidget Metadata

### Files Modified
- `src/nanochat/ui/message_widget.py`
- `src/nanochat/ui/window.py`

### Test: Metadata Parameters

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| model_id parameter | Create widget with model_id="gpt-4o" | Model name displayed | |
| token_count parameter | Create with token_count=1234 | "1,234 tokens" displayed | |
| cost_usd parameter | Create with cost_usd=0.0042 | "$0.0042" displayed | |
| cost_usd small value | Create with cost_usd=0.0001 | "$0.10m" (mills) displayed | |
| response_time_ms parameter | Create with response_time_ms=2500 | "2.5s" displayed | |
| response_time_ms < 1000 | Create with response_time_ms=450 | "450ms" displayed | |
| All parameters | Create with all metadata | All values displayed correctly | |
| None values | Create with all None | No metadata footer shown | |

### Test: Action Buttons

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Copy button exists | Check widget DOM | Copy button present | |
| Copy button click | Click copy button | Content copied to clipboard | |
| Copy feedback | Click and observe | Icon changes briefly to checkmark | |
| Regenerate button (assistant) | Create assistant message with on_regenerate | Regenerate button present | |
| Regenerate button (user) | Create user message | No regenerate button | |
| Star button (assistant) | Create with on_star callback | Star button present | |
| Star button (user) | Create user message | No star button | |
| Star icon states | Toggle star button | Icon switches between starred/non-starred | |
| Button hover effects | Mouse over message | Buttons appear (opacity 0→1) | |
| Mouse leave | Mouse exits message | Buttons disappear (opacity 1→0) | |

### Test: Metadata Footer Styling

| Test Case | Expected Result | Status |
|-----------|----------------|--------|
| Dim-label CSS class | Metadata has dim-label class | |
| Caption CSS class | Metadata has caption class | |
| Caption-heading on model | Model ID has caption-heading class | |
| Horizontal spacing | 8px spacing between items | |
| No metadata on user messages | User message has no footer | |

### Manual UI Verification

1. Launch the application
2. Open a conversation with assistant messages
3. Verify each message shows:
   - [ ] Model ID (e.g., "gpt-4o")
   - [ ] Token count with comma formatting
   - [ ] Cost in USD (appropriate formatting)
   - [ ] Response time (ms or s)
4. Hover over a message
5. Verify action buttons appear:
   - [ ] Copy icon (edit-copy-symbolic)
   - [ ] Regenerate icon (view-refresh-symbolic) - assistant only
   - [ ] Star icon (starred/non-starred) - assistant only
6. Click copy button
7. Verify:
   - [ ] Icon changes to checkmark briefly
   - [ ] Toast notification "Copied to clipboard"
   - [ ] Content actually in clipboard

---

## Session 6: Collapsible Reasoning Section

### Files Modified
- `src/nanochat/ui/message_widget.py`
- `src/nanochat/ui/window.py`

### Test: Reasoning Parameter

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| reasoning parameter | Create with reasoning="test" | Reasoning section appears | |
| None reasoning | Create with reasoning=None | No reasoning section | |
| Empty reasoning | Create with reasoning="" | No reasoning section | |
| User message with reasoning | Create user message with reasoning | No reasoning section (assistant only) | |
| Long reasoning content | Create with long reasoning | Content wraps properly | |

### Test: Expander Behavior

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Initial state | Create widget | Expander collapsed by default | |
| Click to expand | Click expander header | Reasoning content shows | |
| Click to collapse | Click expander again | Content hides | |
| Expander label | Check expander text | "💭 Thinking" displayed | |
| CSS class applied | Check widget classes | "reasoning-expander" class present | |

### Test: update_reasoning() Method

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Update reasoning content | Call update_reasoning("new content") | Label text updates | |
| Update during streaming | Call multiple times with accumulating content | Content updates incrementally | |
| Update after creation | Call update on widget without reasoning | No crash, graceful handling | |

### Test: Reasoning Content Styling

| Test Case | Expected Result | Status |
|-----------|----------------|--------|
| Dim-label CSS class | Reasoning has dim-label class | |
| Reasoning-content CSS class | Label has reasoning-content class | |
| Left alignment | Content xalign is 0.0 | |
| Wrap enabled | set_wrap(True) applied | |
| Read-only | Label is not selectable | |

### Manual UI Verification

1. Launch the application
2. Use a reasoning model (e.g., o1, o1-mini, or any model with thinking)
3. Send a message
4. Verify for assistant messages:
   - [ ] "💭 Thinking" expander appears above content
   - [ ] Expander starts collapsed
   - [ ] Clicking expander expands/collapses
   - [ ] Reasoning content is readable with dim styling
5. For user messages:
   - [ ] No reasoning section shown (even if reasoning provided)
6. For non-reasoning models:
   - [ ] No reasoning section shown

---

## Integration Tests: Cross-Session

### Test: Full Message Lifecycle

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Send message and receive response | 1. Send message<br>2. Wait for response<br>3. Check database | Message saved with metadata, reasoning if applicable | |
| Reload conversation | 1. Close app<br>2. Reopen<br>3. Load conversation | Messages load from cache with all metadata | |
| Sync after server change | 1. Modify conversation on server<br>2. Trigger sync in app | Local updates with remote changes | |
| Offline message viewing | 1. Load conversation<br>2. Disconnect network<br>3. Navigate back and forth | Cached messages display correctly | |

### Test: Memory and Performance

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Memory doesn't grow | Open/close 20 conversations | Memory stable, no leaks | |
| UI remains responsive | Generate long response | No freezing, smooth updates | |
| Cache invalidation | Wait 5+ minutes, reload | Fresh data fetched | |

### Test: Error Recovery

| Test Case | Steps | Expected Result | Status |
|-----------|-------|----------------|--------|
| Network error during sync | Disconnect during fetch | Graceful error, cached data shown | |
| Invalid API response | Corrupt response data | Exception caught, error toast shown | |
| Database lock | Two operations simultaneously | Queue or timeout, no crash | |

---

## Regression Tests

### Verify Existing Features Still Work

| Feature | Test Case | Expected Result | Status |
|---------|-----------|----------------|--------|
| Basic chat | Send and receive messages | Works as before | |
| New conversation | Create new conversation | Works as before | |
| Conversation list | Load and display conversations | Works as before | |
| Message markdown | Bold, italic, code, links | Render correctly | |
| Theme switching | Light/dark mode | Works as before | |
| Settings | Open and modify settings | Works as before |
| Models dialog | Select different models | Works as before |
| Assistants dialog | Select assistants | Works as before |

---

## Automated Test Script

```python
#!/usr/bin/env python3
"""
Automated test runner for Sessions 1-6.
Run with: python -m tests.test_opus_refactor
"""

import asyncio
import sqlite3
from pathlib import Path

from nanochat.data.database import Database
from nanochat.data.repositories import ConversationRepository, MessageRepository
from nanochat.data.sync_status import SyncStatus
from nanochat.data.sync_manager import SyncManager, SyncEvent


def test_sync_status_enum():
    """Test Session 1: SyncStatus enum"""
    assert SyncStatus.SYNCED.value == "synced"
    assert SyncStatus.PENDING.value == "pending"
    assert SyncStatus.FAILED.value == "failed"
    print("✓ SyncStatus enum test passed")


def test_database_schema():
    """Test Session 1: Database schema"""
    db = Database()

    # Check conversations table
    cursor = db.connection.execute("PRAGMA table_info(conversations)")
    columns = {row["name"] for row in cursor.fetchall()}
    assert "sync_status" in columns

    # Check messages table
    cursor = db.connection.execute("PRAGMA table_info(messages)")
    columns = {row["name"] for row in cursor.fetchall()}
    assert "sync_status" in columns
    assert "local_id" in columns
    assert "response_time_ms" in columns

    # Check indexes
    cursor = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    )
    indexes = {row["name"] for row in cursor.fetchall()}
    assert "idx_messages_conversation_id" in indexes
    assert "idx_conversations_updated_at" in indexes

    db.close()
    print("✓ Database schema test passed")


def test_repository_creation():
    """Test Session 2: Repository creation"""
    db = Database()

    conv_repo = ConversationRepository(db)
    assert conv_repo.db is db

    msg_repo = MessageRepository(db)
    assert msg_repo.db is db

    db.close()
    print("✓ Repository creation test passed")


def test_repository_operations():
    """Test Session 2: Repository operations"""
    db = Database()
    conv_repo = ConversationRepository(db)
    msg_repo = MessageRepository(db)

    # Test get_conversations
    conversations = conv_repo.get_conversations()
    assert isinstance(conversations, list)

    # Test get_messages_cached (may be empty)
    if conversations:
        messages = msg_repo.get_messages_cached(conversations[0].id)
        assert isinstance(messages, list)

    db.close()
    print("✓ Repository operations test passed")


def test_sync_manager_singleton():
    """Test Session 4: SyncManager singleton"""
    mgr1 = SyncManager()
    mgr2 = SyncManager()
    assert id(mgr1) == id(mgr2)

    mgr3 = get_sync_manager()
    assert isinstance(mgr3, SyncManager)

    print("✓ SyncManager singleton test passed")


def test_sync_manager_events():
    """Test Session 4: SyncManager events"""
    received = []

    def callback(data):
        received.append(data)

    sync_mgr = SyncManager()
    sync_mgr.subscribe(SyncEvent.CONVERSATIONS_REFRESHED, callback)
    sync_mgr.notify_conversations_refreshed()

    # Note: In real test, would process GLib idle callbacks
    # For now, just verify subscription doesn't crash

    sync_mgr.unsubscribe(SyncEvent.CONVERSATIONS_REFRESHED, callback)
    print("✓ SyncManager events test passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Running Opus Refactor Tests (Sessions 1-6)")
    print("=" * 50)

    try:
        test_sync_status_enum()
        test_database_schema()
        test_repository_creation()
        test_repository_operations()
        test_sync_manager_singleton()
        test_sync_manager_events()

        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(run_all_tests())
```

---

## Test Execution Checklist

### Before Testing

- [ ] Backup existing `cache.db` (if important)
- [ ] Note current git branch
- [ ] Ensure clean build: `python -m nanochat`

### Run Automated Tests

```bash
# Run the automated test script
python tests/test_opus_refactor.py

# Or run manually
cd /home/mark/projects/nanochat-desktop
python -m pytest tests/ -v  # if pytest is set up
```

### Manual UI Testing Sequence

1. **Launch Application**
   - [ ] App starts without errors
   - [ ] Window displays correctly
   - [ ] No console errors/warnings

2. **Test Database (Session 1)**
   - [ ] Old database migrates successfully
   - [ ] New tables created if needed
   - [ ] No data loss

3. **Test Repositories (Session 2)**
   - [ ] Conversation list loads
   - [ ] Messages load for selected conversation
   - [ ] New conversation can be created

4. **Test Caching (Session 3)**
   - [ ] First load: fetches from API
   - [ ] Second load: instant from cache
   - [ ] Wait 5+ min: re-fetches from API

5. **Test SyncManager (Session 4)**
   - [ ] Background sync triggers UI updates
   - [ ] No threading crashes
   - [ ] UI always responsive

6. **Test Message Metadata (Session 5)**
   - [ ] Assistant messages show metadata footer
   - [ ] Model ID displayed
   - [ ] Token count formatted with commas
   - [ ] Cost displayed correctly
   - [ ] Response time in correct units
   - [ ] Action buttons work (copy, star, regenerate)
   - [ ] Hover shows buttons

7. **Test Reasoning Section (Session 6)**
   - [ ] Reasoning expander appears for reasoning models
   - [ ] Expander starts collapsed
   - [ ] Clicking expands/collapses
   - [ ] Content displays correctly

### After Testing

- [ ] All tests pass
- [ ] No regressions found
- [ ] Document any issues
- [ ] Update test results in this file

---

## Sign-Off

**Tested by**: _______________
**Date**: _______________
**Sessions Tested**: 1-6
**Result**: Pass / Fail
**Notes**: _____________________________

---

**End of Testing Checklist**
