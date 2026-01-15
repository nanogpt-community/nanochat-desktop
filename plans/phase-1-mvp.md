# Phase 1: MVP - Core Chat

**Version**: v0.1.0  
**Branch**: `v0.1.0`  
**Goal**: Deliver a minimal but functional chat application

---

## Overview

Phase 1 establishes the foundation of NanoChat Desktop with core chat functionality. Users should be able to configure their backend, send messages, receive progressively updated responses (via polling), and manage basic conversations.

---

## Prerequisites

### Human Tasks (Before Starting)

1. **Create GitHub Repository**
   ```bash
   gh repo create nanochat-desktop-v2 --private --description "NanoChat Linux Desktop Client"
   cd nanochat-desktop-v2
   git checkout -b v0.1.0
   ```

2. **Set Up Development Environment**
   ```bash
   # Install system dependencies (Fedora/RHEL)
   sudo dnf install python3.11 python3.11-devel gtk4-devel libadwaita-devel \
                    gobject-introspection-devel cairo-devel libsecret-devel
   
   # Install system dependencies (Ubuntu/Debian)
   sudo apt install python3.11 python3.11-dev libgtk-4-dev libadwaita-1-dev \
                    libgirepository1.0-dev libcairo2-dev libsecret-1-dev
   
   # Install system dependencies (Arch)
   sudo pacman -S python gtk4 libadwaita gobject-introspection cairo libsecret
   ```

3. **Create Python Virtual Environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   ```

---

## Implementation Tasks

### Task 1.1: Project Scaffolding

**Files to create:**
```
nanochat-desktop-v2/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   └── nanochat/
│       ├── __init__.py
│       └── __main__.py
```

**pyproject.toml:**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nanochat-desktop"
version = "0.1.0"
description = "NanoChat Desktop Client for Linux"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
    "PyGObject>=3.46.0",
    "httpx>=0.27.0",
    "pydantic>=2.5.0",
    "keyring>=24.0.0",
    "tomli>=2.0.0",
    "tomli-w>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.1.0",
    "black>=23.0.0",
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[project.scripts]
nanochat = "nanochat.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["src/nanochat"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ["py311"]
```

**src/nanochat/__init__.py:**
```python
"""NanoChat Desktop - Linux chat client for NanoChat API."""

__version__ = "0.1.0"
```

**src/nanochat/__main__.py:**
```python
"""Entry point for NanoChat Desktop."""

import sys

def main():
    """Main entry point."""
    from nanochat.application import NanoChatApplication
    app = NanoChatApplication()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
```

**Acceptance Criteria:**
- [ ] `pip install -e .` succeeds
- [ ] `python -m nanochat` runs without import errors
- [ ] Project follows Python packaging standards

---

### Task 1.2: API Client Foundation

**Files to create:**
```
src/nanochat/api/
├── __init__.py
├── client.py
├── models.py
└── exceptions.py
```

**src/nanochat/api/models.py:**
```python
"""Pydantic models for NanoChat API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """Conversation model."""
    id: str
    title: str
    user_id: str = Field(alias="userId")
    assistant_id: Optional[str] = Field(default=None, alias="assistantId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    model_id: Optional[str] = Field(default=None, alias="modelId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    message_count: int = Field(default=0, alias="messageCount")
    pinned: bool = False
    cost_usd: Optional[float] = Field(default=None, alias="costUsd")

    class Config:
        populate_by_name = True


class Message(BaseModel):
    """Message model."""
    id: str
    conversation_id: str = Field(alias="conversationId")
    role: str  # user | assistant | system
    content: str
    reasoning: Optional[str] = None
    model_id: Optional[str] = Field(default=None, alias="modelId")
    created_at: datetime = Field(alias="createdAt")
    token_count: Optional[int] = Field(default=None, alias="tokenCount")
    cost_usd: Optional[float] = Field(default=None, alias="costUsd")
    starred: Optional[bool] = None

    class Config:
        populate_by_name = True


class ModelCapabilities(BaseModel):
    """Model capabilities."""
    vision: bool = False
    reasoning: bool = False
    images: bool = False
    video: bool = False


class ModelPricing(BaseModel):
    """Model pricing information."""
    prompt: Optional[str] = None
    completion: Optional[str] = None
    image: Optional[str] = None
    request: Optional[str] = None


class Model(BaseModel):
    """AI Model information."""
    id: str
    name: str
    description: Optional[str] = None
    enabled: bool
    pinned: bool
    capabilities: ModelCapabilities
    pricing: Optional[ModelPricing] = None


class GenerateMessageRequest(BaseModel):
    """Request to generate a message."""
    message: Optional[str] = None
    model_id: str
    assistant_id: Optional[str] = None
    project_id: Optional[str] = None
    conversation_id: Optional[str] = None
    web_search_enabled: Optional[bool] = None
    web_search_mode: Optional[str] = None
    reasoning_effort: Optional[str] = None
    temporary: Optional[bool] = None
```

