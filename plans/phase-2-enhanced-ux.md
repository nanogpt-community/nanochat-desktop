# Phase 2: Enhanced UX

**Version**: v0.2.0  
**Branch**: `v0.2.0`  
**Prerequisites**: Phase 1 complete (v0.1.0)

---

## Overview

Phase 2 focuses on improving the user experience with search functionality, keyboard shortcuts, theming, and quality-of-life features that make daily use more pleasant.

---

## Pre-Phase Tasks

### Human Tasks

1. **Create branch from v0.1.0**
   ```bash
   git checkout v0.1.0
   git checkout -b v0.2.0
   git push -u origin v0.2.0
   ```

2. **Gather feedback from Phase 1 usage**
   - Note any bugs or usability issues
   - Create issues for known problems

---

## Implementation Tasks

### Task 2.1: Conversation Search

**Goal**: Allow users to search through their conversations

**API Endpoint**: 
```
GET /api/db/conversations?search=term&mode=fuzzy
```

**Files to modify/create:**
- `src/nanochat/ui/window.py` - Add search entry to sidebar
- `src/nanochat/api/client.py` - Add search parameter

**Implementation:**

1. Add search entry above conversation list:
```python
# In _create_sidebar()
search_entry = Gtk.SearchEntry()
search_entry.set_placeholder_text("Search conversations...")
search_entry.connect("search-changed", self._on_search_changed)
# Add with 300ms debounce
```

2. Update API client:
```python
async def get_conversations(
    self, 
    project_id: Optional[str] = None,
    search: Optional[str] = None,
    mode: str = "fuzzy"  # exact, words, fuzzy
) -> list[Conversation]:
    params = {}
    if project_id:
        params["projectId"] = project_id
    if search:
        params["search"] = search
        params["mode"] = mode
    data = await self._request("GET", "/api/db/conversations", params=params)
    return [Conversation.model_validate(c) for c in data]
```

3. Implement debounced search:
```python
def _on_search_changed(self, entry):
    # Cancel previous search
    if hasattr(self, "_search_timeout"):
        GLib.source_remove(self._search_timeout)
    
    # Schedule new search after 300ms
    self._search_timeout = GLib.timeout_add(
        300, 
        self._perform_search, 
        entry.get_text()
    )
```

**Acceptance Criteria:**
- [ ] Search entry appears in sidebar
- [ ] Typing filters conversations
- [ ] Search is debounced (300ms)
- [ ] Empty search shows all conversations
- [ ] Search works offline with cached data

---

### Task 2.2: Conversation Renaming

**Goal**: Allow users to rename conversations

**API Endpoint**:
```
POST /api/db/conversations
{
  "action": "updateTitle",
  "conversationId": "string",
  "title": "string"
}
```

**Implementation:**

1. Add rename action to conversation context menu
2. Show inline entry or dialog for new title
3. Update API and local cache

```python
# Context menu for conversation row
def _on_conversation_right_click(self, gesture, n_press, x, y):
    menu = Gio.Menu()
    menu.append("Rename", f"win.rename-conversation::{conv_id}")
    menu.append("Delete", f"win.delete-conversation::{conv_id}")
    
    popover = Gtk.PopoverMenu.new_from_model(menu)
    popover.set_parent(gesture.get_widget())
    popover.popup()
```

**Acceptance Criteria:**
- [ ] Right-click shows context menu
- [ ] Rename option opens title editor
- [ ] New title saved to server
- [ ] UI updates immediately
- [ ] Cancel reverts to original title

---

### Task 2.3: Message Actions

**Goal**: Copy message content, potentially edit user messages

**Implementation:**

1. Add copy button to message widgets:
```python
class MessageWidget(Gtk.Box):
    def _setup_actions(self):
        # Copy button (appears on hover)
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_btn.set_tooltip_text("Copy to clipboard")
        copy_btn.connect("clicked", self._on_copy)
        copy_btn.add_css_class("flat")
        self._action_box.append(copy_btn)
    
    def _on_copy(self, button):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self._content)
```

2. Add hover reveal for action buttons:
```css
/* style.css */
.message-actions {
    opacity: 0;
    transition: opacity 200ms;
}

.message-row:hover .message-actions {
    opacity: 1;
}
```

**Acceptance Criteria:**
- [ ] Copy button appears on hover
- [ ] Clicking copies content to clipboard
- [ ] Toast notification confirms copy
- [ ] Works for both user and assistant messages

---

### Task 2.4: Comprehensive Keyboard Shortcuts

**Goal**: Enable efficient keyboard-driven usage

**Shortcuts to implement:**

