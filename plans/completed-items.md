# Completed Items - NanoChat Desktop

**Last Updated**: 2026-01-20
**Current Version**: v0.5.0 (in development)

---

## How to Use This Document

This document tracks all completed work on NanoChat Desktop. When tasks from `pending-tasks.md` are completed, they should be moved here with the completion date.

**Format:**
- ✅ Task name
  - **Completed**: YYYY-MM-DD
  - **Source**: Phase X, Task X.X
  - **Description**: Brief description of what was implemented

---

## Phase 1: MVP Core Chat (v0.1.0)

### ✅ Project Scaffolding
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Initial Setup
- **Description**: Set up project structure, Python packaging, basic configuration

### ✅ API Client Foundation
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.1
- **Description**: Base API client with polling-based message generation

### ✅ Data Layer (Settings, Secrets, XDG)
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.2
- **Description**: Settings management with XDG directory support, libsecret integration for API keys

### ✅ GTK4 Application Shell
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.3
- **Description**: Main window with sidebar (conversation list) and chat area

### ✅ Setup Dialog
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.4
- **Description**: First-run setup dialog for API key and backend URL

### ✅ Model Selector Integration
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.5
- **Description**: Model dropdown in header, fetch models from API

### ✅ Conversation List and Chat Integration
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.6
- **Description**: Load conversations from API, display in sidebar, send/receive messages

### ✅ Local SQLite Database Caching
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.7
- **Description**: Local cache for conversations and messages for offline support

### ✅ Packaging (Flatpak, AppImage)
- **Completed**: Before v0.1.0
- **Source**: Phase 1, Task 1.8
- **Description**: Flatpak manifest and AppImage build configuration

---

## Phase 2: Enhanced UX (v0.2.0)

### ✅ Theme Support
- **Completed**: 2023 (commits 72ea547, 0a0f648)
- **Source**: Phase 2, Task 2.5
- **Description**: System theme, light, and dark modes with live preview
- **Files**: `src/nanochat/application.py`, `src/nanochat/ui/setup_dialog.py`, `data/styles/style.css`
- **Acceptance Criteria**:
  - [x] Theme selector in settings
  - [x] System theme follows OS preference
  - [x] Light/dark modes work correctly
  - [x] Theme persists across restarts
  - [x] Theme changes apply immediately (live preview)

### ✅ Improved Message Display
- **Completed**: 2023 (commit 72ea547)
- **Source**: Phase 2, Task 2.7
- **Description**: Better markdown rendering and code highlighting
- **Files**: `src/nanochat/ui/message_widget.py`, `data/styles/style.css`
- **Acceptance Criteria**:
  - [x] Bold/italic rendered correctly
  - [x] Code blocks have distinct styling
  - [x] Long code blocks scrollable
  - [ ] Copy button on code blocks (deferred)
  - [ ] Links clickable (deferred)

### ✅ Stop Generation Button
- **Completed**: 2023 (commit 72ea547)
- **Source**: Phase 2, Task 2.8
- **Description**: Send button transforms to stop button during generation
- **Files**: `src/nanochat/ui/window.py`
- **Acceptance Criteria**:
  - [x] Send button becomes stop during generation
  - [x] Clicking stop cancels generation (polling stops)
  - [x] Partial response preserved
  - [x] UI returns to normal state

### ✅ Toast Notifications
- **Completed**: 2023 (commit 1bc4e32)
- **Source**: Phase 2, Task 2.9
- **Description**: Non-intrusive feedback for actions using Adw.Toast
- **Files**: `src/nanochat/ui/window.py`
- **Use Cases**:
  - [x] "Retrieving messages..." (loading state)
  - [x] "Refreshed {count} conversations" (success)
  - [x] "Failed to refresh: {error}" (error)
  - [x] "Failed to load messages: {error}" (error)

### ✅ Smart Caching System
- **Completed**: 2023 (commits 7c0bd96, 4286638, 894083c, 3646a3e)
- **Source**: Phase 2, Bonus 2.1
- **Description**: Instant message loading from cache with deferred API sync (5-minute TTL)
- **Files**: `src/nanochat/ui/window.py`
- **Benefits**:
  - Conversations load instantly from SQLite cache
  - No delay when clicking back to recently viewed conversations
  - API calls only happen when cache is stale (5+ minutes old)
  - Significantly improved perceived performance

