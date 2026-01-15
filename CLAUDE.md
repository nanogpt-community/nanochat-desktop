# CLAUDE.md - LLM Instructions for NanoChat Desktop Development

> This file provides instructions for AI assistants (Claude, GPT, etc.) working on the NanoChat Desktop project.

## Project Overview

NanoChat Desktop is a Linux desktop application that provides a native GTK4 interface for the NanoChat API. It is being developed as a fresh implementation inspired by the Android client, focusing on Linux-native features and conventions.

**Repository**: `nanochat-desktop-v2`
**Tech Stack**: Python 3.11+, GTK4/Libadwaita, httpx, Pydantic, SQLite

---

## Key Documents

### Primary Task Tracking (READ THIS FIRST)

**IMPORTANT**: The project now uses consolidated task tracking. Always work from the prioritized task list.

1. [`plans/pending-tasks.md`](plans/pending-tasks.md) - **MASTER TASK LIST** - All pending work, organized by priority (CRITICAL → HIGH → MEDIUM → LOWER)
2. [`plans/completed-items.md`](plans/completed-items.md) - Archive of completed features and releases

### Reference Documentation

3. [`plans/nanochat-desktop-development-plan.md`](plans/nanochat-desktop-development-plan.md) - High-level architecture and tech stack
4. [`plans/other plan docs/api-docs.md`](plans/other%20plan%20docs/api-docs.md) - Complete API documentation
5. [`plans/github-workflow.md`](plans/github-workflow.md) - Git workflow and release process

### Archived Phase Plans

Original phase-specific plans have been moved to [`plans/other plan docs/`](plans/other%20plan%20docs/) for reference. These contain detailed implementation notes but task tracking happens in `pending-tasks.md`.

---

## Task Workflow for Development Sessions

### Step 1: Pick a Task

Go to [`plans/pending-tasks.md`](plans/pending-tasks.md) and select the next task:
- Start with **CRITICAL** priority tasks (Core UX)
- Then move to **HIGH** priority (Organization & Core Features)
- Reference archived phase plans for implementation details

### Step 2: Implement

- Follow the coding standards below
- Reference the appropriate archived phase plan in [`plans/other plan docs/`](plans/other%20plan%20docs/)
- Check [`api-docs.md`](plans/other%20plan%20docs/api-docs.md) for API endpoint signatures

### Step 3: Mark Complete

When done:
1. Cut the task from `pending-tasks.md`
2. Paste it into `completed-items.md` with completion date
3. Update task counts

### Step 4: Continue

Move to the next task in priority order.

---

## Current Status

**Version**: v0.2.0 (Released)
**Next Phase**: v0.3.0 - Assistants and Projects

**Completed** (20 items):
- Phase 1: MVP Core Chat (v0.1.0)
- Phase 2: Enhanced UX (v0.2.0) - Theme support, message display, stop button, toasts, caching

**Pending** (60 tasks):
- CRITICAL: 6 tasks (copy button, shortcuts, rename, search, drag & drop, regeneration)
- HIGH: 15 tasks (assistants, projects, TTS/STT, export, multi-account)
- MEDIUM: 15 tasks (web search, attachments, analytics)
- LOWER: 22 tasks (themes, accessibility, documentation)
- EXPERIMENTAL: 4 tasks (local LLM, multiple windows, plugins)

---

## Coding Standards

### Python Style
- Use Python 3.11+ features (match statements, type hints, etc.)
- Follow PEP 8 with 100-character line limit
- Use `ruff` for linting and `black` for formatting
- All functions must have type hints
- Use docstrings for public functions and classes

### GTK4/PyGObject Style
- Use Libadwaita widgets where available (AdwApplicationWindow, AdwHeaderBar, etc.)
- Prefer declarative UI with `.ui` files or Blueprint when complex
- Use GLib.idle_add() for thread-safe UI updates
- Handle async operations with asyncio + GLib event loop integration

### File Organization
```
src/
├── __init__.py
├── main.py              # Entry point, minimal code
├── application.py       # Adw.Application subclass
├── api/                 # All API-related code
├── data/                # Database, settings, secrets
├── ui/                  # GTK widgets and windows
└── utils/               # Helper functions
```