**src/nanochat/api/exceptions.py:**
```python
"""API exceptions."""


class NanoChatAPIError(Exception):
    """Base exception for API errors."""
    pass


class AuthenticationError(NanoChatAPIError):
    """Authentication failed."""
    pass


class ConnectionError(NanoChatAPIError):
    """Network connection error."""
    pass


class RateLimitError(NanoChatAPIError):
    """Rate limit exceeded."""
    pass
```

**src/nanochat/api/client.py:**
```python
"""HTTP client for NanoChat API."""

import httpx
from typing import AsyncGenerator, Optional
import json

from .models import (
    Conversation, Message, Model, GenerateMessageRequest
)
from .exceptions import (
    NanoChatAPIError, AuthenticationError, ConnectionError, RateLimitError
)


class NanoChatClient:
    """Async client for NanoChat API."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(30.0, read=300.0)
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an API request with error handling."""
        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                raise NanoChatAPIError(f"API error: {e.response.status_code}")
        except httpx.NetworkError:
            raise ConnectionError("Cannot connect to server")
    
    # Conversations
    async def get_conversations(self, project_id: Optional[str] = None) -> list[Conversation]:
        """Get all conversations."""
        params = {}
        if project_id:
            params["projectId"] = project_id
        data = await self._request("GET", "/api/db/conversations", params=params)
        return [Conversation.model_validate(c) for c in data]
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation."""
        await self._request("DELETE", "/api/db/conversations", params={"id": conversation_id})
    
    # Messages
    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Get messages for a conversation."""
        data = await self._request(
            "GET", "/api/db/messages", 
            params={"conversationId": conversation_id}
        )
        return [Message.model_validate(m) for m in data]
    
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get a single conversation by ID."""
        data = await self._request(
            "GET",
            "/api/db/conversations",
            params={"id": conversation_id},
        )
        return Conversation.model_validate(data)

    async def generate_message_with_polling(
        self, request: GenerateMessageRequest
    ) -> tuple[str, str]:
        """Generate a message using polling.

        Returns:
            tuple: (conversation_id, final_content)

        Note: The API returns immediately with a conversation_id.
        This method polls for the generated content.
        """
        # 1. Send the message (returns immediately with conversation_id)
        response = await self._request(
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
            conversation = await self.get_conversation(conversation_id)

            # Get messages
            messages = await self.get_messages(conversation_id)

            # Find assistant message and update if content changed
            for msg in messages:
                if msg.role == "assistant" and msg.content:
                    if msg.content != last_content:
                        last_content = msg.content

            # Stop polling when generation is complete
            if not conversation.generating:
                break

        return conversation_id, last_content

    # Models
    async def get_models(self) -> list[Model]:
        """Get available models."""
        data = await self._request("GET", "/api/models")
        return [Model.model_validate(m) for m in data]
    
    # Connection test
    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            await self.get_models()
            return True
        except NanoChatAPIError:
            return False
```

**Acceptance Criteria:**
- [ ] Can connect to API with valid credentials
- [ ] Can fetch conversations list
- [ ] Can fetch messages for a conversation
- [ ] Can fetch a single conversation (for checking `generating` status)
- [ ] Can generate messages with polling (progressive content updates)
- [ ] Proper error handling for network issues

---

### Task 1.3: Data Layer - Settings and Secrets

**Files to create:**
```
src/nanochat/data/
├── __init__.py
├── settings.py
├── secrets.py
└── xdg.py
```

**src/nanochat/data/xdg.py:**
```python
"""XDG Base Directory helpers."""

from pathlib import Path
import os


def get_config_dir() -> Path:
    """Get XDG config directory for NanoChat."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    config_dir = Path(xdg_config) / "nanochat"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get XDG data directory for NanoChat."""
    xdg_data = os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
    data_dir = Path(xdg_data) / "nanochat"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """Get XDG cache directory for NanoChat."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
    cache_dir = Path(xdg_cache) / "nanochat"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
```