| Shortcut | Action | Scope |
|----------|--------|-------|
| `Ctrl+N` | New conversation | Global |
| `Ctrl+Q` | Quit | Global |
| `Ctrl+,` | Settings | Global |
| `Ctrl+K` | Focus search | Sidebar |
| `Escape` | Cancel/close | Various |
| `Ctrl+Enter` | Send message | Chat input |
| `Up/Down` | Navigate conversations | Sidebar |
| `Ctrl+Shift+C` | Copy last response | Chat |
| `F2` | Rename conversation | Sidebar |

**Implementation:**

1. Add actions in `application.py`:
```python
def _setup_actions(self):
    # ... existing actions ...
    
    # Focus search
    search_action = Gio.SimpleAction.new("focus-search", None)
    search_action.connect("activate", self._on_focus_search)
    self.add_action(search_action)
    self.set_accels_for_action("app.focus-search", ["<Control>k"])
```

2. Add window-level keyboard controller:
```python
def _setup_keyboard(self):
    controller = Gtk.EventControllerKey()
    controller.connect("key-pressed", self._on_key_pressed)
    self.add_controller(controller)

def _on_key_pressed(self, controller, keyval, keycode, state):
    # Handle Escape
    if keyval == Gdk.KEY_Escape:
        # Close dialog, cancel edit, etc.
        return True
    return False
```

**Acceptance Criteria:**
- [ ] All shortcuts work as specified
- [ ] Shortcuts shown in menus/tooltips
- [ ] No conflicts with system shortcuts
- [ ] Escape cancels current operation

---

### Task 2.5: Theme Support ✅ **COMPLETED**

**Implemented in**: 72ea547, 0a0f648

**Goal**: Support system theme, light, and dark modes

**Files created/modified:**
- `src/nanochat/application.py` - Apply theme with `_apply_theme()` and `_load_css()`
- `src/nanochat/ui/setup_dialog.py` - Theme selector with live preview
- `src/nanochat/ui/message_widget.py` - CSS-styled messages
- `data/styles/style.css` - Custom stylesheet

**Implementation:**

1. Settings for theme in `UISettings` model:
```python
class UISettings(BaseModel):
    theme: str = "system"  # system, light, dark
```

2. Apply theme in application (live preview):
```python
def _apply_theme(self):
    manager = Adw.StyleManager.get_default()
    theme = self.settings_manager.settings.ui.theme

    if theme == "system":
        manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
    elif theme == "light":
        manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    elif theme == "dark":
        manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
```

3. Theme selector with live update in SetupDialog:
```python
theme_row = Adw.ComboRow()
theme_row.set_title("Theme")
theme_row.set_model(Gtk.StringList.new(["System", "Light", "Dark"]))
theme_row.connect("notify::selected-item", self._on_theme_changed)
```

**Acceptance Criteria:**
- [x] Theme selector in settings
- [x] System theme follows OS preference
- [x] Light/dark modes work correctly
- [x] Theme persists across restarts
- [x] **BONUS**: Theme changes apply immediately (live preview)

---

### Task 2.6: System Tray Integration

**Goal**: Allow app to minimize to system tray (optional feature)

**Note**: This is a lower priority feature as tray support varies by DE. Implement if time allows.

**Implementation options:**
- Use `Gtk.StatusIcon` (deprecated but works)
- Use `AppIndicator3` (Ubuntu/GNOME)
- Skip for KDE (background apps handled differently)

**Basic implementation:**
```python
# Optional tray support
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
    HAS_TRAY = True
except:
    HAS_TRAY = False

if HAS_TRAY:
    indicator = AppIndicator3.Indicator.new(
        "nanochat",
        "com.nanogpt.NanoChat",
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
```

**Acceptance Criteria:**
- [ ] Tray icon appears (where supported)
- [ ] Click shows/hides window
- [ ] Right-click shows menu with quit option
- [ ] Graceful fallback where not supported

---

### Task 2.7: Improved Message Display ✅ **COMPLETED**

**Implemented in**: 72ea547

**Goal**: Better markdown rendering and code highlighting

**Files modified:**
- `src/nanochat/ui/message_widget.py` - Redesigned with improved styling
- `data/styles/style.css` - CSS for message styling

**Implementation:**

1. Basic markdown rendering in `MessageWidget`:
```python
def _parse_content(self, content: str) -> None:
    """Parse markdown content and add widgets."""
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('```'):
            # Code block
            self._add_code_block(line)
        elif '`' in line:
            # Inline code
            self._add_inline_code(line)
        else:
            # Regular text with bold/italic
            self._add_formatted_text(line)
