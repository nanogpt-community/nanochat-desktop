# Pending Tasks - NanoChat Desktop

**Last Updated**: 2026-01-20
**Current Version**: v0.5.0 (in development)
**Status**: Consolidated task list for future development sessions

---

## How to Use This Document

This is the master task list for all remaining work on NanoChat Desktop. Tasks are organized by **criticality** (most to least important) rather than by phase.

**Workflow for development sessions:**
1. Pick a task from this list
2. Implement the feature
3. When complete, move the task to `completed-items.md`
4. Update the completion date

---

## CRITICAL Priority (Core UX)

These tasks are essential for basic usability and should be completed first.

### [ ] Message Copy Button
**Source**: Phase 3, Task 3.12 (migrated from Phase 2)

Allow users to copy message content to clipboard with a single click.

**Implementation:**
- Add copy button to message widgets (appears on hover)
- Toast notification confirms copy
- Works for both user and assistant messages

**Files**: `src/nanochat/ui/message_widget.py`

---

### [ ] Conversation Renaming
**Source**: Phase 3, Task 3.11 (migrated from Phase 2)

Allow users to rename conversations from the context menu.

**Note**: F2 shortcut exists but shows "coming soon" toast. Full implementation needed.

**Implementation:**
- Right-click context menu on conversation rows
- Inline entry or dialog for new title
- Update API and local cache
- Cancel reverts to original title

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/api/client.py`

---

### [ ] Drag and Drop Attachments
**Source**: Future Enhancements, High Priority

Allow users to drag files directly into chat input area.

**Implementation:**
```python
def _setup_drop_target(self):
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.connect("drop", self._on_file_dropped)
    self.add_controller(drop_target)

def _on_file_dropped(self, target, value, x, y):
    file = value
    path = Path(file.get_path())
    self._attach_file(path)
```

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Message Regeneration
**Source**: Future Enhancements, Medium Priority

Regenerate the last assistant response with a single click.

**Implementation:**
- Add regenerate button to assistant messages
- Calls `/api/generate-message` without message body (regenerates last)
- Shows loading state during regeneration
- Replaces previous response

**API Endpoint**:
```
POST /api/generate-message
{
  "conversation_id": "string"
  // No message - regenerates last
}
```

**Files**: `src/nanochat/ui/message_widget.py`, `src/nanochat/api/client.py`

---

### [ ] Session Persistence
**Source**: Future Enhancements, Lower Priority

Resume last session on startup.

**Implementation:**
- Remember last conversation
- Restore scroll position
- Restore unsent message draft
- Save state periodically

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/data/settings.py`

---

## HIGH Priority (Organization & Core Features)

These tasks add important organizational capabilities and core features that users expect.

### [ ] API Models for Assistants and Projects
**Source**: Phase 3, Task 3.1

Define Pydantic models for Assistants and Projects API responses.

**Models to add:**
- `Assistant` - Full assistant object with all fields
- `CreateAssistantRequest` - For creating new assistants
- `UpdateAssistantRequest` - For updating assistants
- `Project` - Project object with metadata
- `CreateProjectRequest` - For creating new projects
- `UpdateProjectRequest` - For updating projects

**Files**: `src/nanochat/api/models.py`

---

### [ ] API Client Methods for Assistants
**Source**: Phase 3, Task 3.2

Implement API client methods for assistant CRUD operations.

**Methods to add:**
- `get_assistants()` - List all assistants
- `create_assistant(request)` - Create new assistant
- `update_assistant(id, request)` - Update assistant
- `delete_assistant(id)` - Delete assistant
- `set_default_assistant(id)` - Set as default

**Files**: `src/nanochat/api/client.py`

---

### [ ] API Client Methods for Projects
**Source**: Phase 3, Task 3.3

Implement API client methods for project CRUD operations.