**src/nanochat/data/settings.py:**
```python
"""Settings management using TOML."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w

from .xdg import get_config_dir


class ServerSettings(BaseModel):
    """Server connection settings."""
    backend_url: str = ""


class UISettings(BaseModel):
    """UI preferences."""
    theme: str = "system"  # system, light, dark
    sidebar_width: int = 280


class ChatSettings(BaseModel):
    """Chat preferences."""
    default_model: str = ""


class Settings(BaseModel):
    """Application settings."""
    server: ServerSettings = ServerSettings()
    ui: UISettings = UISettings()
    chat: ChatSettings = ChatSettings()


class SettingsManager:
    """Manages application settings."""
    
    def __init__(self):
        self._settings_path = get_config_dir() / "config.toml"
        self._settings: Optional[Settings] = None
    
    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = self._load()
        return self._settings
    
    def _load(self) -> Settings:
        """Load settings from file."""
        if self._settings_path.exists():
            with open(self._settings_path, "rb") as f:
                data = tomllib.load(f)
            return Settings.model_validate(data)
        return Settings()
    
    def save(self) -> None:
        """Save settings to file."""
        if self._settings:
            with open(self._settings_path, "wb") as f:
                tomli_w.dump(self._settings.model_dump(), f)
    
    def update(self, **kwargs) -> None:
        """Update settings and save."""
        # Update nested settings
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()
```

**src/nanochat/data/secrets.py:**
```python
"""Secure credential storage using libsecret/keyring."""

import keyring
from typing import Optional


KEYRING_SERVICE = "nanochat-desktop"


class SecretsManager:
    """Manages secure storage of credentials."""
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get stored API key."""
        return keyring.get_password(KEYRING_SERVICE, "api_key")
    
    @staticmethod
    def set_api_key(api_key: str) -> None:
        """Store API key securely."""
        keyring.set_password(KEYRING_SERVICE, "api_key", api_key)
    
    @staticmethod
    def delete_api_key() -> None:
        """Delete stored API key."""
        try:
            keyring.delete_password(KEYRING_SERVICE, "api_key")
        except keyring.errors.PasswordDeleteError:
            pass
    
    @staticmethod
    def has_api_key() -> bool:
        """Check if API key is stored."""
        return SecretsManager.get_api_key() is not None
```

**Acceptance Criteria:**
- [ ] Settings persist across app restarts
- [ ] API key stored in system keyring
- [ ] XDG directories created correctly
- [ ] Settings load with sensible defaults

---

### Task 1.4: GTK4 Application Shell

**Files to create:**
```
src/nanochat/
├── application.py
└── ui/
    ├── __init__.py
    └── window.py
```

**src/nanochat/application.py:**
```python
"""GTK4/Libadwaita Application."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib

from nanochat.data.settings import SettingsManager
from nanochat.data.secrets import SecretsManager


class NanoChatApplication(Adw.Application):
    """Main application class."""
    
    def __init__(self):
        super().__init__(
            application_id="com.nanogpt.NanoChat",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        
        self.settings_manager = SettingsManager()
        self.secrets_manager = SecretsManager()
        self._window = None
    
    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)
        
        # Set up actions
        self._setup_actions()
    
    def do_activate(self):
        """Called when the application is activated."""
        if not self._window:
            from nanochat.ui.window import NanoChatWindow
            self._window = NanoChatWindow(application=self)
        
        self._window.present()
        
        # Check if setup is needed
        if not self._is_configured():
            self._show_setup_dialog()
    
    def _setup_actions(self):
        """Set up application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        
        # Settings action
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self._on_settings)
        self.add_action(settings_action)
        self.set_accels_for_action("app.settings", ["<Control>comma"])
        
        # New chat action
        new_chat_action = Gio.SimpleAction.new("new-chat", None)
        new_chat_action.connect("activate", self._on_new_chat)
        self.add_action(new_chat_action)
        self.set_accels_for_action("app.new-chat", ["<Control>n"])
    
    def _is_configured(self) -> bool:
        """Check if app is configured."""
        has_url = bool(self.settings_manager.settings.server.backend_url)
        has_key = self.secrets_manager.has_api_key()
        return has_url and has_key
    
    def _show_setup_dialog(self):
        """Show setup dialog."""
        from nanochat.ui.setup_dialog import SetupDialog
        dialog = SetupDialog(self._window)
        dialog.present()
    
    def _on_settings(self, action, param):
        """Handle settings action."""
        self._show_setup_dialog()
    
    def _on_new_chat(self, action, param):
        """Handle new chat action."""
        if self._window:
            self._window.new_conversation()
```

