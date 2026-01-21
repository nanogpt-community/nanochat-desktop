# Issue #12: Local DB not caching messages it sent

**Issue URL**: https://github.com/nanogpt-community/nanochat-desktop/issues/12
**Status**: OPEN
**Priority**: HIGH

## Description
Whenever sending a message to the server and getting a response, the expectation is that the message is cached in the DB so that if the app is closed and reopened immediately, the message is there and it doesn't have to fetch it from the server. Currently, when reopening the app and clicking on a recent message, there's network traffic to retrieve the data.

## Objective
Implement proper local database caching for messages so that:
- User-sent messages are immediately saved to the local database
- Assistant responses are saved to the local database as they're received
- On app startup, recent conversations load from local cache instead of making network requests
- Network requests are only made for updates/new messages, not cached data

## Technical Context
- **File Location**: `src/data/database.py`, `src/api/client.py`, `src/ui/chat_view.py`
- **Tech Stack**: SQLite, httpx, Pydantic
- **Related API Endpoints**:
  - `POST /api/generate-message` - Send message
  - `GET /api/db/messages?conversationId={id}` - Get messages
  - `GET /api/db/conversations?id={id}` - Get conversation

## Root Cause Analysis

The issue indicates that messages are not being written to the local database when:
1. User sends a message
2. Server response is received

This could be due to:
- Missing database write operations after message creation
- Database writes happening but not being queried correctly on app startup
- Race condition where UI loads before database writes complete
- Database transactions not being committed

## Implementation Plan

### Step 1: Audit Current Message Flow
**Files to analyze**: 
- `src/api/client.py` - Check where messages are sent/received
- `src/data/database.py` - Check if message insert/update methods exist
- `src/ui/chat_view.py` - Check where messages are displayed

**Actions**:
1. Trace the code path from user input → server → database
2. Identify where database writes should occur
3. Check if database writes are actually happening
4. Verify database queries on app startup

### Step 2: Implement Message Caching on Send
**Files to modify**: `src/api/client.py` or message handling logic

When a user sends a message:
```python
async def send_message(self, conversation_id: str, message: str):
    # 1. Create user message object
    user_message = Message(
        id=str(uuid.uuid4()),  # Generate client-side ID
        conversation_id=conversation_id,
        role="user",
        content=message,
        created_at=datetime.utcnow(),
    )
    
    # 2. Save to local database IMMEDIATELY
    await self.db.insert_message(user_message)
    
    # 3. Send to server
    response = await self._request(
        "POST",
        "/api/generate-message",
        json={
            "message": message,
            "conversation_id": conversation_id,
        }
    )
    
    return response
```

### Step 3: Implement Response Caching
**Files to modify**: Message polling/streaming logic

During the polling loop (as per CLAUDE.md instructions):
```python
async def generate_message_with_polling(request: GenerateMessageRequest):
    # Send the message
    response = await client._request(
        "POST",
        "/api/generate-message",
        json=request.model_dump(exclude_none=True, by_alias=True)
    )
    conversation_id = response.get("conversation_id")
    
    max_polls = 600
    last_content = ""
    assistant_message_id = None
    
    for _ in range(max_polls):
        await asyncio.sleep(0.5)
        
        # Get messages from server
        messages = await client.get_messages(conversation_id)
        
        # Find assistant message
        for msg in messages:
            if msg.role == "assistant":
                # CACHE TO DATABASE
                if msg.content != last_content:
                    last_content = msg.content
                    
                    # Update or insert to database
                    if assistant_message_id is None:
                        assistant_message_id = msg.id
                        await self.db.insert_message(msg)
                    else:
                        await self.db.update_message(msg.id, content=msg.content)
                    
                    # Update UI
                    GLib.idle_add(self._update_message_display, msg.content)
        
        # Check if generation complete
        conversation = await client.get_conversation(conversation_id)
        if not conversation.generating:
            break
    
    return last_content
```

### Step 4: Update Database Schema
**Files to modify**: `src/data/database.py`