### Import Order
```python
# Standard library
import asyncio
from pathlib import Path

# Third-party
import httpx
from pydantic import BaseModel

# GTK/GLib
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Local imports
from nanochat.api import client
from nanochat.data import database
```

---

## Git Workflow

### Branch Strategy
- **Main branch**: `main` - always stable, contains latest release
- **Development**: Work on feature branches, merge to version branches
- **Version branches**: `v0.1.0`, `v0.2.0`, etc. - each phase gets its own version
- **Tags**: Match branch names exactly (tag `v0.1.0` on branch `v0.1.0`)

### Commit Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**: feat, fix, docs, style, refactor, test, chore
**Scopes**: api, ui, data, build, deps

**Examples**:
```
feat(api): implement SSE streaming for message generation
fix(ui): prevent crash when conversation list is empty
docs(readme): add installation instructions
chore(deps): update httpx to 0.27.0
```

### Creating a Release
```bash
# Ensure you're on the version branch
git checkout v0.1.0

# Tag the release
git tag -a v0.1.0 -m "Release v0.1.0 - MVP Core Chat"

# Push branch and tag
git push origin v0.1.0
git push origin --tags

# On GitHub:
# 1. Go to Releases > Draft a new release
# 2. Select tag v0.1.0
# 3. Set release title: "v0.1.0 - MVP Core Chat"
# 4. Upload the Flatpak bundle (.flatpak file)
# 5. Publish release
```

---

## API Integration Guidelines

### Authentication
All API requests must include the Bearer token:
```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

### Message Generation (Polling-based)

The `/api/generate-message` endpoint returns immediately with a `conversation_id`. The client must poll for the generated message content:

```python
async def generate_message_with_polling(request: GenerateMessageRequest):
    # 1. Send the message (returns immediately with conversation_id)
    response = await client._request(
        "POST",
        "/api/generate-message",
        json=request.model_dump(exclude_none=True, by_alias=True)
    )
    conversation_id = response.get("conversation_id")

    # 2. Poll for messages and conversation status
    max_polls = 600  # 5 minutes at 0.5s intervals
    last_content = ""

    for _ in range(max_polls):
        await asyncio.sleep(0.5)

        # Check conversation status to see if still generating
        conversation = await client.get_conversation(conversation_id)

        # Get messages
        messages = await client.get_messages(conversation_id)

        # Find assistant message and update if content changed
        for msg in messages:
            if msg.role == "assistant" and msg.content:
                if msg.content != last_content:
                    last_content = msg.content
                    # Update UI with new content
                    ...

        # Stop polling when generation is complete
        if not conversation.generating:
            break

    return last_content
```

**Key Points:**
- The API returns immediately with `conversation_id` - it does NOT use SSE streaming
- Poll `/api/db/messages?conversationId={id}` every 0.5 seconds for updated content
- Poll `/api/db/conversations?id={id}` to check the `generating` field
- Stop when `generating` is `false` or when complete content is received
- The `Conversation` model has a `generating: bool` field that indicates active generation

### Error Handling
```python
try:
    response = await client.get(url)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        # Handle authentication error
        raise AuthenticationError("Invalid API key")
    elif e.response.status_code == 429:
        # Handle rate limiting
        raise RateLimitError("Too many requests")
    else:
        raise APIError(f"API error: {e.response.status_code}")
except httpx.NetworkError:
    raise ConnectionError("Cannot reach server")
```

---

## Testing Approach

### Manual Testing Checklist
For each feature, verify:
- [ ] Works with valid input
- [ ] Handles empty/null values gracefully
- [ ] Network errors show user-friendly messages
- [ ] UI remains responsive during async operations
- [ ] Keyboard navigation works

### API Testing with curl
```bash
# Test connection
curl -X GET "$BACKEND_URL/api/models" \
  -H "Authorization: Bearer $API_KEY"

