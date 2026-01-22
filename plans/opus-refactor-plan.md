# NanoChat Desktop Refactoring Plan
## Inspired by nanochat-android Architecture

**Document Version**: 1.0
**Date**: January 22, 2026
**Author**: AI Assistant (Claude Opus 4.5)

---

## LLM Implementation Instructions

> **This section provides step-by-step instructions for AI assistants (Claude, GPT, etc.) working on implementing this refactoring plan.**

### How to Use This Document

1. **Read the entire document first** to understand the scope and architecture
2. **Work in phases** - Start with Phase 1 (Data Layer) before moving to later phases
3. **Reference the existing codebase** alongside the Android examples provided
4. **Check related docs** - See [`CLAUDE.md`](../CLAUDE.md) for coding standards and [`plans/issue-12-local-db-caching.md`](issue-12-local-db-caching.md) for the caching issue this plan addresses

### Task Breakdown for LLM Sessions

Each session should focus on ONE of these discrete tasks:

#### Session 1: Add SyncStatus and Update Database Schema
- Create [`src/nanochat/data/sync_status.py`](../src/nanochat/data/sync_status.py) with SyncStatus enum
- Update [`src/nanochat/data/database.py`](../src/nanochat/data/database.py) to add new columns
- Add database migration logic for existing databases
- **Test**: Verify database schema updates work

#### Session 2: Create Repository Layer
- Create [`src/nanochat/data/repositories/__init__.py`](../src/nanochat/data/repositories/__init__.py)
- Create [`src/nanochat/data/repositories/conversation_repository.py`](../src/nanochat/data/repositories/conversation_repository.py)
- Create [`src/nanochat/data/repositories/message_repository.py`](../src/nanochat/data/repositories/message_repository.py)
- **Test**: Verify repositories work with existing database

#### Session 3: Implement Smart Caching in Repositories
- Add timestamp-based sync logic to ConversationRepository
- Add cache-fresh checking to MessageRepository
- Wire repositories into [`src/nanochat/ui/window.py`](../src/nanochat/ui/window.py)
- **Test**: Verify messages load from cache first

#### Session 4: Create SyncManager Event Bus
- Create [`src/nanochat/data/sync_manager.py`](../src/nanochat/data/sync_manager.py)
- Add event subscriptions in window.py
- Replace direct method calls with event emissions
- **Test**: Verify events propagate correctly

#### Session 5: Enhance MessageWidget with Metadata
- Update [`src/nanochat/ui/message_widget.py`](../src/nanochat/ui/message_widget.py) to accept metadata
- Add metadata footer display (tokens, cost, time)
- Add action buttons (copy, regenerate, star)
- Update [`src/nanochat/api/models.py`](../src/nanochat/api/models.py) if needed
- **Test**: Verify metadata displays correctly

#### Session 6: Add Collapsible Reasoning Section
- Add reasoning display to MessageWidget
- Implement expand/collapse with Gtk.Expander
- Style with CSS classes
- **Test**: Verify reasoning models show collapsible thinking

#### Session 7: Create Streaming Manager
- Create [`src/nanochat/api/streaming.py`](../src/nanochat/api/streaming.py)
- Add cancellation support
- Add timeout handling (5 minutes)
- Add UI update throttling
- **Test**: Verify streaming can be cancelled, handles timeout

#### Session 8: Add Starred Messages Feature
- Add toggle star API method to client.py
- Add star button to MessageWidget
- Save starred status to local database
- **Test**: Verify starring works

### Code Examples Reference

For each feature, this document provides:
1. **Inspiration**: Link to Android Kotlin source showing the pattern
2. **Proposed Python code**: Equivalent implementation for GTK4/Python
3. **Integration points**: Where the new code connects to existing code

### Key Files to Understand Before Starting

| File | Purpose | Line Count |
|------|---------|------------|
| [`src/nanochat/ui/window.py`](../src/nanochat/ui/window.py) | Main UI, needs refactoring | ~1769 |
| [`src/nanochat/data/database.py`](../src/nanochat/data/database.py) | SQLite caching | ~241 |
| [`src/nanochat/api/client.py`](../src/nanochat/api/client.py) | API client with SSE | ~328 |
| [`src/nanochat/api/models.py`](../src/nanochat/api/models.py) | Pydantic models | ~188 |
| [`src/nanochat/ui/message_widget.py`](../src/nanochat/ui/message_widget.py) | Message display | ~279 |

### Testing Each Change

After each modification:
1. Run `python -m nanochat` to start the app
2. Send a test message
3. Close and reopen the app
4. Verify the message loads from cache (no network traffic in developer tools)
5. Verify UI displays correctly

### Common Pitfalls to Avoid

1. **Don't block the main thread** - All database/network calls must be async or in threads
2. **Use GLib.idle_add()** - For any UI updates from background threads
3. **Handle errors gracefully** - Show toast notifications, don't crash
4. **Preserve backward compatibility** - Existing databases must migrate cleanly
5. **Follow GTK4 patterns** - Use Adw widgets where available

---

## Executive Summary