```

2. CSS styling for messages:
```css
/* Applied via MessageWidget.add_css_class() */
.message-user {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
    border-radius: 12px;
    padding: 12px;
}

.message-assistant {
    background-color: @card_bg_color;
    border-radius: 12px;
    padding: 12px;
}

.code-block {
    background-color: @view_bg_color;
    border-radius: 6px;
    padding: 8px;
    font-family: monospace;
}
```

**Acceptance Criteria:**
- [x] Bold/italic rendered correctly
- [x] Code blocks have distinct styling
- [ ] Copy button on code blocks (deferred to future phase)
- [x] Long code blocks scrollable
- [ ] Links clickable (opens browser) (deferred to future phase)

---

### Task 2.8: Stop Generation Button ✅ **COMPLETED**

**Implemented in**: 72ea547

**Goal**: Allow canceling ongoing generation

**Implementation:**

1. Send button transforms during generation in `window.py`:
```python
def _set_generating(self, generating: bool) -> None:
    """Update UI state for generation."""
    self._generating = generating
    if generating:
        self._send_button.set_icon_name("media-playback-stop-symbolic")
        self._send_button.set_tooltip_text("Stop generating")
        self._send_button.add_css_class("destructive-action")
    else:
        self._send_button.set_icon_name("mail-send-symbolic")
        self._send_button.set_tooltip_text("Send message")
        self._send_button.remove_css_class("destructive-action")
```

2. Stop button handler in CSS:
```css
button.stop-generating {
    background-color: @error_bg_color;
    color: @error_fg_color;
}
```

**Acceptance Criteria:**
- [x] Send button becomes stop during generation
- [x] Clicking stop cancels generation (polling stops)
- [x] Partial response preserved
- [x] UI returns to normal state

---

### Task 2.9: Toast Notifications ✅ **COMPLETED**

**Implemented in**: 1bc4e32

**Goal**: Show non-intrusive feedback for actions

**Files modified:**
- `src/nanochat/ui/window.py` - Added `_show_toast()` method, `Adw.ToastOverlay`

**Implementation:**

Use Libadwaita's toast in `window.py`:
```python
def _show_toast(self, message: str, timeout: float = 2.0) -> None:
    """Show a toast notification."""
    toast = Adw.Toast.new(message)
    toast.set_timeout(timeout)
    self._toast_overlay.add_toast(toast)
```

**Use cases implemented:**
- [x] "Retrieving messages..." (loading state)
- [x] "Refreshed {count} conversations" (success)
- [x] "Failed to refresh: {error}" (error)
- [x] "Failed to load messages: {error}" (error)

**Acceptance Criteria:**
- [x] Toasts appear for key actions
- [x] Auto-dismiss after timeout
- [x] Can dismiss manually
- [x] Don't stack excessively

---

## Bonus Features (Not in Original Plan)

### Bonus 2.1: Smart Caching System ✅ **COMPLETED**

**Implemented in**: 7c0bd96, 4286638, 894083c, 3646a3e

**Goal**: Instant message loading from cache with deferred API sync

**Files modified:**
- `src/nanochat/ui/window.py` - Added cache tracking, freshness checks

**Implementation:**

1. Cache freshness tracking (5-minute TTL):
```python
class NanoChatWindow(Adw.ApplicationWindow):
    def __init__(self, ...):
        self._conversation_fetch_time: dict[str, float] = {}
        self._cache_stale_seconds = 300  # 5 minutes
```

2. Instant cache load with deferred API sync:
```python
async def _on_conversation_selected(self, row):
    # Load from cache immediately for instant display
    local_messages = await self._db.get_messages(conversation_id)
    if local_messages:
        self._update_messages_list(local_messages, from_cache=True)

    # Then sync with API in background if cache is stale
    if self._is_cache_stale(conversation_id):
        await self._sync_conversation_from_api(conversation_id)
```

3. Cache comparison to avoid unnecessary UI updates:
```python
def _messages_equal(self, a: list[Message], b: list[Message]) -> bool:
    """Compare two message lists for equality."""
    if len(a) != len(b):
        return False
    return all(
        ma.id == mb.id and ma.content == mb.content
        for ma, mb in zip(a, b)
    )