**Methods to add:**
- `get_projects()` - List all projects
- `get_project(id)` - Get single project
- `create_project(request)` - Create new project
- `update_project(id, request)` - Update project
- `delete_project(id)` - Delete project
- `move_conversation_to_project(conv_id, project_id)` - Move conversation

**Files**: `src/nanochat/api/client.py`

---

### [ ] Assistants Management UI
**Source**: Phase 3, Task 3.4

Create dialog for managing assistants.

**Features:**
- List all assistants with icons and descriptions
- Create new assistant dialog
- Edit assistant (name, description, system prompt)
- Delete assistant (except default)
- Set assistant as default
- Changes sync to server

**Files to create**:
- `src/nanochat/ui/assistants_dialog.py`
- `src/nanochat/ui/assistant_editor.py`

---

### [ ] Projects Management UI
**Source**: Phase 3, Task 3.5

Create dialog for managing projects.

**Features:**
- List all projects with colors
- Create new project dialog
- Edit project (name, description, color)
- Delete project
- Color picker for project colors

**Files to create**: `src/nanochat/ui/projects_dialog.py`

---

### [ ] Assistant Selector in Chat
**Source**: Phase 3, Task 3.6

Allow selecting an assistant when starting a new conversation.

**Implementation:**
- Assistant dropdown in header bar
- "No Assistant" option at top
- Load assistants from API/cache
- Selected assistant used in message generation

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Project Filter in Sidebar
**Source**: Phase 3, Task 3.7

Filter conversations by project.

**Implementation:**
- Project filter dropdown at top of sidebar
- Options: "All Conversations", "No Project", [project list]
- Projects show their color
- Filter affects conversation list

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Move Conversation to Project
**Source**: Phase 3, Task 3.8

Allow moving conversations between projects.

**Implementation:**
- "Move to Project" submenu in conversation context menu
- Lists all projects plus "No Project"
- Updates server and local state
- Toast confirms action

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Database Caching for Assistants/Projects
**Source**: Phase 3, Task 3.9

Add local SQLite caching for assistants and projects.

**Implementation:**
- Create `assistants` table in database
- Create `projects` table in database
- Sync with API on load
- Support offline mode with cached data

**Files**: `src/nanochat/data/database.py`

---

### [ ] Conversation Export
**Source**: Future Enhancements, High Priority

Export conversations to various formats.

**Implementation:**
- Create `ConversationExporter` class
- Support formats: Markdown (.md), Plain text (.txt), JSON, PDF
- Add export option to conversation menu
- Use weasyprint or reportlab for PDF

**Files to create**: `src/nanochat/export/conversation_exporter.py`

---

### [ ] Multi-Account Support
**Source**: Future Enhancements, High Priority

Support multiple backend configurations/accounts.

**Implementation:**
- Store multiple accounts in config
- Account switcher in settings
- Isolated data per account
- Account selector at startup

**Config structure:**
```toml
[[accounts]]
name = "Personal"
backend_url = "https://personal.nanochat.com"
default = true

[[accounts]]
name = "Work"
backend_url = "https://work.nanochat.com"
```

**Files**: `src/nanochat/data/settings.py`, `src/nanochat/ui/setup_dialog.py`

---

### [ ] System Prompt Quick Edits
**Source**: Future Enhancements, High Priority

Edit system prompt per-conversation without full assistant creation.

**Implementation:**
- "Customize" button in chat header
- Temporary system prompt override
- Option to save as new assistant
- Persists for current conversation

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Text-to-Speech (TTS)
**Source**: Future Enhancements, High Priority

Read assistant responses aloud using NanoGPT TTS API.

**Implementation:**
- Add speaker button to assistant messages
- Use GStreamer for audio playback
- Support voice and speed selection
- Cache generated audio

**API Endpoint**:
```
POST /api/tts
{
  "text": "string",
  "model": "tts-1",
  "voice": "alloy",
  "speed": 1.0
}
Response: audio/mpeg binary
```