This document outlines a comprehensive refactoring plan for nanochat-desktop, inspired by the architecture patterns and features found in the [nanochat-android](https://github.com/jcrabapple/nanochat-android) repository. The focus is on improving **user experience**, **performance**, and **data caching** to create a faster, more responsive desktop application.

### Key Findings from Android Analysis

The Android app implements several sophisticated patterns that our desktop app can learn from:

1. **Repository Pattern with Clean Architecture** - Separate local/remote data sources
2. **Reactive Data Flow** - Kotlin Flow for real-time UI updates from database changes
3. **Smart Sync Strategy** - Timestamp-based intelligent merging, not full overwrites
4. **Event Bus for Updates** - ConversationSyncManager for cross-component communication
5. **Rich Message Display** - Detailed metadata (tokens, cost, response time), starred messages
6. **Proper SSE Streaming** - Cancellable streams with timeout handling

---

## Architecture Comparison

### Current Desktop Architecture

```
┌─────────────────────────────────────┐
│         UI Layer (GTK4)             │
│  - window.py (monolithic)           │
│  - message_widget.py                │
├─────────────────────────────────────┤
│         API Layer                   │
│  - client.py (direct API calls)     │
├─────────────────────────────────────┤
│         Data Layer                  │
│  - database.py (basic caching)      │
│  - settings.py                      │
└─────────────────────────────────────┘
```

**Issues**:
- `window.py` at 1769 lines is a monolith mixing UI, business logic, and data management
- No repository pattern - UI calls database directly
- No reactive data flow - manual UI updates
- Basic caching without smart sync strategy
- No sync status tracking

### Android Architecture (Target)

```
┌─────────────────────────────────────┐
│         UI Layer (Compose)          │
│  - ChatScreen.kt + ChatViewModel.kt │
│  - MessageBubble.kt (components)    │
├─────────────────────────────────────┤
│         Domain Layer                │
│  - Repository interfaces            │
│  - SyncManager for events           │
├─────────────────────────────────────┤
│         Data Layer                  │
│  - Local: Room DAOs + Entities      │
│  - Remote: NanoChatApi + DTOs       │
│  - SyncStatus tracking              │
└─────────────────────────────────────┘
```

**Advantages**:
- Clear separation of concerns
- Reactive UI updates via Flow/LiveData
- Smart sync with conflict resolution
- Cancellable operations
- Offline-first design

---

## Recommended Refactoring Areas

### Phase 1: Data Layer Improvements (Critical - Performance)

#### 1.1 Add SyncStatus Tracking to Database

**Inspiration**: Android's `SyncStatus` enum in entities

**Current State**: Desktop database has no sync tracking

**Proposed Changes**:

```python
# src/nanochat/data/sync_status.py (NEW)
from enum import Enum

class SyncStatus(Enum):
    SYNCED = "synced"      # Server has this data
    PENDING = "pending"    # Local change not yet synced
    FAILED = "failed"      # Sync attempted but failed
```

```python
# Update database schema
"""
ALTER TABLE messages ADD COLUMN sync_status TEXT DEFAULT 'synced';
ALTER TABLE conversations ADD COLUMN sync_status TEXT DEFAULT 'synced';
ALTER TABLE messages ADD COLUMN local_id TEXT;  -- Preserve UI identity during sync
ALTER TABLE messages ADD COLUMN response_time_ms INTEGER;  -- Performance metrics
"""
```

**Benefits**:
- Know which messages need syncing
- Support offline compose and queue
- Track sync failures for retry

#### 1.2 Implement Repository Pattern

**Inspiration**: Android's `ConversationRepository`, `MessageRepository`

**Proposed New Files**:

```
src/nanochat/data/
├── repositories/
│   ├── __init__.py
│   ├── conversation_repository.py
│   └── message_repository.py
```

```python
# src/nanochat/data/repositories/conversation_repository.py
class ConversationRepository:
    """Central point for all conversation data operations."""
    
    def __init__(self, database: Database, api_client: NanoChatClient):
        self.db = database
        self.api = api_client
        self._sync_listeners: list[Callable] = []
    
    def get_conversations(self) -> list[Conversation]:
        """Get conversations from local cache (instant)."""
        return self.db.get_conversations()
    
    async def fetch_and_sync_conversations(self) -> Result[list[Conversation]]:
        """
        Fetch from API and intelligently merge with local data.
        Uses timestamp-based merging like Android:
        - If local.updated_at < remote.updated_at: use remote
        - If local.updated_at >= remote.updated_at: keep local
        - Delete local conversations not on server
        """
        try:
            remote_conversations = await self.api.get_conversations()
            local_conversations = self.db.get_conversations()
            
            local_ids = {c.id for c in local_conversations}
            remote_ids = {c.id for c in remote_conversations}
            
            # Merge strategy
            for remote_conv in remote_conversations:
                local_conv = self.db.get_conversation(remote_conv.id)
                if local_conv is None or local_conv.updated_at < remote_conv.updated_at:
                    self.db.save_conversation(remote_conv)
            
            # Delete conversations that don't exist on server
            orphaned_ids = local_ids - remote_ids
            for conv_id in orphaned_ids:
                self.db.delete_conversation(conv_id)
            
            self._notify_sync_complete()
            return Result.success(self.db.get_conversations())
        except Exception as e:
            return Result.failure(e)
    
    def add_sync_listener(self, callback: Callable) -> None:
        self._sync_listeners.append(callback)
    
    def _notify_sync_complete(self) -> None:
        for listener in self._sync_listeners:
            GLib.idle_add(listener)
```

**Benefits**:
- Single source of truth for data operations
- Encapsulates sync logic away from UI
- Enables offline-first behavior
- Testable in isolation

#### 1.3 Implement Smart Message Caching

**Inspiration**: Android's `getConversationWithMessages()` method

**Current Issue**: Desktop fetches messages from API every time, 300ms+ delay

**Proposed Solution**:

```python
# src/nanochat/data/repositories/message_repository.py
class MessageRepository:
    """Handles message data with intelligent caching."""
    
    CACHE_FRESH_SECONDS = 300  # 5 minutes
    
    def __init__(self, database: Database, api_client: NanoChatClient):
        self.db = database
        self.api = api_client
        self._fetch_timestamps: dict[str, float] = {}
    
    def get_messages_cached(self, conversation_id: str) -> list[Message]:
        """Get messages from local cache immediately."""
        return self.db.get_messages(conversation_id)
    
    async def get_messages_with_sync(
        self, 
        conversation_id: str,
        force_refresh: bool = False
    ) -> tuple[list[Message], bool]:
        """
        Returns (messages, was_from_cache).
        
        Strategy:
        1. Return cached messages immediately if available
        2. Background sync if cache is stale (> 5 min)
        3. Force refresh if explicitly requested
        """
        cached = self.db.get_messages(conversation_id)
        last_fetch = self._fetch_timestamps.get(conversation_id, 0)
        cache_age = time.time() - last_fetch
        
        if cached and cache_age < self.CACHE_FRESH_SECONDS and not force_refresh:
            return (cached, True)
        
        # Fetch from API
        try:
            remote_messages = await self.api.get_messages(conversation_id)
            
            # Upsert strategy (like Android)
            self.db.save_messages(remote_messages)
            
            # Update fetch timestamp
            self._fetch_timestamps[conversation_id] = time.time()
            
            return (remote_messages, False)
        except Exception as e:
            # Offline fallback
            if cached:
                return (cached, True)
            raise e
    
    async def save_pending_message(self, message: Message) -> None:
        """Save a message as pending sync."""
        message_with_status = message.model_copy(
            update={"sync_status": SyncStatus.PENDING}
        )
        self.db.save_message(message_with_status)
```

#### 1.4 Add Event Bus for Sync Updates

**Inspiration**: Android's `ConversationSyncManager` with SharedFlow

**Proposed Implementation**:

```python
# src/nanochat/data/sync_manager.py (NEW)
from enum import Enum
from typing import Callable
from gi.repository import GLib

class SyncEvent(Enum):
    CONVERSATION_CREATED = "conversation_created"
    CONVERSATION_UPDATED = "conversation_updated"
    CONVERSATION_DELETED = "conversation_deleted"
    CONVERSATIONS_REFRESHED = "conversations_refreshed"
    MESSAGES_UPDATED = "messages_updated"

class SyncManager:
    """
    Central event bus for data synchronization.
    Enables loose coupling between components.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = {}
        return cls._instance
    
    def subscribe(self, event: SyncEvent, callback: Callable) -> None:
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def unsubscribe(self, event: SyncEvent, callback: Callable) -> None:
        if event in self._listeners:
            self._listeners[event].remove(callback)
    
    def emit(self, event: SyncEvent, data: dict = None) -> None:
        """Emit event on the main thread."""
        if event in self._listeners:
            for callback in self._listeners[event]:
                GLib.idle_add(callback, data)
    
    def notify_conversation_created(self, conversation_id: str) -> None:
        self.emit(SyncEvent.CONVERSATION_CREATED, {"conversation_id": conversation_id})
    
    def notify_messages_updated(self, conversation_id: str) -> None:
        self.emit(SyncEvent.MESSAGES_UPDATED, {"conversation_id": conversation_id})
```

**Usage in window.py**:

```python
# Subscribe to sync events
self.sync_manager = SyncManager()
self.sync_manager.subscribe(
    SyncEvent.CONVERSATIONS_REFRESHED,
    self._on_conversations_refreshed
)

def _on_conversations_refreshed(self, data: dict) -> None:
    """React to background sync completion."""
    self._update_conversation_list(self.conversation_repo.get_conversations())
```

---

### Phase 2: Message Display Improvements (High Priority - UX)

#### 2.1 Enhanced MessageWidget with Metadata

**Inspiration**: Android's `MessageBubble.kt` with token/cost/time display

**Current State**: Desktop MessageWidget shows only role and content

**Proposed Enhancements**:

```python
# src/nanochat/ui/message_widget.py - Enhanced version

class MessageWidget(Adw.Bin):
    """Enhanced message widget with metadata display."""
    
    def __init__(
        self,
        role: str,
        content: str,
        model_id: str | None = None,
        token_count: int | None = None,
        cost_usd: float | None = None,
        response_time_ms: int | None = None,
        starred: bool = False,
        reasoning: str | None = None,
        on_copy: Callable | None = None,
        on_regenerate: Callable | None = None,
        on_star: Callable | None = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._build_enhanced_ui()
    
    def _build_enhanced_ui(self) -> None:
        # ... existing content display ...
        
        # Add collapsible reasoning section (like Android's "Thinking" block)
        if self.reasoning:
            self._add_reasoning_section()
        
        # Add metadata footer for assistant messages
        if self.role == "assistant":
            self._add_metadata_footer()
        
        # Add action buttons (copy, regenerate, star)
        self._add_action_buttons()
    
    def _add_reasoning_section(self) -> None:
        """Collapsible section for model reasoning/thinking."""
        expander = Gtk.Expander()
        expander.set_label("💭 Thinking")
        expander.add_css_class("reasoning-expander")
        
        reasoning_label = Gtk.Label(label=self.reasoning)
        reasoning_label.set_wrap(True)
        reasoning_label.add_css_class("dim-label")
        reasoning_label.add_css_class("reasoning-content")
        
        expander.set_child(reasoning_label)
        self.content_box.prepend(expander)  # Before main content
    
    def _add_metadata_footer(self) -> None:
        """Add model, tokens, cost, response time display."""
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        metadata_box.add_css_class("message-metadata")
        
        # Model ID
        if self.model_id:
            model_label = Gtk.Label(label=self.model_id)
            model_label.add_css_class("dim-label")
            model_label.add_css_class("caption")
            metadata_box.append(model_label)
        
        # Token count
        if self.token_count:
            tokens_label = Gtk.Label(label=f"{self.token_count} tokens")
            tokens_label.add_css_class("dim-label")
            tokens_label.add_css_class("caption")
            metadata_box.append(tokens_label)
        
        # Cost
        if self.cost_usd:
            cost_str = f"${self.cost_usd:.4f}" if self.cost_usd < 0.01 else f"${self.cost_usd:.2f}"
            cost_label = Gtk.Label(label=cost_str)
            cost_label.add_css_class("dim-label")
            cost_label.add_css_class("caption")
            metadata_box.append(cost_label)
        
        # Response time
        if self.response_time_ms:
            time_seconds = self.response_time_ms / 1000.0
            time_label = Gtk.Label(label=f"{time_seconds:.1f}s")
            time_label.add_css_class("dim-label")
            time_label.add_css_class("caption")
            metadata_box.append(time_label)
        
        self.content_box.append(metadata_box)
    
    def _add_action_buttons(self) -> None:
        """Add copy, regenerate, and star buttons."""
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        actions_box.set_halign(Gtk.Align.END)
        actions_box.add_css_class("message-actions")
        
        # Regenerate button (assistant only)
        if self.role == "assistant" and self.on_regenerate:
            regen_btn = Gtk.Button(icon_name="view-refresh-symbolic")
            regen_btn.add_css_class("flat")
            regen_btn.add_css_class("circular")
            regen_btn.set_tooltip_text("Regenerate response")
            regen_btn.connect("clicked", lambda _: self.on_regenerate())
            actions_box.append(regen_btn)
        
        # Star button (assistant only)
        if self.role == "assistant" and self.on_star:
            star_icon = "starred-symbolic" if self.starred else "non-starred-symbolic"
            star_btn = Gtk.Button(icon_name=star_icon)
            star_btn.add_css_class("flat")
            star_btn.add_css_class("circular")
            star_btn.set_tooltip_text("Star message")
            star_btn.connect("clicked", lambda _: self.on_star(not self.starred))
            actions_box.append(star_btn)
        
        # Copy button (always)
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.add_css_class("circular")
        copy_btn.set_tooltip_text("Copy message")
        copy_btn.connect("clicked", self._on_copy_clicked)
        actions_box.append(copy_btn)
        
        self.content_box.append(actions_box)
```

#### 2.2 Improved Markdown Rendering

**Inspiration**: Android's `SimpleMarkdownText.kt` (38KB comprehensive implementation)

**Current State**: Desktop has basic markdown (bold, italic, code, links)

**Missing Features**:
- Tables
- Horizontal rules
- Nested lists
- Syntax highlighting for code blocks
- LaTeX math rendering
- Mermaid diagrams

**Proposed**: Integrate a proper markdown library

```python
# Option 1: Use markdown-it-py for parsing
pip install markdown-it-py

# Option 2: Use GtkSourceView for code blocks with syntax highlighting
from gi.repository import GtkSource

def _render_code_block(self, language: str, code: str) -> GtkSource.View:
    """Render code block with syntax highlighting."""
    buffer = GtkSource.Buffer()
    
    # Set language for highlighting
    lang_manager = GtkSource.LanguageManager.get_default()
    language_obj = lang_manager.get_language(language)
    if language_obj:
        buffer.set_language(language_obj)
    
    buffer.set_text(code)
    
    view = GtkSource.View(buffer=buffer)
    view.set_editable(False)
    view.set_show_line_numbers(True)
    view.add_css_class("code-block")
    
    return view
```

#### 2.3 Follow-Up Questions Display

**Inspiration**: Android's `FollowUpQuestions.kt`

**Feature**: Display clickable follow-up question suggestions after assistant response

```python
class FollowUpQuestionsWidget(Gtk.FlowBox):
    """Display follow-up question suggestions as clickable chips."""
    
    def __init__(
        self,
        questions: list[str],
        on_question_clicked: Callable[[str], None]
    ):
        super().__init__()
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_max_children_per_line(3)
        self.add_css_class("follow-up-questions")
        
        for question in questions:
            chip = self._create_question_chip(question, on_question_clicked)
            self.append(chip)
    
    def _create_question_chip(
        self,
        question: str,
        callback: Callable
    ) -> Gtk.Button:
        btn = Gtk.Button(label=question)
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.connect("clicked", lambda _: callback(question))
        return btn
```

---

### Phase 3: Streaming and Performance Improvements

#### 3.1 Cancellable Streaming with Timeout

**Inspiration**: Android's `StreamingManager.kt`

**Current Issues**:
- No stream timeout handling
- No way to cancel mid-generation
- No rate limiting of UI updates

**Proposed Improvements**:

```python
# src/nanochat/api/streaming.py (NEW)
import asyncio
from typing import Callable, Optional

class StreamingManager:
    """
    Manages SSE streaming with cancellation and timeout support.
    Inspired by Android's StreamingManager.kt
    """
    
    STREAM_TIMEOUT_SECONDS = 300  # 5 minutes
    UI_UPDATE_THROTTLE_MS = 50    # Don't update UI more than 20x/second
    
    def __init__(self, api_client: NanoChatClient):
        self.client = api_client
        self._current_task: Optional[asyncio.Task] = None
        self._cancelled = False
        self._last_ui_update = 0
    
    async def stream_message(
        self,
        request: GenerateMessageRequest,
        on_content_delta: Callable[[str], None],
        on_reasoning_delta: Callable[[str], None],
        on_message_start: Callable[[str, str], None],  # conv_id, msg_id
        on_complete: Callable[[dict], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Stream a message with proper event handling.
        
        Events emitted:
        - message_start: {conversation_id, message_id}
        - delta: {content?, reasoning?}
        - message_complete: {token_count, cost_usd, response_time_ms}
        - error: {error}
        """
        self._cancelled = False
        accumulated_content = ""
        accumulated_reasoning = ""
        
        def handle_event(event_type: str, data: dict) -> None:
            nonlocal accumulated_content, accumulated_reasoning
            
            if self._cancelled:
                return
            
            if event_type == "message_start":
                on_message_start(
                    data.get("conversation_id"),
                    data.get("message_id")
                )
            
            elif event_type == "delta":
                content = data.get("content", "")
                reasoning = data.get("reasoning", "")
                
                if content:
                    accumulated_content += content
                    # Throttle UI updates
                    if self._should_update_ui():
                        GLib.idle_add(on_content_delta, accumulated_content)
                
                if reasoning:
                    accumulated_reasoning += reasoning
                    if self._should_update_ui():
                        GLib.idle_add(on_reasoning_delta, accumulated_reasoning)
            
            elif event_type == "message_complete":
                # Final UI update with complete content
                GLib.idle_add(on_content_delta, accumulated_content)
                GLib.idle_add(on_complete, data)
            
            elif event_type == "error":
                GLib.idle_add(on_error, data.get("error", "Unknown error"))
        
        try:
            # Wrap in timeout
            await asyncio.wait_for(
                self.client.stream_generate_message(request, handle_event),
                timeout=self.STREAM_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            on_error("Stream timeout after 5 minutes")
        except asyncio.CancelledError:
            on_error("Generation cancelled")
        except Exception as e:
            on_error(str(e))
    
    def _should_update_ui(self) -> bool:
        """Throttle UI updates to prevent lag."""
        now = time.time() * 1000
        if now - self._last_ui_update > self.UI_UPDATE_THROTTLE_MS:
            self._last_ui_update = now
            return True
        return False
    
    def cancel(self) -> None:
        """Cancel the current streaming operation."""
        self._cancelled = True
        if self._current_task:
            self._current_task.cancel()
```

#### 3.2 Optimistic UI Updates

**Inspiration**: Android immediately shows user message before server confirms

**Current**: Desktop waits until stream starts before showing user message

**Improvement**: Show user message immediately with "sending" indicator

```python
def _on_send(self, widget: Gtk.Widget) -> None:
    text = self.message_entry.get_text().strip()
    if not text:
        return
    
    # 1. Optimistically add user message to UI immediately
    temp_id = f"temp_{uuid.uuid4()}"
    user_widget = MessageWidget(
        role="user",
        content=text,
        pending=True  # Shows subtle "sending" indicator
    )
    user_widget.set_name(temp_id)
    self.messages_list.append(user_widget)
    
    # 2. Save to local DB as pending
    pending_message = Message(
        id=temp_id,
        conversation_id=self._current_conversation_id,
        role="user",
        content=text,
        created_at=datetime.utcnow(),
        sync_status=SyncStatus.PENDING
    )
    self.message_repo.save_pending_message(pending_message)
    
    # 3. Clear input immediately
    self.message_entry.set_text("")
    
    # 4. Start streaming in background
    asyncio.create_task(self._stream_response(text, temp_id))
```

---

### Phase 4: UI/UX Refinements

#### 4.1 Pinned Conversations

**Inspiration**: Android's `pinned` column and `getPinnedConversations()`

**Feature**: Allow users to pin important conversations to top of list

```python
# Database change
ALTER TABLE conversations ADD COLUMN pinned BOOLEAN DEFAULT 0;

# Repository method
def get_pinned_conversations(self) -> list[Conversation]:
    """Get pinned conversations sorted by updated_at."""
    return self.db.execute(
        "SELECT * FROM conversations WHERE pinned = 1 ORDER BY updated_at DESC"
    )

# UI: Add pin toggle in conversation context menu
def _on_toggle_pin(self, conversation_id: str) -> None:
    conv = self.conversation_repo.get_by_id(conversation_id)
    conv.pinned = not conv.pinned
    self.conversation_repo.save(conv)
    self._update_conversation_list()
```

#### 4.2 Starred Messages

**Inspiration**: Android's message starring with dedicated view

**Feature**: Star important messages for quick reference

```python
# API endpoint (already supports this)
POST /api/db/messages
{
    "action": "setStarred",
    "messageId": "...",
    "starred": true
}

GET /api/db/messages?starred=true
```

```python
# Add to message widget
def _on_star_toggled(self, starred: bool) -> None:
    asyncio.create_task(
        self.message_repo.toggle_star(self.message_id, starred)
    )
    self._update_star_icon(starred)
```

#### 4.3 Web Search Result Cards

**Inspiration**: Android's `WebSearchResultCard.kt`

**Feature**: Display web search results in a collapsible card with source links

```python
class WebSearchResultCard(Gtk.Box):
    """Display web search results with sources."""
    
    def __init__(self, search_data: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("web-search-card")
        
        # Header with search icon
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("edit-find-symbolic")
        title = Gtk.Label(label="Web Search Results")
        title.add_css_class("heading")
        header.append(icon)
        header.append(title)
        self.append(header)
        
        # Sources list
        sources = search_data.get("sources", [])
        for source in sources:
            source_row = self._create_source_row(source)
            self.append(source_row)
    
    def _create_source_row(self, source: dict) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Favicon (if available)
        # Title as link
        link = Gtk.LinkButton.new_with_label(
            source.get("url", ""),
            source.get("title", "Source")
        )
        link.add_css_class("caption")
        row.append(link)
        
        return row
```

---

### Phase 5: Architecture Cleanup

#### 5.1 Split window.py into Components

**Problem**: `window.py` is 1769 lines mixing concerns

**Proposed Structure**:

```
src/nanochat/ui/
├── window.py                    # Main window, reduced to ~300 lines
├── components/
│   ├── __init__.py
│   ├── sidebar.py               # Conversation list sidebar
│   ├── chat_area.py             # Main chat area
│   ├── input_bar.py             # Message input with attachments
│   ├── message_list.py          # Scrollable message container
│   └── model_selector.py        # Model/assistant dropdowns
├── dialogs/
│   ├── __init__.py
│   ├── assistants_dialog.py     # (existing)
│   ├── models_dialog.py         # (existing)
│   └── settings_dialog.py       # New unified settings
└── widgets/
    ├── __init__.py
    ├── message_widget.py        # (existing, enhanced)
    ├── attachment_preview.py    # (existing)
    └── follow_up_questions.py   # (new)
```

#### 5.2 Create ViewModel Layer

**Inspiration**: Android's MVVM with ViewModel

**Purpose**: Separate UI state management from widgets

```python
# src/nanochat/ui/viewmodels/chat_viewmodel.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class ChatUiState:
    """Immutable state container for chat UI."""
    is_loading: bool = False
    is_sending: bool = False
    error_message: str | None = None
    current_conversation_id: str | None = None
    messages: list[Message] = field(default_factory=list)
    web_search_enabled: bool = False
    web_search_mode: str = "standard"

class ChatViewModel:
    """Manages UI state for the chat screen."""
    
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        streaming_manager: StreamingManager
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.streaming = streaming_manager
        
        self._state = ChatUiState()
        self._state_listeners: list[Callable[[ChatUiState], None]] = []
    
    def add_state_listener(self, callback: Callable[[ChatUiState], None]) -> None:
        self._state_listeners.append(callback)
    
    def _emit_state(self) -> None:
        for listener in self._state_listeners:
            GLib.idle_add(listener, self._state)
    
    async def load_conversation(self, conversation_id: str) -> None:
        self._state = self._state.copy(
            is_loading=True,
            current_conversation_id=conversation_id
        )
        self._emit_state()
        
        messages, from_cache = await self.message_repo.get_messages_with_sync(conversation_id)
        
        self._state = self._state.copy(
            is_loading=False,
            messages=messages
        )
        self._emit_state()
    
    async def send_message(self, content: str) -> None:
        self._state = self._state.copy(is_sending=True)
        self._emit_state()
        
        # ... send logic ...
        
        self._state = self._state.copy(is_sending=False)
        self._emit_state()
```

---

## Implementation Priority

### Immediate (Fix Issue #12)

| Task | Impact | Effort |
|------|--------|--------|
| Save messages to DB during streaming | High | Low |
| Update fetch timestamps properly | High | Low |
| Implement cache-first loading | High | Medium |

### Short-term (Performance)

| Task | Impact | Effort |
|------|--------|--------|
| Repository pattern for data access | High | Medium |
| SyncStatus tracking | Medium | Low |
| Streaming cancellation | Medium | Low |
| UI update throttling | Medium | Low |

### Medium-term (UX)

| Task | Impact | Effort |
|------|--------|--------|
| Enhanced MessageWidget with metadata | High | Medium |
| Follow-up questions | Medium | Low |
| Pinned conversations | Medium | Low |
| Starred messages | Medium | Medium |
| Collapsible reasoning blocks | Medium | Low |

### Long-term (Architecture)

| Task | Impact | Effort |
|------|--------|--------|
| Split window.py into components | High | High |
| ViewModel layer | Medium | High |
| SyncManager event bus | Medium | Medium |
| Improved markdown rendering | Medium | High |

---

## Risk Assessment

### Low Risk
- Adding metadata display to MessageWidget
- Implementing follow-up questions
- Adding pinned conversations
- Starring messages

### Medium Risk
- Repository pattern (requires refactoring data access)
- SyncManager (requires coordinating multiple components)
- Splitting window.py (touching core UI code)

### High Risk
- ViewModel layer (significant architecture change)
- Replacing markdown renderer (may break existing content)

---

## Success Metrics

After implementation, we should measure:

1. **Load Time**: Conversation messages should appear in <100ms from cache
2. **First Paint**: User message should appear instantly on send
3. **Sync Reliability**: No duplicate messages, no lost data
4. **Offline Capability**: App should be usable without network for cached data
5. **Memory Usage**: No memory leaks from streaming operations
6. **UI Responsiveness**: No lag during message streaming

---

## Appendix: File Mapping

| Android File | Desktop Equivalent | Notes |
|-------------|-------------------|-------|
| `NanoChatDatabase.kt` | `database.py` | Add migrations, sync status |
| `ConversationDao.kt` | `database.py` | Add similar query methods |
| `MessageDao.kt` | `database.py` | Add similar query methods |
| `ConversationEntity.kt` | `models.py` (Conversation) | Add sync_status |
| `MessageEntity.kt` | `models.py` (Message) | Add response_time_ms, local_id |
| `ConversationRepository.kt` | NEW: `repositories/conversation_repository.py` | Smart sync logic |
| `MessageRepository.kt` | NEW: `repositories/message_repository.py` | Cache management |
| `ConversationSyncManager.kt` | NEW: `sync_manager.py` | Event bus |
| `StreamingManager.kt` | NEW: `streaming.py` | Cancellation, timeout |
| `ChatViewModel.kt` | NEW: `viewmodels/chat_viewmodel.py` | State management |
| `MessageBubble.kt` | `message_widget.py` | Enhance with metadata |
| `SimpleMarkdownText.kt` | `message_widget.py._render_markdown()` | Improve rendering |
| `FollowUpQuestions.kt` | NEW: `widgets/follow_up_questions.py` | New feature |
| `WebSearchResultCard.kt` | NEW: `widgets/web_search_card.py` | New feature |

---

## Conclusion

The nanochat-android codebase demonstrates a mature, well-architected approach to building a responsive chat application. By adopting key patterns like the repository pattern, smart sync strategy, and reactive UI updates, the desktop application can achieve similar levels of performance and user experience.

The recommended approach is:
1. **Start with data layer fixes** to resolve Issue #12 (immediate)
2. **Add repository pattern** to encapsulate data operations (short-term)
3. **Enhance UI components** with metadata and features (medium-term)
4. **Refactor architecture** for long-term maintainability (long-term)

This incremental approach allows shipping improvements quickly while building toward a more robust architecture.

---

## Implementation Checklist for LLMs

> **Copy this checklist to track progress. Mark items with [x] when complete.**

### Phase 1: Data Layer Improvements (CRITICAL)

- [ ] **1.1 SyncStatus Enum**
  - [ ] Create `src/nanochat/data/sync_status.py`
  - [ ] Define `SyncStatus` enum with SYNCED, PENDING, FAILED values

- [ ] **1.2 Database Schema Updates**
  - [ ] Add `sync_status` column to messages table
  - [ ] Add `sync_status` column to conversations table
  - [ ] Add `local_id` column to messages table
  - [ ] Add `response_time_ms` column to messages table
  - [ ] Create migration function for existing databases
  - [ ] Test migration on existing database

- [ ] **1.3 Repository Pattern**
  - [ ] Create `src/nanochat/data/repositories/` directory
  - [ ] Create `conversation_repository.py` with:
    - [ ] `get_conversations()` - returns from cache
    - [ ] `fetch_and_sync_conversations()` - smart merge with API
    - [ ] `save_conversation()`
    - [ ] `delete_conversation()`
  - [ ] Create `message_repository.py` with:
    - [ ] `get_messages_cached()` - instant from DB
    - [ ] `get_messages_with_sync()` - cache-first with background sync
    - [ ] `save_pending_message()` - for optimistic UI
    - [ ] `CACHE_FRESH_SECONDS` constant (300s = 5 min)
  - [ ] Update `window.py` to use repositories instead of direct DB calls

- [ ] **1.4 SyncManager Event Bus**
  - [ ] Create `src/nanochat/data/sync_manager.py`
  - [ ] Define `SyncEvent` enum
  - [ ] Implement singleton `SyncManager` class
  - [ ] Add subscribe/unsubscribe/emit methods
  - [ ] Integrate into `window.py` for conversation list updates

### Phase 2: Message Display Improvements (HIGH)

- [ ] **2.1 Enhanced MessageWidget**
  - [ ] Accept additional parameters: `model_id`, `token_count`, `cost_usd`, `response_time_ms`, `starred`, `reasoning`
  - [ ] Add metadata footer section
  - [ ] Display model name
  - [ ] Display token count
  - [ ] Display cost (format: $0.0012 or $0.01)
  - [ ] Display response time (format: 2.3s)

- [ ] **2.2 Action Buttons**
  - [ ] Add regenerate button (assistant messages only)
  - [ ] Add star toggle button (assistant messages only)
  - [ ] Add copy button (all messages)
  - [ ] Wire up callbacks

- [ ] **2.3 Collapsible Reasoning**
  - [ ] Add Gtk.Expander for reasoning section
  - [ ] Show "💭 Thinking" label
  - [ ] Start collapsed by default
  - [ ] Style with dim-label CSS class

- [ ] **2.4 Follow-Up Questions**
  - [ ] Create `src/nanochat/ui/widgets/follow_up_questions.py`
  - [ ] Parse follow_up_suggestions from message
  - [ ] Display as clickable chips
  - [ ] Wire click to send as new message

### Phase 3: Streaming Improvements (MEDIUM)

- [ ] **3.1 StreamingManager**
  - [ ] Create `src/nanochat/api/streaming.py`
  - [ ] Add cancellation support (`_cancelled` flag)
  - [ ] Add 5-minute timeout with `asyncio.wait_for()`
  - [ ] Add UI update throttling (50ms minimum between updates)

- [ ] **3.2 Optimistic UI**
  - [ ] Show user message immediately (before server response)
  - [ ] Add "pending" visual indicator
  - [ ] Update message ID after server confirms

### Phase 4: UX Features (MEDIUM)

- [ ] **4.1 Pinned Conversations**
  - [ ] Add `pinned` column to conversations table (if not exists)
  - [ ] Add pin toggle in conversation context menu
  - [ ] Sort pinned conversations to top of list
  - [ ] Add visual indicator (📌 or similar)

- [ ] **4.2 Starred Messages**
  - [ ] Add `starred` column to messages table (if not exists)
  - [ ] Add star button to MessageWidget
  - [ ] Implement `toggle_star()` API call
  - [ ] Update local database on star
  - [ ] Visual feedback (gold star when starred)

- [ ] **4.3 Web Search Result Cards**
  - [ ] Create `src/nanochat/ui/widgets/web_search_card.py`
  - [ ] Parse web search annotations from message
  - [ ] Display collapsible card with sources
  - [ ] Make source links clickable

### Phase 5: Architecture Cleanup (LOWER)

- [ ] **5.1 Split window.py**
  - [ ] Extract sidebar to `src/nanochat/ui/components/sidebar.py`
  - [ ] Extract chat area to `src/nanochat/ui/components/chat_area.py`
  - [ ] Extract input bar to `src/nanochat/ui/components/input_bar.py`
  - [ ] Keep window.py as coordinator (~300 lines)

- [ ] **5.2 ViewModel Layer** (Optional)
  - [ ] Create `src/nanochat/ui/viewmodels/chat_viewmodel.py`
  - [ ] Define `ChatUiState` dataclass
  - [ ] Move state management from window.py
  - [ ] Implement state listener pattern

---

## Quick Reference: Android Source Files

For detailed implementation reference, examine these Android source files:

| Feature | Android File | GitHub URL |
|---------|-------------|------------|
| Database setup | `NanoChatDatabase.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/data/local/NanoChatDatabase.kt) |
| Message DAO | `MessageDao.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/data/local/dao/MessageDao.kt) |
| Conversation sync | `ConversationRepository.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/data/repository/ConversationRepository.kt) |
| Event bus | `ConversationSyncManager.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/data/sync/ConversationSyncManager.kt) |
| Message bubble | `MessageBubble.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/ui/chat/components/MessageBubble.kt) |
| Streaming | `StreamingManager.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/data/remote/StreamingManager.kt) |
| Markdown | `SimpleMarkdownText.kt` | [Link](https://github.com/jcrabapple/nanochat-android/blob/main/app/src/main/java/com/nanogpt/chat/ui/chat/components/SimpleMarkdownText.kt) |

---

## Notes for Future LLM Sessions

When continuing this work:

1. **Check what's already been done** - Review git history and the checklist above
2. **Test incrementally** - Don't implement everything at once
3. **Preserve existing functionality** - Ensure the app still works after each change
4. **Update this document** - Mark completed items on the checklist
5. **Document any deviations** - If you implement something differently, note why

**End of Document**