Ensure the database has proper methods for message operations:
```python
class Database:
    async def insert_message(self, message: Message):
        """Insert a new message into the database"""
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role,
                    message.content,
                    message.created_at.isoformat() if message.created_at else None,
                )
            )
            await conn.commit()
    
    async def update_message(self, message_id: str, content: str):
        """Update an existing message's content"""
        async with self.connection() as conn:
            await conn.execute(
                """
                UPDATE messages 
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (content, message_id)
            )
            await conn.commit()
    
    async def get_messages_by_conversation(self, conversation_id: str) -> list[Message]:
        """Get all messages for a conversation from local cache"""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, conversation_id, role, content, created_at, updated_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            rows = await cursor.fetchall()
            return [Message.from_db_row(row) for row in rows]
```

### Step 5: Load from Cache on Startup
**Files to modify**: `src/ui/main_window.py` or conversation list logic

When loading conversations on app startup:
```python
async def load_conversation(self, conversation_id: str):
    # 1. First, try to load from local cache
    cached_messages = await self.db.get_messages_by_conversation(conversation_id)
    
    if cached_messages:
        # Display cached messages immediately (fast!)
        for msg in cached_messages:
            self._display_message(msg)
    
    # 2. Then, check for updates from server (background)
    try:
        # Get latest conversation state
        conversation = await self.api_client.get_conversation(conversation_id)
        
        # Get latest messages from server
        server_messages = await self.api_client.get_messages(conversation_id)
        
        # Compare and update cache if needed
        if len(server_messages) > len(cached_messages):
            # New messages exist, update cache and UI
            for msg in server_messages:
                await self.db.insert_message(msg)
                if msg.id not in [m.id for m in cached_messages]:
                    self._display_message(msg)
    except Exception as e:
        # Offline mode - just use cache
        logger.warning(f"Could not sync from server: {e}")
```

### Step 6: Add Sync Status Indicator
**Files to modify**: `src/ui/chat_view.py`

Add UI indicator to show when syncing with server:
```python
def _show_sync_status(self, syncing: bool):
    if syncing:
        self.sync_spinner.start()
        self.sync_label.set_text("Syncing...")
    else:
        self.sync_spinner.stop()
        self.sync_label.set_text("Up to date")
```

### Step 7: Test Implementation

**Manual Testing Checklist**:
- [ ] Send a message and verify it appears in the database immediately
- [ ] Close the app before the assistant response completes
- [ ] Reopen the app and verify the user message is still there
- [ ] Verify assistant responses are saved as they stream in
- [ ] Close and reopen app, verify no network traffic for cached conversations
- [ ] Test offline mode - verify app works with cached data
- [ ] Test with slow network connection
- [ ] Verify database file grows appropriately

**Database Verification**:
```bash
# Check that messages are being written
sqlite3 ~/.local/share/nanochat/nanochat.db "SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;"
```

## Files to Create/Modify

### Modified Files
- `src/data/database.py` - Add/fix message insert/update methods
- `src/api/client.py` - Add database caching to message operations
- `src/ui/chat_view.py` - Load from cache first, then sync
- `src/ui/main_window.py` - Implement cache-first loading strategy

### New Files
None (unless we want to create a separate caching layer)

## Dependencies
- `aiosqlite` - Already in use for async SQLite operations
- No new dependencies required

## Acceptance Criteria
- [ ] User messages are written to local database immediately on send
- [ ] Assistant responses are cached to database as they're received
- [ ] On app startup, conversations load from cache (no network traffic)
- [ ] Background sync updates cache with any new messages from server
- [ ] App works in offline mode with cached conversations
- [ ] No duplicate messages in the database
- [ ] Database operations don't block the UI

## Potential Issues & Solutions

**Issue**: Race condition - UI loads before database write completes
**Solution**: Ensure database writes use `await` and complete before UI updates

**Issue**: Duplicate messages in database
**Solution**: Use `INSERT ... ON CONFLICT` to handle duplicates gracefully

**Issue**: Database file grows too large
**Solution**: Implement message pruning/archiving for old conversations (future enhancement)

**Issue**: Sync conflicts - local vs server state
**Solution**: Always prefer server state as source of truth, use server-provided message IDs

## Related Issues
- Issue #3 (CLOSED) - DB not caching chats (similar issue, may have been partially fixed)

## Estimated Effort
**Time**: 4-6 hours
**Complexity**: Medium-High
**Risk**: Medium (database operations can be tricky)

## Additional Notes
- This is a critical UX issue - users expect offline access to recent chats
- Consider implementing a sync strategy (immediate vs periodic)
- May want to add a "refresh" button for manual sync
- Consider adding database indexes on `conversation_id` for faster queries
- Future: Implement conflict resolution for offline edits