**src/nanochat/ui/window.py:**
```python
"""Main application window."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib


class NanoChatWindow(Adw.ApplicationWindow):
    """Main window with sidebar and chat area."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_default_size(1200, 800)
        self.set_title("NanoChat")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the UI."""
        # Main layout with navigation split view
        self.split_view = Adw.NavigationSplitView()
        self.set_content(self.split_view)
        
        # Sidebar
        sidebar = self._create_sidebar()
        self.split_view.set_sidebar(sidebar)
        
        # Content area
        content = self._create_content()
        self.split_view.set_content(content)
    
    def _create_sidebar(self) -> Adw.NavigationPage:
        """Create sidebar with conversation list."""
        page = Adw.NavigationPage()
        page.set_title("Conversations")
        
        # Toolbar view for header + content
        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        # New chat button
        new_btn = Gtk.Button(icon_name="list-add-symbolic")
        new_btn.set_tooltip_text("New Chat")
        new_btn.connect("clicked", lambda _: self.new_conversation())
        header.pack_start(new_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Conversation list
        self.conversation_list = Gtk.ListBox()
        self.conversation_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.conversation_list.add_css_class("navigation-sidebar")
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.conversation_list)
        scrolled.set_vexpand(True)
        
        toolbar_view.set_content(scrolled)
        
        return page
    
    def _create_content(self) -> Adw.NavigationPage:
        """Create main content area for chat."""
        page = Adw.NavigationPage()
        page.set_title("Chat")
        
        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)
        
        # Header bar with model selector
        header = Adw.HeaderBar()
        
        # Model selector dropdown
        self.model_selector = Gtk.DropDown()
        self.model_selector.set_tooltip_text("Select Model")
        header.set_title_widget(self.model_selector)
        
        # Settings button
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.set_action_name("app.settings")
        header.pack_end(settings_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Chat area (will be replaced with ChatView)
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.chat_box.set_vexpand(True)
        
        # Messages area (scrollable)
        self.messages_scroll = Gtk.ScrolledWindow()
        self.messages_scroll.set_vexpand(True)
        self.messages_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.messages_list.set_margin_start(12)
        self.messages_list.set_margin_end(12)
        self.messages_list.set_margin_top(12)
        self.messages_list.set_margin_bottom(12)
        self.messages_scroll.set_child(self.messages_list)
        self.chat_box.append(self.messages_scroll)
        
        # Input area
        input_box = self._create_input_area()
        self.chat_box.append(input_box)
        
        toolbar_view.set_content(self.chat_box)
        
        return page
    
    def _create_input_area(self) -> Gtk.Box:
        """Create message input area."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_bottom(12)
        box.add_css_class("linked")
        
        # Text entry
        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text("Type a message...")
        self.message_entry.set_hexpand(True)
        self.message_entry.connect("activate", self._on_send)
        box.append(self.message_entry)
        
        # Send button
        self.send_btn = Gtk.Button(icon_name="mail-send-symbolic")
        self.send_btn.set_tooltip_text("Send Message")
        self.send_btn.add_css_class("suggested-action")
        self.send_btn.connect("clicked", self._on_send)
        box.append(self.send_btn)
        
        return box
    
    def _on_send(self, widget):
        """Handle send button click."""
        text = self.message_entry.get_text().strip()
        if text:
            # TODO: Send message via API
            self.message_entry.set_text("")
            print(f"Sending: {text}")
    
    def new_conversation(self):
        """Start a new conversation."""
        # TODO: Implement
        print("New conversation")
```

**Acceptance Criteria:**
- [ ] Application launches with Libadwaita window
- [ ] Split view shows sidebar and content
- [ ] Header bar with model selector placeholder
- [ ] Message input with send button
- [ ] Keyboard shortcuts work (Ctrl+Q, Ctrl+N)

---

### Task 1.5: Setup Dialog

**File to create:** `src/nanochat/ui/setup_dialog.py`

