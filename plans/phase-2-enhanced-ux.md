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

### Task 2.5: Theme Support

**Goal**: Support system theme, light, and dark modes

**Files to create/modify:**
- `src/nanochat/data/settings.py` - Add theme setting
- `src/nanochat/application.py` - Apply theme
- `data/styles/style.css` - Custom styles

**Implementation:**

1. Settings for theme:
```python
class UISettings(BaseModel):
    theme: str = "system"  # system, light, dark
```

2. Apply theme in application:
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

3. Add theme selector to settings:
```python
# In SetupDialog
theme_row = Adw.ComboRow()
theme_row.set_title("Theme")
theme_row.set_model(Gtk.StringList.new(["System", "Light", "Dark"]))
```

**Acceptance Criteria:**
- [ ] Theme selector in settings
- [ ] System theme follows OS preference
- [ ] Light/dark modes work correctly
- [ ] Theme persists across restarts

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

### Task 2.7: Improved Message Display

**Goal**: Better markdown rendering and code highlighting

**Implementation:**

1. Use Pango markup for basic formatting:
```python
def markdown_to_pango(text: str) -> str:
    """Convert markdown to Pango markup."""
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # Code inline
    text = re.sub(r"`(.+?)`", r"<tt>\1</tt>", text)
    # Escape special chars
    text = GLib.markup_escape_text(text)
    return text
```

2. Code blocks with monospace font:
```python
def create_code_block(code: str, language: str) -> Gtk.Widget:
    frame = Gtk.Frame()
    frame.add_css_class("code-block")
    
    view = Gtk.TextView()
    view.set_editable(False)
    view.set_monospace(True)
    view.get_buffer().set_text(code)
    
    # Copy button
    copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
    copy_btn.connect("clicked", lambda _: copy_to_clipboard(code))
    
    frame.set_child(view)
    return frame
```

3. CSS for code blocks:
```css
.code-block {
    background-color: @view_bg_color;
    border-radius: 6px;
    padding: 8px;
    font-family: monospace;
}
```

**Acceptance Criteria:**
- [ ] Bold/italic rendered correctly
- [ ] Code blocks have distinct styling
- [ ] Copy button on code blocks
- [ ] Long code blocks scrollable
- [ ] Links clickable (opens browser)

---

### Task 2.8: Stop Generation Button

**Goal**: Allow canceling ongoing generation

**Implementation:**

1. Track generation state:
```python
class ChatState:
    is_generating: bool = False
    current_task: Optional[asyncio.Task] = None
```

2. Show stop button during generation:
```python
def _update_send_button(self, generating: bool):
    if generating:
        self.send_btn.set_icon_name("media-playback-stop-symbolic")
        self.send_btn.set_tooltip_text("Stop generating")
    else:
        self.send_btn.set_icon_name("mail-send-symbolic")
        self.send_btn.set_tooltip_text("Send message")
```

3. Cancel generation:
```python
async def _on_stop_generation(self):
    if self._state.current_task:
        self._state.current_task.cancel()
        # Also call cancel API
        await self._api_client.cancel_generation(
            conversation_id=self._current_conversation_id
        )
```

**Acceptance Criteria:**
- [ ] Send button becomes stop during generation
- [ ] Clicking stop cancels generation
- [ ] Partial response preserved
- [ ] UI returns to normal state

---

### Task 2.9: Toast Notifications

**Goal**: Show non-intrusive feedback for actions

**Implementation:**

Use Libadwaita's toast:
```python
def _show_toast(self, message: str, timeout: int = 2):
    toast = Adw.Toast.new(message)
    toast.set_timeout(timeout)
    self._toast_overlay.add_toast(toast)
```

**Use cases:**
- "Message copied to clipboard"
- "Conversation deleted"
- "Connection lost"
- "Settings saved"

**Acceptance Criteria:**
- [ ] Toasts appear for key actions
- [ ] Auto-dismiss after timeout
- [ ] Can dismiss manually
- [ ] Don't stack excessively

---

## Definition of Done - Phase 2

- [ ] All tasks completed
- [ ] Manual testing checklist:
  - [ ] Search finds conversations
  - [ ] Rename works
  - [ ] Copy message works
  - [ ] All keyboard shortcuts work
  - [ ] Theme switching works
  - [ ] Stop generation works
  - [ ] Toasts appear appropriately
- [ ] Code reviewed
- [ ] Branch merged and tagged as `v0.2.0`
- [ ] Release created with binaries

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
# - nanochat-v0.2.0.flatpak
# - nanochat-v0.2.0-x86_64.AppImage
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