```

**Benefits:**
- Conversations load instantly from SQLite cache
- No delay when clicking back to recently viewed conversations
- API calls only happen when cache is stale (5+ minutes old)
- Significantly improved perceived performance

---

### Bonus 2.2: Manual Refresh Button ✅ **COMPLETED**

**Implemented in**: 1bc4e32

**Goal**: Allow users to manually trigger conversation list refresh

**Files modified:**
- `src/nanochat/ui/window.py` - Added refresh button to sidebar

**Implementation:**

Refresh button in sidebar header:
```python
def _create_sidebar(self) -> None:
    header = Adw.HeaderBar()
    self._refresh_button = Gtk.Button(icon_name="view-refresh-symbolic")
    self._refresh_button.set_tooltip_text("Refresh conversations")
    self._refresh_button.connect("clicked", self._on_refresh_clicked)
    header.pack_start(self._refresh_button)
```

Force refresh that bypasses cache:
```python
async def _on_refresh_clicked(self, button):
    """Manually refresh conversations from API."""
    self._refresh_button.set_sensitive(False)
    self._show_toast("Retrieving conversations...")

    # Clear cache timestamps to force refresh
    self._conversation_fetch_time.clear()

    await self._load_conversations(force_refresh=True)
```

**Acceptance Criteria:**
- [x] Refresh button in sidebar header
- [x] Clears cache and forces API sync
- [x] Shows loading toast
- [x] Disabled during loading
- [x] Shows success toast with count

---

### Bonus 2.3: Blank Chat Startup ✅ **COMPLETED**

**Implemented in**: 06f8965

**Goal**: Start app with blank/new chat instead of auto-loading latest conversation

**Files modified:**
- `src/nanochat/ui/window.py` - Fixed auto-selection behavior

**Implementation:**

Prevent GTK's auto-selection on startup:
```python
def _on_conversation_selected(self, list_box, row):
    if row is None:
        return

    conversation_id = row.conversation_id

    # Prevent auto-loading on startup - if we haven't selected anything yet,
    # and GTK auto-selects the first row, immediately unselect it
    if self._current_conversation_id is None:
        self._conversation_list.unselect_all()
        self._current_conversation_id = None
        return

    # Normal selection handling...
```

**Benefits:**
- App starts with clean state (no conversation selected)
- Users can immediately start typing a new message
- No unwanted API calls on startup
- More intuitive onboarding experience

---

## Definition of Done - Phase 2

### Completed Tasks ✅
- [x] Task 2.5: Theme Support
- [x] Task 2.7: Improved Message Display
- [x] Task 2.8: Stop Generation Button
- [x] Task 2.9: Toast Notifications
- [x] Bonus 2.1: Smart Caching System
- [x] Bonus 2.2: Manual Refresh Button
- [x] Bonus 2.3: Blank Chat Startup

### Remaining Tasks
*All remaining Phase 2 tasks have been moved to Phase 3 to finalize this release.*

**Moved to Phase 3:**
- Task 2.1: Conversation Search → Task 3.10
- Task 2.2: Conversation Renaming → Task 3.11
- Task 2.3: Message Actions (Copy button) → Task 3.12
- Task 2.4: Keyboard Shortcuts → Task 3.13
- Task 2.6: System Tray Integration → Task 3.14 (lower priority)

### Manual Testing Checklist
- [ ] Theme switching works (system/light/dark)
- [ ] Messages render with basic markdown (bold, italic, code blocks)
- [ ] Stop button appears during generation and stops it
- [ ] Toast notifications appear for refresh/load operations
- [ ] Conversations load instantly from cache (5-minute TTL)
- [ ] Refresh button forces conversation list reload
- [ ] App starts with blank/new chat state

### Release Status
**Current**: ✅ **READY FOR RELEASE** (v0.2.0 branch)
**Completed Features**: 4 main tasks + 3 bonus features
**All remaining tasks moved to Phase 3**

---

## Release Checklist

```bash
# Update version in pyproject.toml to 0.2.0
# Update version in __init__.py to "0.2.0"

# Build and test
flatpak-builder --user --install build flatpak/com.nanogpt.NanoChat.yml
flatpak run com.nanogpt.NanoChat  # Test

# Export packages
flatpak build-bundle ~/.local/share/flatpak/repo \
    nanochat-v0.2.0.flatpak com.nanogpt.NanoChat

# Tag and release
git checkout v0.2.0
git tag -a v0.2.0 -m "Release v0.2.0 - Enhanced UX"
git push origin v0.2.0 --tags

# Create GitHub release with:
# - com.nanogpt.NanoChat-0.2.0.flatpak
# - Changelog highlighting new features
```

---

## Notes for LLM

When implementing Phase 2:

1. **Search debouncing** is critical - don't spam the API
2. **Theme changes** should be instant, no restart required
3. **Keyboard shortcuts** must not conflict with system shortcuts
4. **Toast messages** should be brief and informative
5. **Always test** with both cached and fresh data
