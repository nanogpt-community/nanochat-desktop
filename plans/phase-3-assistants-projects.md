# Phase 3: Assistants and Projects

**Version**: v0.3.0  
**Branch**: `v0.3.0`  
**Prerequisites**: Phase 2 complete (v0.2.0)

---

## Overview

Phase 3 adds organization features - Assistants (custom AI personas with system prompts) and Projects (conversation folders). These features help users organize their work and customize AI behavior.

---

## Pre-Phase Tasks

### Human Tasks

1. **Create branch from v0.2.0**
   ```bash
   git checkout v0.2.0
   git checkout -b v0.3.0
   git push -u origin v0.3.0
   ```

---

## API Reference

### Assistants API

```
GET    /api/assistants               - List all assistants
POST   /api/assistants               - Create assistant
PATCH  /api/assistants/:id           - Update assistant
DELETE /api/assistants/:id           - Delete assistant
POST   /api/assistants/:id           - Set as default (action: setDefault)
```

**Assistant Object:**
```json
{
  "id": "string",
  "name": "string",
  "description": "string | null",
  "systemPrompt": "string",
  "isDefault": "boolean",
  "defaultModelId": "string | null",
  "defaultWebSearchMode": "string | null",
  "icon": "string | null",
  "temperature": "number | null",
  "topP": "number | null",
  "maxTokens": "number | null",
  "contextSize": "number | null",
  "reasoningEffort": "string | null",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Projects API

```
GET    /api/projects                 - List projects
POST   /api/projects                 - Create project
GET    /api/projects/:id             - Get project with details
PATCH  /api/projects/:id             - Update project
DELETE /api/projects/:id             - Delete project
```

**Project Object:**
```json
{
  "id": "string",
  "name": "string",
  "description": "string | null",
  "systemPrompt": "string | null",
  "color": "string | null",
  "role": "owner | editor | viewer",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Move Conversation to Project

```
POST /api/db/conversations
{
  "action": "setProject",
  "conversationId": "string",
  "projectId": "string | null"
}
```

---

## Implementation Tasks

### Task 3.1: API Models for Assistants and Projects

**Files to modify:**
- `src/nanochat/api/models.py`

```python
# Add to models.py

class Assistant(BaseModel):
    """Assistant/persona configuration."""
    id: str
    name: str
    description: Optional[str] = None
    system_prompt: str = Field(alias="systemPrompt")
    is_default: bool = Field(default=False, alias="isDefault")
    default_model_id: Optional[str] = Field(default=None, alias="defaultModelId")
    default_web_search_mode: Optional[str] = Field(default=None, alias="defaultWebSearchMode")
    icon: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = Field(default=None, alias="topP")
    max_tokens: Optional[int] = Field(default=None, alias="maxTokens")
    context_size: Optional[int] = Field(default=None, alias="contextSize")
    reasoning_effort: Optional[str] = Field(default=None, alias="reasoningEffort")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class CreateAssistantRequest(BaseModel):
    """Request to create an assistant."""
    name: str
    description: Optional[str] = None
    system_prompt: str = Field(alias="systemPrompt")
    default_model_id: Optional[str] = Field(default=None, alias="defaultModelId")
    default_web_search_mode: Optional[str] = Field(default=None, alias="defaultWebSearchMode")
    icon: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = Field(default=None, alias="topP")
    max_tokens: Optional[int] = Field(default=None, alias="maxTokens")
    context_size: Optional[int] = Field(default=None, alias="contextSize")
    reasoning_effort: Optional[str] = Field(default=None, alias="reasoningEffort")

    class Config:
        populate_by_name = True


class UpdateAssistantRequest(BaseModel):
    """Request to update an assistant."""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    default_model_id: Optional[str] = Field(default=None, alias="defaultModelId")
    default_web_search_mode: Optional[str] = Field(default=None, alias="defaultWebSearchMode")
    icon: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = Field(default=None, alias="topP")
    max_tokens: Optional[int] = Field(default=None, alias="maxTokens")
    context_size: Optional[int] = Field(default=None, alias="contextSize")
    reasoning_effort: Optional[str] = Field(default=None, alias="reasoningEffort")

    class Config:
        populate_by_name = True


class Project(BaseModel):
    """Project/folder for organizing conversations."""
    id: str
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    color: Optional[str] = None
    role: str = "owner"
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class CreateProjectRequest(BaseModel):
    """Request to create a project."""
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    color: Optional[str] = None

    class Config:
        populate_by_name = True


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    color: Optional[str] = None

    class Config:
        populate_by_name = True
```

**Acceptance Criteria:**
- [ ] All models defined with proper field aliases
- [ ] Models validate API responses correctly

---

### Task 3.2: API Client Methods for Assistants

**Files to modify:**
- `src/nanochat/api/client.py`

```python
# Add to NanoChatClient class

# Assistants
async def get_assistants(self) -> list[Assistant]:
    """Get all assistants."""
    data = await self._request("GET", "/api/assistants")
    return [Assistant.model_validate(a) for a in data]

async def create_assistant(self, request: CreateAssistantRequest) -> Assistant:
    """Create a new assistant."""
    data = await self._request(
        "POST", "/api/assistants",
        json=request.model_dump(exclude_none=True, by_alias=True)
    )
    return Assistant.model_validate(data)

async def update_assistant(self, assistant_id: str, request: UpdateAssistantRequest) -> Assistant:
    """Update an assistant."""
    data = await self._request(
        "PATCH", f"/api/assistants/{assistant_id}",
        json=request.model_dump(exclude_none=True, by_alias=True)
    )
    return Assistant.model_validate(data)

async def delete_assistant(self, assistant_id: str) -> None:
    """Delete an assistant."""
    await self._request("DELETE", f"/api/assistants/{assistant_id}")

async def set_default_assistant(self, assistant_id: str) -> None:
    """Set an assistant as the default."""
    await self._request(
        "POST", f"/api/assistants/{assistant_id}",
        json={"action": "setDefault"}
    )
```

**Acceptance Criteria:**
- [ ] Can list assistants
- [ ] Can create assistant
- [ ] Can update assistant
- [ ] Can delete assistant
- [ ] Can set default assistant

---

### Task 3.3: API Client Methods for Projects

```python
# Add to NanoChatClient class

# Projects
async def get_projects(self) -> list[Project]:
    """Get all projects."""
    data = await self._request("GET", "/api/projects")
    return [Project.model_validate(p) for p in data]

async def get_project(self, project_id: str) -> Project:
    """Get a single project."""
    data = await self._request("GET", f"/api/projects/{project_id}")
    return Project.model_validate(data)

async def create_project(self, request: CreateProjectRequest) -> Project:
    """Create a new project."""
    data = await self._request(
        "POST", "/api/projects",
        json=request.model_dump(exclude_none=True, by_alias=True)
    )
    return Project.model_validate(data)

async def update_project(self, project_id: str, request: UpdateProjectRequest) -> Project:
    """Update a project."""
    data = await self._request(
        "PATCH", f"/api/projects/{project_id}",
        json=request.model_dump(exclude_none=True, by_alias=True)
    )
    return Project.model_validate(data)

async def delete_project(self, project_id: str) -> None:
    """Delete a project."""
    await self._request("DELETE", f"/api/projects/{project_id}")

async def move_conversation_to_project(
    self, 
    conversation_id: str, 
    project_id: Optional[str]
) -> None:
    """Move a conversation to a project (or remove from project if None)."""
    await self._request(
        "POST", "/api/db/conversations",
        json={
            "action": "setProject",
            "conversationId": conversation_id,
            "projectId": project_id
        }
    )
```

**Acceptance Criteria:**
- [ ] Can list projects
- [ ] Can create project
- [ ] Can update project
- [ ] Can delete project
- [ ] Can move conversation to project

---

### Task 3.4: Assistants Management UI

**Files to create:**
- `src/nanochat/ui/assistants_dialog.py`

**Design:**
```
┌──────────────────────────────────────────────────┐
│  Assistants                              [+ New] │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 🤖 Default Assistant              [Default]│  │
│  │    General-purpose AI assistant            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 💻 Code Helper                             │  │
│  │    Specialized in programming tasks        │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ ✍️ Writing Assistant                       │  │
│  │    Helps with writing and editing          │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Implementation:**

```python
class AssistantsDialog(Adw.PreferencesWindow):
    """Dialog for managing assistants."""
    
    def __init__(self, parent):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Assistants")
        self.set_default_size(600, 500)
        
        self._setup_ui()
        self._load_assistants()
    
    def _setup_ui(self):
        page = Adw.PreferencesPage()
        self.add(page)
        
        # Assistants group
        self.assistants_group = Adw.PreferencesGroup()
        self.assistants_group.set_title("Your Assistants")
        
        # Add button in header
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.connect("clicked", self._on_add_assistant)
        self.assistants_group.set_header_suffix(add_btn)
        
        page.add(self.assistants_group)
    
    def _create_assistant_row(self, assistant: Assistant) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(assistant.name)
        row.set_subtitle(assistant.description or "")
        
        # Icon
        if assistant.icon:
            row.add_prefix(Gtk.Label(label=assistant.icon))
        
        # Default badge
        if assistant.is_default:
            badge = Gtk.Label(label="Default")
            badge.add_css_class("dim-label")
            row.add_suffix(badge)
        
        # Edit button
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.add_css_class("flat")
        edit_btn.connect("clicked", lambda _: self._edit_assistant(assistant))
        row.add_suffix(edit_btn)
        
        # Delete button (if not default)
        if not assistant.is_default:
            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.connect("clicked", lambda _: self._delete_assistant(assistant))
            row.add_suffix(del_btn)
        
        row.set_activatable(True)
        row.connect("activated", lambda _: self._edit_assistant(assistant))
        
        return row
```

**Also create:** `src/nanochat/ui/assistant_editor.py` - Dialog for editing assistant details

**Acceptance Criteria:**
- [ ] Assistants list shows all assistants
- [ ] Can create new assistant
- [ ] Can edit assistant (name, description, system prompt)
- [ ] Can delete assistant (except default)
- [ ] Can set assistant as default
- [ ] Changes sync to server

---

### Task 3.5: Projects Management UI

**Files to create:**
- `src/nanochat/ui/projects_dialog.py`

Similar structure to AssistantsDialog but for projects.

**Acceptance Criteria:**
- [ ] Projects list shows all projects
- [ ] Can create new project
- [ ] Can edit project
- [ ] Can delete project
- [ ] Project color displayed as badge/indicator

---

### Task 3.6: Assistant Selector in Chat

**Goal**: Allow selecting an assistant when starting a new conversation

**Implementation:**

1. Add assistant dropdown next to model selector:
```python
# In window.py _create_content()
self.assistant_selector = Gtk.DropDown()
self.assistant_selector.set_tooltip_text("Select Assistant")
# Add to header bar
```

2. Load assistants:
```python
def _load_assistants(self):
    # Similar pattern to _load_models()
    # Include "No Assistant" option at top
    pass
```

3. Use selected assistant in message generation:
```python
async def _send_message(self, text: str):
    request = GenerateMessageRequest(
        message=text,
        model_id=self._get_selected_model_id(),
        assistant_id=self._get_selected_assistant_id(),  # New
        conversation_id=self._current_conversation_id
    )
    # ... rest of send logic
```

**Acceptance Criteria:**
- [ ] Assistant dropdown appears in header
- [ ] Can select different assistants
- [ ] New conversations use selected assistant
- [ ] "No Assistant" option available

---

### Task 3.7: Project Filter in Sidebar

**Goal**: Filter conversations by project

**Implementation:**

1. Add project filter dropdown at top of sidebar:
```python
# In _create_sidebar()
self.project_filter = Gtk.DropDown()
self.project_filter.set_tooltip_text("Filter by Project")
self.project_filter.connect("notify::selected", self._on_project_filter_changed)
# Insert before search entry
```

2. Filter options:
- "All Conversations"
- "No Project"
- [List of projects with colors]

3. Update conversation loading:
```python
def _on_project_filter_changed(self, dropdown, pspec):
    selected = dropdown.get_selected()
    if selected == 0:
        project_id = None  # All
    elif selected == 1:
        project_id = "null"  # No project
    else:
        project_id = self._project_ids[selected - 2]
    
    self._load_conversations(project_id=project_id)
```

**Acceptance Criteria:**
- [ ] Project filter dropdown in sidebar
- [ ] "All Conversations" shows everything
- [ ] "No Project" shows unassigned conversations
- [ ] Project selection filters correctly
- [ ] Projects show their color

---

### Task 3.8: Move Conversation to Project

**Goal**: Allow moving conversations between projects

**Implementation:**

1. Add "Move to Project" option in conversation context menu:
```python
def _create_conversation_menu(self, conv_id: str) -> Gio.Menu:
    menu = Gio.Menu()
    menu.append("Rename", f"win.rename-conversation::{conv_id}")
    
    # Move to project submenu
    project_menu = Gio.Menu()
    project_menu.append("No Project", f"win.move-to-project::{conv_id}::null")
    for project in self._projects:
        project_menu.append(
            project.name, 
            f"win.move-to-project::{conv_id}::{project.id}"
        )
    menu.append_submenu("Move to Project", project_menu)
    
    menu.append("Delete", f"win.delete-conversation::{conv_id}")
    return menu
```

2. Handle action:
```python
def _on_move_to_project(self, action, param):
    parts = param.get_string().split("::")
    conv_id = parts[0]
    project_id = parts[1] if parts[1] != "null" else None
    
    # Run async move
    self._run_async(self._move_conversation(conv_id, project_id))

async def _move_conversation(self, conv_id: str, project_id: Optional[str]):
    await self._api_client.move_conversation_to_project(conv_id, project_id)
    self._show_toast("Conversation moved")
    self._reload_conversations()
```

**Acceptance Criteria:**
- [ ] "Move to Project" submenu in context menu
- [ ] Lists all projects plus "No Project"
- [ ] Moving updates server and local state
- [ ] Toast confirms action

---

### Task 3.9: Database Caching for Assistants/Projects

**Files to modify:**
- `src/nanochat/data/database.py`

Add tables for caching assistants and projects:

```python
def _create_tables(self):
    # ... existing tables ...
    
    self._conn.execute("""
        CREATE TABLE IF NOT EXISTS assistants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            system_prompt TEXT NOT NULL,
            is_default INTEGER,
            default_model_id TEXT,
            icon TEXT,
            created_at TEXT,
            updated_at TEXT,
            synced_at TEXT
        )
    """)
    
    self._conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            system_prompt TEXT,
            color TEXT,
            role TEXT,
            created_at TEXT,
            updated_at TEXT,
            synced_at TEXT
        )
    """)
```

**Acceptance Criteria:**
- [ ] Assistants cached locally
- [ ] Projects cached locally
- [ ] Works offline with cached data
- [ ] Syncs when online

---

## Tasks Migrated from Phase 2

### Task 3.10: Conversation Search *(migrated from Task 2.1)*

**Goal**: Allow users to search through their conversations

**API Endpoint**:
```
GET /api/db/conversations?search=term&mode=fuzzy
```

**Files to modify:**
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

### Task 3.11: Conversation Renaming *(migrated from Task 2.2)*

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

### Task 3.12: Message Actions *(migrated from Task 2.3)*

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

### Task 3.13: Keyboard Shortcuts *(migrated from Task 2.4)*

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

### Task 3.14: System Tray Integration *(migrated from Task 2.6, lower priority)*

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

## Definition of Done - Phase 3

- [ ] All tasks completed (Tasks 3.1-3.9 + Migrated Tasks 3.10-3.14)
- [ ] Manual testing checklist:
  - [ ] Can list assistants
  - [ ] Can create/edit/delete assistants
  - [ ] Default assistant works
  - [ ] Can select assistant for chat
  - [ ] Can list projects
  - [ ] Can create/edit/delete projects
  - [ ] Can filter by project
  - [ ] Can move conversations to projects
  - [ ] Offline mode works with cached data
  - [ ] Search finds conversations
  - [ ] Rename works
  - [ ] Copy message works
  - [ ] All keyboard shortcuts work
- [ ] Code reviewed
- [ ] Branch merged and tagged as `v0.3.0`
- [ ] Release created with binaries

---

## Release Checklist

```bash
# Update version to 0.3.0
git checkout v0.3.0
git tag -a v0.3.0 -m "Release v0.3.0 - Assistants and Projects"
git push origin v0.3.0 --tags

# Build packages and create GitHub release
```

---

## Notes for LLM

When implementing Phase 3:

1. **Assistants affect message generation** - ensure assistant_id is passed correctly
2. **Projects are organizational** - they don't affect AI behavior directly
3. **Default assistant** - there should always be one default
4. **Project colors** - use consistent color representation (hex string)
5. **Caching** - sync strategy: load cached, fetch fresh, update cache
6. **Error handling** - graceful fallback if API fails