**Files**: `src/nanochat/ui/message_widget.py`, `src/nanochat/audio/tts_player.py`

---

### [ ] Speech-to-Text (STT)
**Source**: Future Enhancements, High Priority

Voice input for messages using NanoGPT STT API.

**Implementation:**
- Add microphone button next to send
- Use PipeWire/PulseAudio for microphone access
- Show recording indicator
- Support push-to-talk vs toggle

**API Endpoint**:
```
POST /api/stt
FormData:
  audio: binary (webm, mp4, etc.)
  model: "Whisper-Large-V3"
  language: "auto"

Response:
{
  "transcription": "string",
  "text": "string"
}
```

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/audio/audio_recorder.py`

---

## MEDIUM Priority (Power User Features)

These features add advanced functionality for power users.

### [ ] Image Attachments
**Source**: Phase 4, Task 4.3

Allow attaching images to messages.

**Implementation:**
- Attach button in input area
- File chooser dialog (image filter)
- Upload to `/api/storage` endpoint
- Thumbnail preview with remove button
- Attachment sent with message

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/api/client.py`

---

### [ ] Document Attachments
**Source**: Phase 4, Task 4.4

Support PDF and document attachments.

**Implementation:**
- Extend file chooser for documents (PDF, markdown, text, epub)
- Document icon preview instead of thumbnail
- File type sent correctly in request

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Starred Messages
**Source**: Phase 4, Task 4.5

Allow starring/bookmarking important messages.

**Implementation:**
- Star button on each message
- Visual feedback when starred
- Star status persists via API
- Optional: Starred messages dialog

**Files**: `src/nanochat/ui/message_widget.py`, `src/nanochat/api/client.py`

---

### [ ] Model Analytics View
**Source**: Phase 4, Task 4.6

Show usage statistics and insights.

**Implementation:**
- Analytics dialog accessible from menu
- Shows total messages count
- Shows total cost
- Shows top models by usage
- Data loads from `/api/analytics`

**Files to create**: `src/nanochat/ui/analytics_dialog.py`

---

### [ ] Balance Display
**Source**: Phase 4, Task 4.7

Show NanoGPT account balance in UI.

**Implementation:**
- Balance label in header bar
- Shows balance and subscription usage (if applicable)
- Refreshes every 5 minutes
- Handles missing data gracefully

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/api/client.py`

---

### [ ] API Client Extensions
**Source**: Phase 4, Task 4.8

Add new API client methods for Phase 4 features.

**Methods to add:**
- `get_balance()` - Get NanoGPT balance
- `get_subscription_usage()` - Get subscription usage
- `get_analytics()` - Get model analytics
- `upload_file(content, filename, mime_type)` - Upload file
- `delete_file(storage_id)` - Delete file
- `set_message_starred(message_id, starred)` - Set starred status
- `get_starred_messages()` - Get all starred messages

**Files**: `src/nanochat/api/client.py`

---

### [ ] Annotation Display
**Source**: Phase 4, Task 4.9

Show web search results and other annotations in messages.

**Implementation:**
- Parse `message.annotations` field
- Display web search results as card with source links
- Handle different annotation types gracefully
- Clean presentation below message content

**Files**: `src/nanochat/ui/message_widget.py`

---

### [ ] Pinned Conversations
**Source**: Future Enhancements, Medium Priority

Pin important conversations to top of list.

**API Endpoint**:
```
POST /api/db/conversations
{
  "action": "togglePin",
  "conversationId": "string"
}
```

**Implementation:**
- Pin icon on conversation rows
- Pinned section at top of list
- Persist via API

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/api/client.py`

---

### [ ] Conversation Branching
**Source**: Future Enhancements, Medium Priority

Branch from any message to explore alternative responses.

**API Endpoint**:
```
POST /api/db/conversations
{
  "action": "branch",
  "conversationId": "string",
  "fromMessageId": "string"
}
```

**Implementation:**
- Add "Branch from here" to message context menu
- Creates new conversation from that point
- Shows relationship in UI