```python
"""Setup/configuration dialog."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib
import asyncio


class SetupDialog(Adw.PreferencesWindow):
    """Setup dialog for backend URL and API key."""
    
    def __init__(self, parent):
        super().__init__()
        
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("NanoChat Setup")
        self.set_default_size(500, 400)
        
        self._app = parent.get_application()
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Build the setup UI."""
        # Server page
        server_page = Adw.PreferencesPage()
        server_page.set_title("Server")
        server_page.set_icon_name("network-server-symbolic")
        self.add(server_page)
        
        # Connection group
        conn_group = Adw.PreferencesGroup()
        conn_group.set_title("Connection")
        conn_group.set_description("Configure your NanoChat server connection")
        server_page.add(conn_group)
        
        # Backend URL
        self.url_row = Adw.EntryRow()
        self.url_row.set_title("Backend URL")
        self.url_row.set_input_purpose(Gtk.InputPurpose.URL)
        conn_group.add(self.url_row)
        
        # API Key
        self.key_row = Adw.PasswordEntryRow()
        self.key_row.set_title("API Key")
        conn_group.add(self.key_row)
        
        # Test connection button
        test_btn = Gtk.Button(label="Test Connection")
        test_btn.add_css_class("suggested-action")
        test_btn.set_margin_top(12)
        test_btn.connect("clicked", self._on_test_connection)
        conn_group.add(test_btn)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_margin_top(8)
        conn_group.add(self.status_label)
        
        # Save button in header
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        # Note: Adw.PreferencesWindow doesn't have a simple way to add header buttons
        # We'll handle save when the window closes
        
        self.connect("close-request", self._on_close)
    
    def _load_current_settings(self):
        """Load current settings into form."""
        settings = self._app.settings_manager.settings
        self.url_row.set_text(settings.server.backend_url)
        
        api_key = self._app.secrets_manager.get_api_key()
        if api_key:
            self.key_row.set_text(api_key)
    
    def _on_test_connection(self, button):
        """Test the connection."""
        url = self.url_row.get_text().strip()
        key = self.key_row.get_text().strip()
        
        if not url or not key:
            self.status_label.set_markup(
                '<span color="red">Please enter URL and API key</span>'
            )
            return
        
        self.status_label.set_text("Testing...")
        button.set_sensitive(False)
        
        # Run async test
        def run_test():
            import asyncio
            from nanochat.api.client import NanoChatClient
            
            async def test():
                async with NanoChatClient(url, key) as client:
                    return await client.test_connection()
            
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(test())
                loop.close()
                return result
            except Exception as e:
                return str(e)
        
        def on_complete(success):
            button.set_sensitive(True)
            if success is True:
                self.status_label.set_markup(
                    '<span color="green">✓ Connection successful</span>'
                )
            else:
                self.status_label.set_markup(
                    f'<span color="red">✗ {success}</span>'
                )
        
        # Run in thread
        import threading
        def thread_func():
            result = run_test()
            GLib.idle_add(on_complete, result)
        
        thread = threading.Thread(target=thread_func)
        thread.start()
    
    def _on_save(self, button):
        """Save settings."""
        self._save_settings()
        self.close()
    
    def _on_close(self, window):
        """Handle window close."""
        self._save_settings()
        return False
    
    def _save_settings(self):
        """Save current form to settings."""
        url = self.url_row.get_text().strip()
        key = self.key_row.get_text().strip()
        
        if url:
            self._app.settings_manager.settings.server.backend_url = url
            self._app.settings_manager.save()
        
        if key:
            self._app.secrets_manager.set_api_key(key)
```

**Acceptance Criteria:**
- [ ] Dialog opens from settings menu
- [ ] Can enter backend URL and API key
- [ ] Test connection validates credentials
- [ ] Settings saved to config file
- [ ] API key saved to system keyring

---

### Task 1.6: Model Selector Integration

**Update:** `src/nanochat/ui/window.py` - Add model loading

```python
# Add to NanoChatWindow class

def _load_models(self):
    """Load models from API."""
    import threading
    import asyncio
    from nanochat.api.client import NanoChatClient
    
    app = self.get_application()
    url = app.settings_manager.settings.server.backend_url
    key = app.secrets_manager.get_api_key()
    
    if not url or not key:
        return
    
    def fetch():
        async def get_models():
            async with NanoChatClient(url, key) as client:
                return await client.get_models()
        
        loop = asyncio.new_event_loop()
        models = loop.run_until_complete(get_models())
        loop.close()
        return models
    
    def on_complete(models):
        # Filter to enabled models and populate dropdown
        enabled = [m for m in models if m.enabled]
        
        # Create string list for dropdown
        model_names = Gtk.StringList()
        self._model_ids = []
        for model in enabled:
            model_names.append(model.name)
            self._model_ids.append(model.id)
        
        self.model_selector.set_model(model_names)
        
        # Select default model
        default = app.settings_manager.settings.chat.default_model
        if default in self._model_ids:
            idx = self._model_ids.index(default)
            self.model_selector.set_selected(idx)
    
    def thread_func():
        try:
            models = fetch()
            GLib.idle_add(on_complete, models)
        except Exception as e:
            print(f"Failed to load models: {e}")
    
    thread = threading.Thread(target=thread_func)
    thread.start()
```