### ✅ Manual Refresh Button
- **Completed**: 2023 (commit 1bc4e32)
- **Source**: Phase 2, Bonus 2.2
- **Description**: Manual refresh button in sidebar header that bypasses cache
- **Files**: `src/nanochat/ui/window.py`
- **Acceptance Criteria**:
  - [x] Refresh button in sidebar header
  - [x] Clears cache and forces API sync
  - [x] Shows loading toast
  - [x] Disabled during loading
  - [x] Shows success toast with count

### ✅ Blank Chat Startup
- **Completed**: 2023 (commit 06f8965)
- **Source**: Phase 2, Bonus 2.3
- **Description**: Start app with blank/new chat instead of auto-loading latest conversation
- **Files**: `src/nanochat/ui/window.py`
- **Benefits**:
  - App starts with clean state (no conversation selected)
  - Users can immediately start typing a new message
  - No unwanted API calls on startup
  - More intuitive onboarding experience

---

## Phase 4: Core UX Improvements (v0.4.0)

### ✅ Keyboard Shortcuts
- **Completed**: 2025-01-18 (commit 24539ca)
- **Source**: Pending Tasks, CRITICAL Priority
- **Description**: Comprehensive keyboard shortcuts for power-user productivity
- **Files**: `src/nanochat/application.py`, `src/nanochat/ui/window.py`, `src/nanochat/ui/shortcuts_dialog.py`
- **Implemented Shortcuts**:
  - `Ctrl+N` - New conversation
  - `Ctrl+Q` - Quit application
  - `Ctrl+,` - Open settings
  - `Ctrl+Shift+C` - Copy last assistant response to clipboard
  - `F1` - Show keyboard shortcuts help dialog
  - `Ctrl+K` - Focus search entry
  - `Ctrl+Enter` - Send message
  - `Escape` - Clear search / close dialogs
  - `Up/Down` - Navigate conversations in sidebar
  - `Enter` - Load selected conversation
  - `F2` - Rename conversation (stub for future)
- **Acceptance Criteria**:
  - [x] All global shortcuts work via Gtk.Application actions
  - [x] Window-level shortcuts handled via EventControllerKey
  - [x] Sidebar navigation with arrow keys
  - [x] Shortcuts help dialog displays all shortcuts correctly
  - [x] No conflicts with system shortcuts

### ✅ Conversation Search
- **Completed**: 2025-01-18 (commit 24539ca)
- **Source**: Pending Tasks, CRITICAL Priority
- **Description**: Search entry in sidebar for filtering conversations by title
- **Files**: `src/nanochat/ui/window.py`, `src/nanochat/application.py` (CSS)
- **Features**:
  - Search entry above conversation list
  - 300ms debounce for smooth typing
  - Case-insensitive title filtering
  - Empty state when no matches found
  - `Ctrl+K` focuses search from anywhere
  - `Escape` clears search
  - Preserves full list during filtering
- **Acceptance Criteria**:
  - [x] Search filters conversations correctly
  - [x] Search responds within 400ms of typing stop
  - [x] Empty state shows helpful message
  - [x] Clearing search restores full list
  - [x] Keyboard navigation works in filtered results

### ✅ Flatpak Runtime Update
- **Completed**: 2025-01-18 (commit ca2b579)
- **Source**: GitHub Issue #2
- **Description**: Update Flatpak runtime from GNOME 45 to GNOME 49
- **Files**: `flatpak/com.nanogpt.NanoChat.yml`, `pyproject.toml`
- **Changes**:
  - Updated runtime-version from 45 to 49
  - GNOME 49 is the current stable platform (45 and 47 are EOL)
  - Build successful with Python 3.13 (included in GNOME 49)
  - Version bumped to 0.4.0 in pyproject.toml
- **Acceptance Criteria**:
  - [x] Flatpak manifest uses GNOME 49 runtime
  - [x] No EOL runtime warnings when installing
  - [x] Application builds successfully with new runtime
  - [x] All features work correctly with new runtime
  - [x] Version in pyproject.toml matches git branch (0.4.0)

### ✅ Web Search Toggle and Configuration
- **Completed**: 2026-01-20
- **Source**: Phase 4, Tasks 4.1-4.2 (MEDIUM Priority)
- **Description**: Web search functionality with toggle button and configuration popover
- **Files**:
  - `src/nanochat/ui/web_search_config.py` (new)
  - `src/nanochat/ui/window.py` (modified)
  - `src/nanochat/ui/__init__.py` (modified)
  - `src/nanochat/api/models.py` (modified)
  - `src/nanochat/api/client.py` (modified)
  - `src/nanochat/data/settings.py` (modified)
  - `src/nanochat/application.py` (modified - CSS)