# Test message generation (non-streaming)
curl -X POST "$BACKEND_URL/api/generate-message" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "model_id": "gpt-4o"}'
```

---

## Common Tasks for LLM

### 1. Implementing a New API Endpoint

1. Add Pydantic models in `src/api/models.py`:
   ```python
   class NewFeatureRequest(BaseModel):
       field1: str
       field2: Optional[int] = None

   class NewFeatureResponse(BaseModel):
       success: bool
       data: dict
   ```

2. Add method to `src/api/client.py`:
   ```python
   async def new_feature(self, request: NewFeatureRequest) -> NewFeatureResponse:
       response = await self._request("POST", "/api/new-feature", json=request.model_dump())
       return NewFeatureResponse.model_validate(response)
   ```

3. Add UI integration in appropriate widget

### 2. Adding a New GTK Widget

1. Create widget file in `src/ui/`:
   ```python
   @Gtk.Template(filename="widget.ui")  # Optional, can be pure Python
   class NewWidget(Adw.Bin):
       __gtype_name__ = "NewWidget"

       def __init__(self):
           super().__init__()
           self._setup_ui()

       def _setup_ui(self):
           # Build UI programmatically or load template
           pass
   ```

2. Register in `src/ui/__init__.py`

3. Use in parent widget or window

### 3. Database Schema Changes

1. Update models in `src/data/models.py`
2. Add migration in `src/data/migrations/`
3. Update `database.py` to apply migrations on startup

---

## Reference Materials by Topic

### For Architecture Decisions
See: [`plans/nanochat-desktop-development-plan.md`](plans/nanochat-desktop-development-plan.md)

### For API Endpoints
See: [`plans/other plan docs/api-docs.md`](plans/other%20plan%20docs/api-docs.md)

### For Implementation Details (Archived)
- **Phase 1**: [`plans/other plan docs/phase-1-mvp.md`](plans/other%20plan%20docs/phase-1-mvp.md) - Core chat, API client, basic UI
- **Phase 2**: [`plans/other plan docs/phase-2-enhanced-ux.md`](plans/other%20plan%20docs/phase-2-enhanced-ux.md) - Search, shortcuts, themes
- **Phase 3**: [`plans/other plan docs/phase-3-assistants-projects.md`](plans/other%20plan%20docs/phase-3-assistants-projects.md) - Assistants, projects
- **Phase 4**: [`plans/other plan docs/phase-4-advanced-features.md`](plans/other%20plan%20docs/phase-4-advanced-features.md) - Web search, attachments
- **Phase 5**: [`plans/other plan docs/phase-5-polish.md`](plans/other%20plan%20docs/phase-5-polish.md) - Themes, accessibility

---

## Do's and Don'ts

### Do
- ✅ Work from [`plans/pending-tasks.md`](plans/pending-tasks.md) - Pick tasks in priority order
- ✅ Reference [`plans/other plan docs/api-docs.md`](plans/other%20plan%20docs/api-docs.md) for exact endpoint signatures
- ✅ Use async/await for all network operations
- ✅ Handle all error cases with user-friendly messages
- ✅ Test on both X11 and Wayland
- ✅ Follow XDG Base Directory specification for file paths
- ✅ Use libsecret for storing sensitive data (API keys)
- ✅ Move completed tasks to [`plans/completed-items.md`](plans/completed-items.md)

### Don't
- ❌ Create new phase-specific plans - Use `pending-tasks.md`
- ❌ Block the UI thread with synchronous operations
- ❌ Store API keys in plain text files
- ❌ Hardcode the backend URL
- ❌ Use GTK3 widgets (this is a GTK4 project)
- ❌ Skip error handling for API calls
- ❌ Forget to update task tracking documents

---

## Useful Commands

```bash
# Run the application in development
python -m nanochat

# Run with debug logging
NANOCHAT_DEBUG=1 python -m nanochat

# Build Flatpak locally
flatpak-builder --user --install --force-clean build flatpak/com.nanogpt.NanoChat.yml

# Export Flatpak as single file
flatpak build-export export build
flatpak build-bundle export com.nanogpt.NanoChat-<version>.flatpak com.nanogpt.NanoChat

# Check code style
ruff check src/
black --check src/
```

---

## Contact and Support

- **Current Tasks**: [`plans/pending-tasks.md`](plans/pending-tasks.md)
- **API Documentation**: [`plans/other plan docs/api-docs.md`](plans/other%20plan%20docs/api-docs.md)
- **Architecture**: [`plans/nanochat-desktop-development-plan.md`](plans/nanochat-desktop-development-plan.md)
- **Git Workflow**: [`plans/github-workflow.md`](plans/github-workflow.md)
- **Implementation Details**: See relevant phase plan in [`plans/other plan docs/`](plans/other%20plan%20docs/)