**Acceptance Criteria:**
- [ ] Models load on app startup
- [ ] Dropdown shows model names
- [ ] Can select different models
- [ ] Selection persists

---

### Task 1.7: Conversation List and Chat Integration

This task brings everything together - loading conversations, displaying them in the sidebar, and enabling basic chat functionality with polling-based message generation.

**Files to update/create:**
- Update `src/nanochat/ui/window.py` - Full chat integration
- Create `src/nanochat/ui/message_widget.py` - Message display

**Full implementation should:**
1. Load conversations on startup
2. Display conversations in sidebar
3. Load messages when conversation selected
4. Send messages with polling-based progressive response updates
5. Support new conversation creation

**Acceptance Criteria:**
- [ ] Conversations appear in sidebar
- [ ] Clicking conversation loads messages
- [ ] Can send message and see progressive response updates
- [ ] New conversation appears after first message
- [ ] Delete conversation works

---

### Task 1.8: Local Database Caching

**Files to create:**
```
src/nanochat/data/
├── database.py
└── models.py
```

**Implementation should:**
1. Create SQLite database in XDG data directory
2. Cache conversations and messages locally
3. Load from cache if offline
4. Sync with server when online

**Acceptance Criteria:**
- [ ] Database created on first run
- [ ] Conversations cached locally
- [ ] Messages cached locally
- [ ] App works with cached data when offline

---

### Task 1.9: Packaging

**Files to create:**
```
flatpak/
└── com.nanogpt.NanoChat.yml

appimage/
└── AppImageBuilder.yml

data/
├── icons/
│   └── com.nanogpt.NanoChat.svg
└── com.nanogpt.NanoChat.desktop
```

**Human Tasks:**
1. Create app icon (SVG)
2. Test Flatpak build locally
3. Test AppImage build locally

**Acceptance Criteria:**
- [ ] Flatpak builds successfully
- [ ] AppImage builds successfully
- [ ] Both launch and function correctly

---

## Definition of Done - Phase 1

- [ ] All tasks completed
- [ ] Manual testing checklist passed:
  - [ ] Fresh install works
  - [ ] Setup dialog configures connection
  - [ ] Model selector populates
  - [ ] Can create new conversation
  - [ ] Can send message
  - [ ] Streaming response displays
  - [ ] Can switch conversations
  - [ ] Can delete conversation
  - [ ] Settings persist after restart
  - [ ] Works on X11
  - [ ] Works on Wayland
- [ ] Code reviewed
- [ ] Branch merged and tagged as `v0.1.0`
- [ ] Release created on GitHub with binaries

---

## Release Checklist

```bash
# Final testing
./run_tests.sh  # If tests exist

# Build packages
flatpak-builder --user --install build flatpak/com.nanogpt.NanoChat.yml
# Export Flatpak bundle
flatpak build-bundle ~/.local/share/flatpak/repo \
    nanochat-v0.1.0.flatpak com.nanogpt.NanoChat

# Build AppImage
python -m python_appimage build app -p 3.11 .
mv NanoChat-*.AppImage nanochat-v0.1.0-x86_64.AppImage

# Create release
git checkout v0.1.0
git tag -a v0.1.0 -m "Release v0.1.0 - MVP Core Chat"
git push origin v0.1.0 --tags

# On GitHub:
# 1. Create release from tag v0.1.0
# 2. Upload nanochat-v0.1.0.flatpak
# 3. Upload nanochat-v0.1.0-x86_64.AppImage
# 4. Write release notes
```

---

## Implementation Notes

### Architectural Deviation from Plan

**Task 1.2 - API Client Foundation:**

The original plan specified a `generate_message_with_polling()` method in `src/nanochat/api/client.py`. In the actual implementation, the polling logic is embedded directly in `src/nanochat/ui/window.py` within the `_on_send()` method (lines 536-627).

**Reasoning:** This approach keeps the UI update logic tightly coupled with the polling mechanism, allowing for more direct GLib idle_add calls for progressive UI updates without additional abstraction layers.

**Impact:** None - the functionality works identically. This is an implementation detail that does not affect the API contract or user experience.
