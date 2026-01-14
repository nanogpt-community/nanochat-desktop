# CLAUDE.md - LLM Instructions for NanoChat Desktop Development

> This file provides instructions for AI assistants (Claude, GPT, etc.) working on the NanoChat Desktop project.

## Project Overview

NanoChat Desktop is a Linux desktop application that provides a native GTK4 interface for the NanoChat API. It is being developed as a fresh implementation inspired by the Android client, focusing on Linux-native features and conventions.

**Repository**: `nanochat-desktop-v2`  
**Tech Stack**: Python 3.11+, GTK4/Libadwaita, httpx, Pydantic, SQLite

---

## Key Documents

Before starting any work, review these documents in order:

1. [`plans/nanochat-desktop-development-plan.md`](nanochat-desktop-development-plan.md) - High-level architecture and tech stack
2. [`plans/api-docs.md`](api-docs.md) - Complete API documentation
3. Phase-specific plans in `plans/phase-*.md`

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
# 4. Upload binary files (Flatpak, AppImage)
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

### SSE Streaming
The `/api/generate-message` endpoint returns Server-Sent Events:
```python
async def stream_message(request: GenerateMessageRequest):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{base_url}/api/generate-message",
            headers=headers,
            json=request.model_dump(exclude_none=True)
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield StreamComplete()
                    else:
                        event = parse_sse_event(data)
                        yield event
```

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

## Phase-Specific Instructions

See the detailed phase plans for specific implementation guidance:

- **Phase 1** (`plans/phase-1-mvp.md`): Core chat, API client, basic UI
- **Phase 2** (`plans/phase-2-enhanced-ux.md`): Search, keyboard shortcuts, themes
- **Phase 3** (`plans/phase-3-assistants-projects.md`): Assistants and projects management
- **Phase 4** (`plans/phase-4-advanced-features.md`): Web search, attachments, analytics
- **Phase 5** (`plans/phase-5-polish.md`): Themes, accessibility, store submission

---

## Do's and Don'ts

### Do
- ✅ Reference `plans/api-docs.md` for exact endpoint signatures
- ✅ Use async/await for all network operations
- ✅ Handle all error cases with user-friendly messages
- ✅ Test on both X11 and Wayland
- ✅ Follow XDG Base Directory specification for file paths
- ✅ Use libsecret for storing sensitive data (API keys)

### Don't
- ❌ Block the UI thread with synchronous operations
- ❌ Store API keys in plain text files
- ❌ Hardcode the backend URL
- ❌ Use GTK3 widgets (this is a GTK4 project)
- ❌ Skip error handling for API calls
- ❌ Forget to update the todo list after completing tasks

---

## Useful Commands

```bash
# Run the application in development
python -m nanochat

# Run with debug logging
NANOCHAT_DEBUG=1 python -m nanochat

# Build Flatpak locally
flatpak-builder --user --install build flatpak/com.nanogpt.NanoChat.yml

# Build AppImage
python -m python_appimage build app -p 3.11 .

# Check code style
ruff check src/
black --check src/
```

---

## Contact and Support

- **API Issues**: Check `plans/api-docs.md` first
- **Architecture Questions**: See `plans/nanochat-desktop-development-plan.md`
- **Phase-Specific Questions**: See relevant `plans/phase-*.md` file