- **Features Implemented**:
  - Toggle button in input area (search icon, left of text entry)
  - Visual feedback when enabled (accent color)
  - Right-click or long-press to open configuration popover
  - Mode selection: Off, Standard (quick), Deep (comprehensive)
  - Provider selection: Tavily (recommended), Linkup, Exa, Kagi
  - Settings persist across app restarts
  - Dynamic tooltip showing current mode when enabled
  - Web search parameters sent to API when enabled
- **Implementation Details**:
  - `WebSearchSettings` model with enabled, mode, provider fields
  - `WebSearchConfigPopover` widget with radio button groups
  - API model updated with `web_search_provider` field
  - API client uses snake_case serialization (`by_alias=False`) to match server expectations
  - Settings integrated into existing `ChatSettings` structure
- **Acceptance Criteria**:
  - [x] Toggle button appears in input area
  - [x] Toggle state persists across restarts
  - [x] Right-click/long-press opens configuration popover
  - [x] Mode and provider selection works
  - [x] Visual feedback (button color, tooltip)
  - [x] Web search parameters included in API requests when enabled
  - [x] Server performs web searches correctly

---

## Completed Bug Fixes & Improvements

### ✅ Conversation Selection Fix
- **Completed**: Before v0.2.0
- **Description**: Fixed conversation selection not loading messages properly
- **Files**: `src/nanochat/ui/window.py`

### ✅ API Client Optimization
- **Completed**: Before v0.1.0 review
- **Description**: Improved polling mechanism, fixed snake_case field handling
- **Files**: `src/nanochat/api/client.py`

---

## Release History

### v0.4.0 - Core UX Improvements (In Development)
**Branch**: v0.4.0
**Completed Features**: 3 tasks
- Keyboard Shortcuts (11 shortcuts implemented)
- Conversation Search (with debounce and empty state)
- Flatpak Runtime Update (GNOME 45 → GNOME 49, version bump to 0.4.0)

### v0.2.0 - Enhanced UX (Released)
**Release Date**: 2023
**Branch**: v0.2.0
**Completed Features**: 4 main tasks + 3 bonus features
- Theme Support (system/light/dark)
- Improved Message Display
- Stop Generation Button
- Toast Notifications
- Smart Caching System (5-minute TTL)
- Manual Refresh Button
- Blank Chat Startup

### v0.1.0 - MVP Core Chat (Released)
**Release Date**: Before v0.2.0
**Branch**: v0.1.0
**Completed Features**: Core chat functionality
- API client with polling
- Settings and secrets management
- GTK4 application shell
- Setup dialog
- Model selector
- Conversation list
- Message send/receive
- SQLite caching
- Flatpak packaging

---

## Summary Statistics

- **Total Completed Items**: 23
- **Phase 1 (v0.1.0)**: 9 tasks
- **Phase 2 (v0.2.0)**: 7 tasks + 3 bonus features + 2 bug fixes
- **Phase 4 (v0.4.0)**: 3 CRITICAL tasks (keyboard shortcuts, search, Flatpak update)
- **Releases**: 2 released (v0.1.0, v0.2.0), 1 in development (v0.4.0)

---

## Development Notes

### Lessons Learned from Phase 2

#### GTK Signal Handling
- `selected-rows-changed` only fires when selection **changes**, not on every click
- Solution: Use `Gtk.GestureClick` on each row instead of list-level signals

#### GTK Auto-Selection Behavior
- Gtk.ListBox automatically selects the first row when rows are added
- `unselect_all()` must be called AFTER GTK processes all events
- Solution: Use `GLib.idle_add()` to defer selection state management

#### Pattern for Row Click Handling
```python
# Add click gesture to each row
click = Gtk.GestureClick()
click.connect("pressed", self._on_row_clicked, conv.id)
row.add_controller(click)

# Handler checks for programmatic updates
def _on_row_clicked(self, gesture, n_press, x, y, conv_id):
    if self._updating_conversation_list:
        return
    self._load_messages(conv_id)
```

#### Flatpak Build Notes
- Flatpak builds run sandboxed with no network by default
- To install Python packages, add `--share=network` build argument
- Don't rebuild PyGObject in Flatpak - it's already in the runtime
- Only install pure Python packages (httpx, pydantic, keyring) via pip

---

## Next Steps

For the next development session, refer to `pending-tasks.md` for the prioritized list of remaining work. The remaining CRITICAL priority items are:

1. Message Copy Button
2. Conversation Renaming (full implementation - currently just a stub)
3. Drag and Drop Attachments

Additional CRITICAL tasks that could be tackled:
- Message Regeneration
- Session Persistence

These should be completed before moving to HIGH priority features like Phase 3 (Assistants and Projects).