**Files**: `src/nanochat/ui/message_widget.py`, `src/nanochat/api/client.py`

---

### [ ] Image Generation Display
**Source**: Future Enhancements, Medium Priority

Display generated images inline in chat.

**Implementation:**
- Detect image model responses
- Display images with download option
- Support image gallery for multiple images
- Lightbox view for images

**Files**: `src/nanochat/ui/message_widget.py`

---

### [ ] Message Search
**Source**: Future Enhancements, Lower Priority (moved to Medium)

Search within message content across all conversations.

**Implementation:**
- Full-text search in local database
- Search dialog accessible from menu
- Highlight matching messages
- Jump to conversation/message

**Files**: `src/nanochat/ui/search_dialog.py`, `src/nanochat/data/database.py`

---

## LOWER Priority (Polish & Nice-to-Have)

These tasks improve polish and aesthetics but are not critical.

### [ ] Catppuccin Theme Support
**Source**: Phase 5, Task 5.1

Add Catppuccin color palette support (Latte and Mocha variants).

**Implementation:**
- Define Catppuccin color palettes
- Generate CSS from palette
- Apply theme with Gtk.CssProvider
- Theme selector in settings

**Files to create**:
- `src/nanochat/ui/themes/catppuccin.py`
- `data/styles/catppuccin-latte.css`
- `data/styles/catppuccin-mocha.css`

---

### [ ] Tokyo Night Theme Support
**Source**: Phase 5, Task 5.2

Add Tokyo Night color palette (dark and light variants).

**Implementation:**
- Define Tokyo Night color palettes
- Generate CSS from palette
- Apply theme with Gtk.CssProvider
- Theme selector in settings

**Files to create**:
- `src/nanochat/ui/themes/tokyo_night.py`
- `data/styles/tokyo-night.css`

---

### [ ] Theme Manager
**Source**: Phase 5, Task 5.3

Centralized theme management with persistence.

**Implementation:**
- `ThemeManager` class to handle all themes
- Apply theme method with proper CSS switching
- Persist theme preference
- Theme selector in settings with all options

**Files to create**: `src/nanochat/ui/themes/manager.py`

---

### [ ] Responsive Layout
**Source**: Phase 5, Task 5.4

Support different window sizes gracefully.

**Implementation:**
- Use Adw.NavigationSplitView for responsive sidebar
- Collapse sidebar on narrow windows (< 600px)
- Define breakpoints: compact, medium, expanded
- Smooth transitions between layouts

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Accessibility Improvements
**Source**: Phase 5, Task 5.5

Ensure app is accessible to all users.

**Implementation:**
- Proper labels and tooltips on all interactive elements
- Keyboard navigation works throughout
- Logical tab order
- Screen reader can read messages
- Clear focus indicators
- High contrast mode support

**Files**: Multiple UI files

---

### [ ] Error Handling and Recovery
**Source**: Phase 5, Task 5.6

Graceful error handling with user-friendly messages.

**Implementation:**
- Error dialog for displaying errors
- Network error handling with friendly messages
- Auth errors prompt re-authentication
- Rate limits handled gracefully
- Automatic reconnection attempt (exponential backoff)

**Files**: `src/nanochat/ui/window.py`, new `src/nanochat/ui/error_dialog.py`

---

### [ ] Performance Optimization
**Source**: Phase 5, Task 5.7

Ensure smooth performance.

**Implementation:**
- Lazy loading for conversation lists
- Message virtualization for large chats
- Background sync (don't block UI)
- Cache cleanup for old data

**Files**: `src/nanochat/ui/window.py`, `src/nanochat/data/database.py`

---

### [ ] App Icon and Branding
**Source**: Phase 5, Task 5.8

Create polished app icon and branding.

**Implementation:**
- Create app icon (512x512 PNG, SVG source)
- Multiple sizes: 256, 128, 64, 48, 32, 16
- Icon design: simple, recognizable, follows GNOME guidelines
- Desktop file with proper metadata

**Files to create**:
- `data/icons/hicolor/scalable/apps/com.nanogpt.NanoChat.svg`
- `data/icons/hicolor/*/apps/com.nanogpt.NanoChat.png`
- `data/com.nanogpt.NanoChat.desktop`

---

### [ ] Flatpak Metadata
**Source**: Phase 5, Task 5.9

Complete Flatpak metadata for app store.

**Implementation:**
- Create `com.nanogpt.NanoChat.metainfo.xml`
- Description with feature list
- Screenshots (4 high-quality images)
- App store metadata complete
- Content rating

**Files to create**: `flatpak/com.nanogpt.NanoChat.metainfo.xml`

---

### [ ] Documentation
**Source**: Phase 5, Task 5.10

Complete user and developer documentation.

**Documents to create:**
- `docs/README.md` - Project overview
- `docs/INSTALL.md` - Installation instructions
- `docs/USAGE.md` - User guide
- `docs/CONTRIBUTING.md` - Contributor guide
- `docs/CHANGELOG.md` - Version history

---

### [ ] MCP (Model Context Protocol) Support
**Source**: Future Enhancements, Lower Priority

Execute MCP tools from the desktop client.

**API Endpoints**:
```
GET /api/mcp - Check MCP status
POST /api/mcp - Execute tool
{
  "tool": "string",
  "args": {}
}
```

**Implementation:**
- Display available tools
- Tool execution results in chat
- Error handling for tool failures

**Files**: `src/nanochat/api/client.py`, `src/nanochat/ui/mcp_panel.py`

---

### [ ] Project Files Management
**Source**: Future Enhancements, Lower Priority

Manage project files from desktop.

**API Endpoints**:
```
GET    /api/projects/:id/files
POST   /api/projects/:id/files   (upload)
DELETE /api/projects/:id/files?fileId=...
```

**Implementation:**
- File list in project details
- Upload files to projects
- Delete files from projects

**UI Mock**:
```
┌─────────────────────────────────────────┐
│ Project: My Research          [+ File]  │
├─────────────────────────────────────────┤
│ 📄 document.pdf               [🗑]      │
│ 📄 notes.md                   [🗑]      │
│ 📄 data.csv                   [🗑]      │
└─────────────────────────────────────────┘
```

**Files**: `src/nanochat/ui/projects_dialog.py`

---

### [ ] Shared Projects
**Source**: Future Enhancements, Lower Priority

View shared projects and collaborate.

**API Endpoints**:
```
GET    /api/projects/:id/members
POST   /api/projects/:id/members
DELETE /api/projects/:id/members?userId=...
```

**Implementation:**
- Show project members
- Invite members to projects
- Member role management

**Files**: `src/nanochat/ui/projects_dialog.py`

---

### [ ] Custom Rules Support
**Source**: Future Enhancements, Lower Priority

Manage user rules for AI behavior.

**API Endpoints**:
```
GET    /api/db/user-rules
POST   /api/db/user-rules
DELETE /api/db/user-rules?id=...
```

**Implementation:**
- Rules management dialog
- Create/edit/delete rules
- Rules applied to all conversations

**Files**: `src/nanochat/ui/rules_dialog.py`

---

### [ ] Provider Preferences
**Source**: Future Enhancements, Lower Priority

Configure preferred AI providers per model.

**API Endpoints**:
```
GET   /api/provider-preferences
PATCH /api/provider-preferences
```

**Implementation:**
- Provider preferences in settings
- Per-model provider selection
- Fallback providers

**Files**: `src/nanochat/ui/provider_prefs.py`

---

### [ ] Video Generation Support
**Source**: Future Enhancements, Lower Priority

Support video model workflows.

**API Endpoints**:
```
POST /api/video/generate
GET  /api/video/status?runId=...
```

**Implementation:**
- Detect video model responses
- Show generation progress
- Video player for playback

**Files**: `src/nanochat/ui/message_widget.py`

---

### [ ] Notification Support
**Source**: Future Enhancements, Lower Priority

System notifications for long-running tasks.

**Implementation:**
```python
def _send_notification(self, title: str, body: str):
    notification = Gio.Notification.new(title)
    notification.set_body(body)
    self.get_application().send_notification(None, notification)
```

**Files**: `src/nanochat/ui/window.py`

---

### [ ] Notification Support (Long-Running Tasks)
**Source**: Future Enhancements, Lower Priority

Show system notifications when generation completes in background.

**Implementation:**
- Notify when long generation completes
- Notify on errors
- Notify when files finish uploading
- Respect system notification settings

**Files**: `src/nanochat/application.py`

---

## EXPERIMENTAL Features

These features are exploratory and may or may not be implemented.

### [ ] Local LLM Support
**Source**: Future Enhancements, Experimental

Connect to local Ollama or llama.cpp.

**Implementation Notes:**
- Alternative backend URL
- Local model selection
- No auth required
- Different protocol handling

**Files**: `src/nanochat/api/client.py`, `src/nanochat/ui/setup_dialog.py`

---

### [ ] Multiple Chat Windows
**Source**: Future Enhancements, Experimental

Open conversations in separate windows.

**Implementation:**
- "Open in New Window" option in conversation menu
- Multiple window support in application
- Independent state per window

**Files**: `src/nanochat/application.py`, `src/nanochat/ui/window.py`

---

### [ ] Chat Templates
**Source**: Future Enhancements, Experimental

Start conversations from templates.

**Implementation:**
- Template library
- Quick-start from template
- Custom templates
- Template sharing

**Files**: `src/nanochat/ui/templates_dialog.py`

---

### [ ] Plugin System
**Source**: Future Enhancements, Lower Priority (Experimental)

Allow custom extensions via plugins.

**Implementation:**
- Plugin API definition
- Plugin discovery (XDG plugin directories)
- Plugin loading system
- Safety sandboxing

**Complexity**: Very high - defer indefinitely

**Files**: `src/nanochat/plugins/` (new directory)

---

## OPTIONAL / LOW Priority

These features are nice-to-have but can be deferred indefinitely.

### [ ] System Tray Integration
**Source**: Phase 3, Task 3.14 (lower priority)

Allow app to minimize to system tray.

**Note**: Tray support varies by desktop environment.

**Implementation:**
- Use AppIndicator3 for Ubuntu/GNOME
- Graceful fallback where not supported
- Click shows/hides window
- Right-click shows menu with quit option

**Files**: `src/nanochat/application.py`

---

## Summary Statistics

- **Total Pending Tasks**: 58
- **Critical Priority**: 4 (Keyboard Shortcuts and Conversation Search completed 2025-01-18)
- **High Priority**: 15
- **Medium Priority**: 15
- **Lower Priority**: 22
- **Experimental**: 4
- **Optional**: 1

---

## Notes for Future Sessions

1. **Start with Critical tasks** - These affect core user experience
2. **Complete High Priority before moving to Medium** - Organization features are important
3. **Test thoroughly** - Each task should be manually tested before marking complete
4. **Move completed items** - When done, move task to `completed-items.md` with date
5. **Update this document** - Keep descriptions accurate as implementation details evolve

---

## Version Planning

| Version | Focus | Task Count | Status |
|---------|-------|------------|--------|
| v0.3.0 | Assistants & Projects (HIGH) | 15 tasks | Not started |
| v0.4.0 | Core UX Improvements (CRITICAL) | 2 tasks completed | In progress |
| v0.5.0 | Polish & Release (LOWER) | 22 tasks | Not started |
| v1.1.0+ | Future Enhancements | ~8 tasks | Not started |
| Post-v1.0 | Experimental | ~4 tasks | Not started |
