"""Main application window."""

import asyncio
import logging
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from pathlib import Path
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from nanochat.api.models import Assistant, Conversation, Message, Model
from nanochat.data.database import Database
from nanochat.data.secrets import SecretsManager
from nanochat.data.settings import SettingsManager
from nanochat.data.repositories import ConversationRepository, MessageRepository
from nanochat.ui.message_widget import MessageWidget
from nanochat.ui.models_dialog import ModelsDialog
from nanochat.ui.attachments import (
    AttachmentType,
    PendingAttachment,
    create_pending_attachment,
    validate_attachment,
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
)
from nanochat.ui.attachment_preview import AttachmentPreviewBar

logger = logging.getLogger(__name__)


class NanoChatWindow(Adw.ApplicationWindow):  # type: ignore[misc]
    """Main window with sidebar and chat area."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        secrets_manager: SecretsManager,
        database: Database,
        conversation_repository: ConversationRepository | None = None,
        message_repository: MessageRepository | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)

        self.settings_manager = settings_manager
        self.secrets_manager = secrets_manager
        self.database = database

        # Create repositories (will create API client lazily when needed)
        self.conversation_repo = conversation_repository
        self.message_repo = message_repository
        self._models: list[Model] = []
        self._model_ids: list[str] = []
        self._conversations: list[Conversation] = []
        self._current_conversation_id: str | None = None
        self._current_messages: list[Message] = []
        self._is_sending: bool = False
        # Track loading state for UI feedback
        self._is_loading_conversations: bool = False
        # Track in-progress API syncs to prevent duplicate requests
        self._syncing_conversations: set[str] = set()
        # Flag to prevent message reload during conversation list updates
        self._updating_conversation_list: bool = False
        # Search state
        self._search_query: str = ""
        self._debounce_timer_id: int | None = None
        self._search_debounce_ms: int = 300  # 300ms debounce
        # Web search state
        self._web_search_enabled: bool = False
        self._web_search_mode: str = "standard"
        self._web_search_provider: str = "tavily"
        # Assistant state
        self._assistants: list[Assistant] = []
        self._assistant_ids: list[str] = []
        self._current_assistant_id: str | None = None

        # Attachment state
        self._pending_attachments: list[PendingAttachment] = []
        self._attachment_preview_bar: AttachmentPreviewBar | None = None
        self._is_uploading: bool = False

        self.set_default_size(1200, 800)
        self.set_title("NanoChat")

        self._setup_ui()
        self._setup_keyboard_shortcuts()

        # Connect to map signal for loading after UI is ready
        self.connect("map", self._on_map)

    def _ensure_repositories(self) -> bool:
        """Ensure repositories are initialized.

        Creates repositories on-demand when URL and API key are available.
        Returns True if repositories are ready, False otherwise.
        """
        if self.conversation_repo is None or self.message_repo is None:
            url = self.settings_manager.settings.server.backend_url
            key = self.secrets_manager.get_api_key()

            if not url or not key:
                return False

            if self.conversation_repo is None:
                self.conversation_repo = ConversationRepository(self.database, url, key)
            if self.message_repo is None:
                self.message_repo = MessageRepository(self.database, url, key)

        return True

    def _setup_ui(self) -> None:
        """Build the UI."""
        # Main layout with navigation split view
        self.split_view = Adw.NavigationSplitView()

        # Wrap split view in toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.split_view)
        self.set_content(self.toast_overlay)

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
        page.add_css_class("sidebar")

        # Toolbar view for header + content
        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.add_css_class("sidebar-header")

        # New chat button
        new_btn = Gtk.Button(icon_name="list-add-symbolic")
        new_btn.set_tooltip_text("New Chat (Ctrl+N)")
        new_btn.connect("clicked", lambda _: self.new_conversation())
        header.pack_start(new_btn)

        # Refresh button
        self.refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text("Refresh Conversations")
        self.refresh_btn.connect("clicked", self._on_refresh_conversations)
        header.pack_start(self.refresh_btn)

        toolbar_view.add_top_bar(header)

        # Search entry container
        search_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_box.set_margin_start(8)
        search_box.set_margin_end(8)
        search_box.set_margin_top(8)
        search_box.set_margin_bottom(8)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search conversations...")
        self.search_entry.set_tooltip_text("Search (Ctrl+K)")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_stopped)
        search_box.append(self.search_entry)

        # Container for search + list
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(search_box)

        # Conversation list
        self.conversation_list = Gtk.ListBox()
        self.conversation_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.conversation_list.add_css_class("navigation-sidebar")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.conversation_list)
        scrolled.set_vexpand(True)

        content_box.append(scrolled)
        toolbar_view.set_content(content_box)

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

        # Left side: Assistant selector
        assistant_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self.assistant_selector = Gtk.DropDown()
        self.assistant_selector.set_tooltip_text("Select Assistant")
        self._assistant_change_handler = self.assistant_selector.connect(
            "notify::selected", self._on_assistant_changed
        )
        assistant_box.append(self.assistant_selector)

        # Manage assistants button
        manage_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        manage_btn.add_css_class("flat")
        manage_btn.set_tooltip_text("Manage Assistants")
        manage_btn.connect("clicked", self._on_manage_assistants)
        assistant_box.append(manage_btn)

        header.pack_start(assistant_box)

        # Center: Model selector dropdown with manage button
        model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self.model_selector = Gtk.DropDown()
        self.model_selector.set_size_request(250, -1)  # Minimum width
        self.model_selector.set_tooltip_text("Select Model")
        self._model_change_handler = self.model_selector.connect(
            "notify::selected", self._on_model_changed
        )
        model_box.append(self.model_selector)

        # Manage models button
        manage_models_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        manage_models_btn.add_css_class("flat")
        manage_models_btn.set_tooltip_text("Manage Models")
        manage_models_btn.connect("clicked", self._on_manage_models)
        model_box.append(manage_models_btn)

        header.set_title_widget(model_box)

        # Settings button
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.set_action_name("app.settings")
        header.pack_end(settings_btn)

        toolbar_view.add_top_bar(header)

        # Chat area
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
        """Create message input area with attachments and web search toggle."""
        # Outer container for preview bar + input
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Attachment preview bar (hidden by default)
        self._attachment_preview_bar = AttachmentPreviewBar(
            on_remove=self._on_attachment_remove
        )
        outer_box.append(self._attachment_preview_bar)

        # Input row
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_bottom(12)
        box.add_css_class("chat-input-box")

        # Set up drop target for the input area
        self._setup_drop_target(box)

        # Attach button
        self.attach_btn = Gtk.Button(icon_name="mail-attachment-symbolic")
        self.attach_btn.set_tooltip_text("Attach files (images, PDFs, etc.)")
        self.attach_btn.add_css_class("flat")
        self.attach_btn.add_css_class("attach-button")
        self.attach_btn.connect("clicked", self._on_attach_clicked)
        box.append(self.attach_btn)

        # Web search toggle button
        self.web_search_btn = Gtk.ToggleButton()
        self.web_search_btn.set_icon_name("edit-find-symbolic")
        self.web_search_btn.set_tooltip_text("Enable web search")
        self.web_search_btn.add_css_class("flat")
        self.web_search_btn.add_css_class("web-search-toggle")
        self.web_search_btn.connect("toggled", self._on_web_search_toggled)
        box.append(self.web_search_btn)

        # Web search config popover (attached to toggle button)
        from nanochat.ui.web_search_config import WebSearchConfigPopover

        self.web_search_popover = WebSearchConfigPopover(
            initial_mode=self._web_search_mode,
            initial_provider=self._web_search_provider,
        )
        self.web_search_popover.set_parent(self.web_search_btn)
        self.web_search_popover.connect("settings-changed", self._on_web_search_settings_changed)

        # Add right-click handler for config popover
        right_click = Gtk.GestureClick()
        right_click.set_button(3)  # Right mouse button
        right_click.connect("pressed", self._on_web_search_right_click)
        self.web_search_btn.add_controller(right_click)

        # Add long-press handler for touch/mouse
        long_press = Gtk.GestureLongPress()
        long_press.connect("pressed", self._on_web_search_long_press)
        self.web_search_btn.add_controller(long_press)

        # Text entry (with linked styling)
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        entry_box.add_css_class("linked")
        entry_box.set_hexpand(True)

        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text("Type a message...")
        self.message_entry.set_hexpand(True)
        self.message_entry.set_sensitive(True)
        self.message_entry.connect("activate", self._on_send)
        entry_box.append(self.message_entry)

        box.append(entry_box)

        # Send button
        self.send_btn = Gtk.Button(icon_name="mail-send-symbolic")
        self.send_btn.set_tooltip_text("Send Message")
        self.send_btn.add_css_class("suggested-action")
        self.send_btn.add_css_class("send-button")
        self.send_btn.set_sensitive(True)
        self.send_btn.connect("clicked", self._on_send)
        box.append(self.send_btn)

        outer_box.append(box)

        # Load saved web search preferences
        self._load_web_search_settings()

        return outer_box

    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard event handling for window-level shortcuts."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Setup sidebar navigation
        self._setup_sidebar_navigation()

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        """Handle key press events."""
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        # Ctrl+K - Focus search (when implemented)
        if ctrl and keyval == Gdk.KEY_k:
            self._focus_search()
            return True

        # Ctrl+Enter - Send message
        if ctrl and keyval == Gdk.KEY_Return:
            self._on_send(self.send_btn)
            return True

        # Escape - Various cancel actions
        if keyval == Gdk.KEY_Escape:
            return self._handle_escape()

        # F2 - Rename selected conversation
        if keyval == Gdk.KEY_F2:
            self._rename_selected_conversation()
            return True

        return False  # Event not handled

    def _setup_sidebar_navigation(self) -> None:
        """Set up keyboard navigation for sidebar."""
        # Enable keyboard navigation on the ListBox
        self.conversation_list.set_activate_on_single_click(False)

        # Add key controller for arrow navigation
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_sidebar_key_pressed)
        self.conversation_list.add_controller(key_controller)

    def _on_sidebar_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        """Handle sidebar navigation keys."""
        if keyval == Gdk.KEY_Up:
            self._select_previous_conversation()
            return True
        elif keyval == Gdk.KEY_Down:
            self._select_next_conversation()
            return True
        elif keyval == Gdk.KEY_Return:
            # Load selected conversation
            selected = self.conversation_list.get_selected_row()
            if selected and isinstance(selected, Adw.ActionRow):
                self._load_messages(selected.get_name())
            return True
        return False

    def _select_previous_conversation(self) -> None:
        """Select the previous conversation in the list."""
        selected = self.conversation_list.get_selected_row()
        if selected:
            prev_row = selected.get_prev_sibling()
            while prev_row and not isinstance(prev_row, Adw.ActionRow):
                prev_row = prev_row.get_prev_sibling()
            if prev_row:
                self.conversation_list.select_row(prev_row)
                self._load_messages(prev_row.get_name())
        else:
            # Select first if none selected
            child = self.conversation_list.get_first_child()
            while child and not isinstance(child, Adw.ActionRow):
                child = child.get_next_sibling()
            if child:
                self.conversation_list.select_row(child)

    def _select_next_conversation(self) -> None:
        """Select the next conversation in the list."""
        selected = self.conversation_list.get_selected_row()
        if selected:
            next_row = selected.get_next_sibling()
            while next_row and not isinstance(next_row, Adw.ActionRow):
                next_row = next_row.get_next_sibling()
            if next_row:
                self.conversation_list.select_row(next_row)
                self._load_messages(next_row.get_name())

    def _handle_escape(self) -> bool:
        """Handle Escape key for various cancel actions."""
        # If search is focused and has text, clear it
        if hasattr(self, "search_entry") and self.search_entry.has_focus():
            if self.search_entry.get_text():
                self.search_entry.set_text("")
                return True
        return False

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Handle search text changes with debounce."""
        # Cancel previous debounce timer
        if self._debounce_timer_id:
            GLib.source_remove(self._debounce_timer_id)

        # Schedule new search after debounce delay
        self._debounce_timer_id = GLib.timeout_add(
            self._search_debounce_ms,
            self._perform_search,
            entry.get_text().strip().lower()
        )

    def _perform_search(self, query: str) -> bool:
        """Perform the actual search and update the list."""
        self._search_query = query
        self._debounce_timer_id = None

        if not query:
            # Empty search - show all conversations
            self._update_conversation_list(self._conversations)
        else:
            # Filter conversations by title
            filtered = [
                conv for conv in self._conversations
                if query in conv.title.lower()
            ]
            self._update_conversation_list(filtered, preserve_full_list=True)

        return False  # Don't repeat timer

    def _on_search_stopped(self, entry: Gtk.SearchEntry) -> None:
        """Handle search cancelled (Escape pressed in search entry)."""
        entry.set_text("")
        self._search_query = ""
        self._update_conversation_list(self._conversations)

    def _focus_search(self) -> None:
        """Focus the search entry (for Ctrl+K shortcut)."""
        if hasattr(self, "search_entry"):
            self.search_entry.grab_focus()

    def _rename_selected_conversation(self) -> None:
        """Rename the selected conversation (stub for future implementation)."""
        # This is a stub for now - the full implementation will come later
        self.toast_overlay.add_toast(Adw.Toast(title="Rename feature coming soon!"))

    def copy_last_assistant_message(self) -> None:
        """Copy the last assistant message to clipboard."""
        # Find the last assistant message from current messages
        last_assistant_content = None
        for msg in reversed(self._current_messages):
            if msg.role == "assistant":
                last_assistant_content = msg.content
                break

        if not last_assistant_content:
            self.toast_overlay.add_toast(Adw.Toast(title="No assistant message to copy"))
            return

        # Copy to clipboard
        clipboard = self.get_clipboard()
        clipboard.set(last_assistant_content)

        # Show toast confirmation
        self.toast_overlay.add_toast(Adw.Toast(title="Copied last response"))

    def _on_map(self, widget: Gtk.Widget) -> None:
        """Handle window map event - load data after UI is ready."""
        if not self._model_ids:
            self._load_models()
        if not self._assistants:
            self._load_assistants()
        self._load_conversations()

    def _on_model_changed(self, dropdown: Gtk.DropDown, param: object) -> None:
        """Handle model selection change."""
        selected_idx = dropdown.get_selected()
        if selected_idx != Gtk.INVALID_LIST_POSITION and selected_idx < len(self._model_ids):
            model_id = self._model_ids[selected_idx]
            # Only save if different (though notify usually implies change, but good to be safe)
            if self.settings_manager.settings.chat.default_model != model_id:
                self.settings_manager.settings.chat.default_model = model_id
                self.settings_manager.save()

    def _load_models(self) -> None:
        """Load models from API."""
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

        def fetch() -> list[Model] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_models() -> list[Model]:
                async with NanoChatClient(url, key) as client:
                    models = await client.get_models()
                    # Get favorites from local settings
                    favorite_ids = self.settings_manager.settings.chat.favorite_models

                    # Set is_favorite based on local settings
                    for model in models:
                        model.is_favorite = model.id in favorite_ids

                    # Sort: favorites first, then alphabetically
                    return sorted(
                        [m for m in models if m.enabled],
                        key=lambda m: (not m.is_favorite, m.name.lower())
                    )

            try:
                loop = asyncio.new_event_loop()
                models = loop.run_until_complete(get_models())
                loop.close()
                return models
            except Exception as e:
                return e

        def on_complete(models: list[Model] | Exception) -> None:
            if isinstance(models, Exception):
                logger.error(f"Failed to load models: {models}")
                return

            # Store full model objects
            self._models = models

            model_names = Gtk.StringList()
            self._model_ids = []
            for model in models:
                # Add star prefix for favorites
                display_name = f"★ {model.name}" if model.is_favorite else model.name
                model_names.append(display_name)
                self._model_ids.append(model.id)

            # Block signal to prevent overwriting saved setting during setup
            self.model_selector.handler_block(self._model_change_handler)

            self.model_selector.set_model(model_names)

            default = self.settings_manager.settings.chat.default_model
            if default in self._model_ids:
                idx = self._model_ids.index(default)
                self.model_selector.set_selected(idx)

            self.model_selector.handler_unblock(self._model_change_handler)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _load_assistants(self) -> None:
        """Load assistants from API."""
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

        def fetch() -> list[Assistant] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_assistants() -> list[Assistant]:
                async with NanoChatClient(url, key) as client:
                    return await client.get_assistants()

            try:
                loop = asyncio.new_event_loop()
                assistants = loop.run_until_complete(get_assistants())
                loop.close()
                return assistants
            except Exception as e:
                return e

        def on_complete(assistants: list[Assistant] | Exception) -> None:
            if isinstance(assistants, Exception):
                logger.error(f"Failed to load assistants: {assistants}")
                return

            self._assistants = assistants
            self._update_assistant_dropdown(assistants)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _update_assistant_dropdown(self, assistants: list[Assistant]) -> None:
        """Update the assistant dropdown with loaded assistants."""
        # Block signal during setup
        self.assistant_selector.handler_block(self._assistant_change_handler)

        assistant_names = Gtk.StringList()
        assistant_names.append("No Assistant")  # First option - no assistant
        self._assistant_ids = [""]  # Empty string = no assistant

        default_idx = 0  # Default to "No Assistant"

        for i, assistant in enumerate(assistants):
            name = assistant.name
            if assistant.is_default:
                name += " ★"
                default_idx = i + 1  # +1 because of "No Assistant" option
            assistant_names.append(name)
            self._assistant_ids.append(assistant.id)

        self.assistant_selector.set_model(assistant_names)
        self.assistant_selector.set_selected(default_idx)
        self._current_assistant_id = self._assistant_ids[default_idx] if default_idx > 0 else None

        # Apply default assistant's settings if selected
        if default_idx > 0:
            self._apply_assistant_defaults(assistants[default_idx - 1])

        self.assistant_selector.handler_unblock(self._assistant_change_handler)

    def _on_assistant_changed(self, dropdown: Gtk.DropDown, param: object) -> None:
        """Handle assistant selection change."""
        selected_idx = dropdown.get_selected()
        if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(self._assistant_ids):
            return

        assistant_id = self._assistant_ids[selected_idx]
        self._current_assistant_id = assistant_id if assistant_id else None

        # Apply assistant defaults if an assistant is selected
        if assistant_id:
            for assistant in self._assistants:
                if assistant.id == assistant_id:
                    self._apply_assistant_defaults(assistant)
                    break

    def _apply_assistant_defaults(self, assistant: Assistant) -> None:
        """Apply an assistant's default settings."""
        # Apply default model if set
        if assistant.default_model_id and assistant.default_model_id in self._model_ids:
            idx = self._model_ids.index(assistant.default_model_id)
            self.model_selector.handler_block(self._model_change_handler)
            self.model_selector.set_selected(idx)
            self.model_selector.handler_unblock(self._model_change_handler)

        # Apply default web search mode if set
        if assistant.default_web_search_mode:
            if assistant.default_web_search_mode == "off":
                self._web_search_enabled = False
                self.web_search_btn.set_active(False)
            else:
                self._web_search_enabled = True
                self._web_search_mode = assistant.default_web_search_mode
                self.web_search_btn.set_active(True)
                self.web_search_popover.set_mode(assistant.default_web_search_mode)

        if assistant.default_web_search_provider:
            self._web_search_provider = assistant.default_web_search_provider
            self.web_search_popover.set_provider(assistant.default_web_search_provider)

    def _on_manage_assistants(self, button: Gtk.Button) -> None:
        """Open assistants management dialog."""
        from nanochat.ui.assistants_dialog import AssistantsDialog

        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            self.toast_overlay.add_toast(Adw.Toast(title="Please configure backend first"))
            return

        # Build model list for dropdown in editor
        model_list = [(mid, self._get_model_name(mid)) for mid in self._model_ids]

        dialog = AssistantsDialog(
            backend_url=url,
            api_key=key,
            model_list=model_list,
        )
        dialog.connect("assistants-changed", lambda _: self._load_assistants())
        dialog.present(self)

    def _on_manage_models(self, button: Gtk.Button) -> None:
        """Open models management dialog."""
        if not self._models:
            self.toast_overlay.add_toast(Adw.Toast(title="No models loaded"))
            return

        dialog = ModelsDialog(settings_manager=self.settings_manager, models=self._models)
        dialog.connect("models-changed", self._on_models_changed)
        dialog.present(self)

    def _on_models_changed(self, dialog: ModelsDialog) -> None:  # noqa: ARG002 (unused param for signal)
        """Handle models changed signal from management dialog."""
        # Reload models to refresh the dropdown with new sort order
        self._load_models()

    def _get_model_name(self, model_id: str) -> str:
        """Get model display name from ID."""
        # Get from dropdown model
        idx = self._model_ids.index(model_id) if model_id in self._model_ids else -1
        if idx >= 0:
            model = self.model_selector.get_model()
            if model and idx < model.get_n_items():
                return model.get_string(idx)
        return model_id

    def _load_conversations(self, force_refresh: bool = False) -> None:
        """Load conversations using repository pattern.

        Args:
            force_refresh: If True, skip cache and fetch directly from API
        """
        # Ensure repositories are initialized
        if not self._ensure_repositories():
            return

        # 1. Load from local cache first (instant)
        if not force_refresh:
            local_conversations = self.conversation_repo.get_conversations()
            logger.info(f"Loaded {len(local_conversations)} conversations from cache")
            if local_conversations:
                self._update_conversation_list(local_conversations)

        # 2. Skip sync if not forcing and data is fresh
        if not force_refresh and not self.conversation_repo.is_sync_needed():
            return

        # 3. Sync with API (in background)
        self.refresh_btn.set_sensitive(False)
        self._is_loading_conversations = True

        def fetch() -> None:
            import asyncio

            async def do_sync() -> object:
                return await self.conversation_repo.fetch_and_sync_conversations()

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(do_sync())
                loop.close()

                # Schedule ALL UI updates on the main thread
                GLib.idle_add(self._on_sync_complete, result, force_refresh)

            except Exception as e:
                logger.error(f"Error in sync thread: {e}")
                GLib.idle_add(self._on_sync_error, str(e))

        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()

    def _on_sync_complete(self, result: object, force_refresh: bool) -> None:
        """Handle sync completion on the main thread.

        Args:
            result: SyncResult from the repository
            force_refresh: Whether this was a manual refresh
        """
        from nanochat.data.repositories.conversation_repository import SyncResult

        # Re-enable refresh button
        self.refresh_btn.set_sensitive(True)
        self._is_loading_conversations = False

        if not isinstance(result, SyncResult):
            logger.error(f"Unexpected result type: {type(result)}")
            return

        if result.success:
            logger.info(f"Synced {len(result.data)} conversations from API")
            self._update_conversation_list(result.data)

            # Show success toast if this was a manual refresh
            if force_refresh:
                self.toast_overlay.add_toast(
                    Adw.Toast(title=f"Refreshed {len(result.data)} conversations")
                )
        else:
            logger.error(f"Failed to sync conversations: {result.error}")
            self.toast_overlay.add_toast(
                Adw.Toast(title="Failed to refresh conversations")
            )

    def _on_sync_error(self, error: str) -> None:
        """Handle sync error on the main thread.

        Args:
            error: Error message
        """
        self.refresh_btn.set_sensitive(True)
        self._is_loading_conversations = False
        self.toast_overlay.add_toast(Adw.Toast(title=f"Sync error: {error}"))

    def _update_conversation_list(
        self,
        conversations: list[Conversation],
        preserve_full_list: bool = False,
    ) -> None:
        """Update the conversation list UI.

        Args:
            conversations: Conversations to display (may be filtered)
            preserve_full_list: If True, don't update self._conversations
                               (used when filtering)
        """
        if not preserve_full_list:
            self._conversations = conversations
        self._updating_conversation_list = True

        # Block the "row-activated" signal during updates to prevent auto-selection issues
        # (though we're now using click gestures, the listbox still has default behavior)
        try:
            # Clear list
            child = self.conversation_list.get_first_child()
            while child is not None:
                next_child = child.get_next_sibling()
                self.conversation_list.remove(child)
                child = next_child

            # Show "no results" placeholder if search has no matches
            if not conversations and self._search_query:
                placeholder = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=8,
                )
                placeholder.set_valign(Gtk.Align.CENTER)
                placeholder.set_halign(Gtk.Align.CENTER)
                placeholder.set_margin_top(32)
                placeholder.add_css_class("dim-label")

                icon = Gtk.Image.new_from_icon_name("edit-find-symbolic")
                icon.set_pixel_size(48)
                icon.set_opacity(0.5)
                placeholder.append(icon)

                label = Gtk.Label(label=f'No results for "{self._search_query}"')
                label.add_css_class("title-4")
                placeholder.append(label)

                self.conversation_list.append(placeholder)
            else:
                # Add conversations
                for conv in conversations:
                    row = self._create_conversation_row(conv)
                    self.conversation_list.append(row)

        finally:
            self._updating_conversation_list = False

        # Use idle_add to ensure selection state is set AFTER GTK has processed everything
        def set_selection_state() -> bool:
            # If no conversation is active (e.g. startup), ensure no row is selected
            # This prevents GTK's auto-selection of the first item
            if self._current_conversation_id is None:
                self.conversation_list.unselect_all()
            else:
                # Find and select the current conversation
                child = self.conversation_list.get_first_child()
                while child is not None:
                    if isinstance(child, Adw.ActionRow) and child.get_name() == self._current_conversation_id:
                        self.conversation_list.select_row(child)
                        break
                    child = child.get_next_sibling()
            return False  # Don't repeat

        GLib.idle_add(set_selection_state)

    def _create_conversation_row(self, conv: Conversation) -> Adw.ActionRow:
        """Create a row for the conversation list with delete button."""
        row = Adw.ActionRow()
        row.set_title(conv.title)
        row.set_name(conv.id)
        row.add_css_class("conversation-row")

        # Add click gesture controller for single-click activation
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_row_clicked, conv.id)
        row.add_controller(click)

        # Delete button
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("delete-button")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.set_tooltip_text("Delete Conversation")
        delete_btn.set_opacity(0)
        delete_btn.set_sensitive(False)
        delete_btn.connect("clicked", lambda _, c_id=conv.id: self._confirm_delete(c_id))

        row.add_suffix(delete_btn)

        # Hover controller
        controller = Gtk.EventControllerMotion()

        def on_enter(ctrl: Gtk.EventControllerMotion, x: float, y: float) -> None:
            delete_btn.set_opacity(1)
            delete_btn.set_sensitive(True)

        def on_leave(ctrl: Gtk.EventControllerMotion) -> None:
            delete_btn.set_opacity(0)
            delete_btn.set_sensitive(False)

        controller.connect("enter", on_enter)
        controller.connect("leave", on_leave)
        row.add_controller(controller)

        return row

    def _confirm_delete(self, conversation_id: str) -> None:
        """Show confirmation dialog for deletion."""
        # Find conversation title
        title = "this conversation"
        for conv in self._conversations:
            if conv.id == conversation_id:
                title = f'"{conv.title}"'
                break

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Conversation?",
            body=f"Are you sure you want to delete {title}? This cannot be undone.",
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog: Adw.MessageDialog, response: str) -> None:
            if response == "delete":
                self._delete_conversation(conversation_id)

        dialog.connect("response", on_response)
        dialog.present()

    def _delete_conversation(self, conversation_id: str) -> None:
        """Delete conversation from API and DB."""
        # Optimistically remove from UI
        self._remove_conversation_from_ui(conversation_id)

        # If deleted current conversation, clear view
        if self._current_conversation_id == conversation_id:
            self.new_conversation()

        # Delete from DB (must be done on main thread or thread where DB was created)
        try:
            self.database.delete_conversation(conversation_id)
        except Exception as e:
            logger.error(f"Error deleting from DB: {e}")

        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        def delete_task() -> None:
            if not url or not key:
                return

            # Delete from API
            try:
                import asyncio

                from nanochat.api.client import NanoChatClient

                async def do_delete() -> None:
                    async with NanoChatClient(url, key) as client:
                        await client.delete_conversation(conversation_id)

                loop = asyncio.new_event_loop()
                loop.run_until_complete(do_delete())
                loop.close()
            except Exception as e:
                GLib.idle_add(self._show_error, f"Failed to delete from server: {e}")

        thread = threading.Thread(target=delete_task, daemon=True)
        thread.start()

    def _remove_conversation_from_ui(self, conversation_id: str) -> None:
        """Remove conversation row from list."""
        child = self.conversation_list.get_first_child()
        while child is not None:
            row = child
            if isinstance(row, Adw.ActionRow) and row.get_name() == conversation_id:
                self.conversation_list.remove(row)
                break
            child = row.get_next_sibling()

    def _on_row_clicked(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float, conversation_id: str) -> None:
        """Handle row click event."""
        # Only respond to single clicks (n_press == 1)
        if n_press != 1:
            return

        # Skip if we're updating the conversation list programmatically
        if self._updating_conversation_list:
            return

        if conversation_id:
            self._load_messages(conversation_id)

    def _load_messages(self, conversation_id: str) -> None:
        """Load messages for a conversation using repository pattern."""
        # Ensure repositories are initialized
        if not self._ensure_repositories():
            return

        self._current_conversation_id = conversation_id

        # If an API sync is already in progress for this conversation, just wait for it
        if conversation_id in self._syncing_conversations:
            logger.debug(f"API sync already in progress for {conversation_id[:8]}...")
            return

        # 1. Load from cache first (instant)
        cached_messages = self.message_repo.get_messages_cached(conversation_id)
        if cached_messages:
            logger.debug(f"Loaded {len(cached_messages)} messages from cache for {conversation_id[:8]}...")
            self._update_messages_list(cached_messages, from_cache=True)

        # 2. Skip API sync if cache is fresh
        if cached_messages and self.message_repo.is_cache_fresh(conversation_id):
            logger.debug(f"Cache is fresh for {conversation_id[:8]}, skipping API sync")
            return

        # 3. Sync with API in background
        self._syncing_conversations.add(conversation_id)
        logger.debug(f"Syncing {conversation_id[:8]}... with API")

        def fetch() -> None:
            import asyncio

            async def do_sync() -> tuple:
                return await self.message_repo.get_messages_with_sync(conversation_id)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(do_sync())
                loop.close()

                # Schedule UI updates on the main thread
                GLib.idle_add(self._on_messages_sync_complete, conversation_id, result)

            except Exception as e:
                self._syncing_conversations.discard(conversation_id)
                logger.error(f"Failed to load messages: {e}")
                GLib.idle_add(self._on_messages_sync_error, conversation_id, str(e))

        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()

    def _on_messages_sync_complete(
        self, conversation_id: str, result: tuple[list[Message], bool]
    ) -> None:
        """Handle message sync completion on the main thread.

        Args:
            conversation_id: The conversation that was synced
            result: Tuple of (messages, from_cache)
        """
        messages, from_cache = result

        # Remove from in-progress set
        self._syncing_conversations.discard(conversation_id)

        if from_cache:
            logger.debug(f"Using cached messages for {conversation_id[:8]}...")
        else:
            logger.debug(f"Loaded {len(messages)} messages from API for {conversation_id[:8]}...")

        # Only update if we're still looking at the same conversation
        if self._current_conversation_id == conversation_id:
            self._update_messages_list(messages, from_cache=from_cache)

    def _on_messages_sync_error(self, conversation_id: str, error: str) -> None:
        """Handle message sync error on the main thread.

        Args:
            conversation_id: The conversation that failed to sync
            error: Error message
        """
        self._syncing_conversations.discard(conversation_id)
        self.toast_overlay.add_toast(Adw.Toast(title="Failed to load messages"))

    def _show_loading_indicator(self, message: str) -> None:
        """Show loading indicator in the title bar."""
        # Use the model selector to show loading state
        if self.model_selector:
            # Store original title
            if not hasattr(self, "_original_model_title"):
                self._original_model_title = ""
            # We can't easily change the model selector, so we'll use a toast
            self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=2))

    def _hide_loading_indicator(self) -> None:
        """Hide loading indicator."""
        pass  # Toast handles itself via timeout

    def _update_messages_list(self, messages: list[Message], from_cache: bool = True) -> None:
        """Update the messages list UI.

        Args:
            messages: List of messages to display
            from_cache: True if loading from cache (always display),
                       False if from API (skip if unchanged)
        """
        # If loading from API and messages haven't changed, skip update
        if not from_cache:
            if self._messages_equal(self._current_messages, messages):
                logger.debug("Messages unchanged from cache, skipping UI update")
                return
            logger.debug("Messages changed from API, updating UI")

        # Always update from cache
        self._current_messages = messages

        # Clear messages
        child = self.messages_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.messages_list.remove(child)
            child = next_child

        # Add messages
        for msg in messages:
            widget = MessageWidget(role=msg.role, content=msg.content)
            self.messages_list.append(widget)

        # Scroll to bottom
        adjustment = self.messages_scroll.get_vadjustment()
        adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())

    def _messages_equal(self, msgs1: list[Message], msgs2: list[Message]) -> bool:
        """Compare two message lists for equality."""
        if len(msgs1) != len(msgs2):
            return False
        for m1, m2 in zip(msgs1, msgs2):
            if m1.id != m2.id or m1.content != m2.content or m1.role != m2.role:
                return False
        return True

    def _on_refresh_conversations(self, button: Gtk.Button) -> None:
        """Handle refresh button click - force refresh conversations from API."""
        self._load_conversations(force_refresh=True)

    def _load_web_search_settings(self) -> None:
        """Load web search settings from preferences."""
        # Check if settings has web_search attribute (backward compatibility)
        if hasattr(self.settings_manager.settings.chat, "web_search"):
            ws = self.settings_manager.settings.chat.web_search
            self._web_search_enabled = ws.enabled
            self._web_search_mode = ws.mode
            self._web_search_provider = ws.provider

            # Update UI state
            self.web_search_btn.set_active(self._web_search_enabled)
            self.web_search_popover.set_mode(self._web_search_mode)
            self.web_search_popover.set_provider(self._web_search_provider)

    def _save_web_search_settings(self) -> None:
        """Save web search settings to preferences."""
        if hasattr(self.settings_manager.settings.chat, "web_search"):
            self.settings_manager.settings.chat.web_search.enabled = self._web_search_enabled
            self.settings_manager.settings.chat.web_search.mode = self._web_search_mode
            self.settings_manager.settings.chat.web_search.provider = self._web_search_provider
            self.settings_manager.save()

    # ========== Drag and Drop Support ==========

    def _setup_drop_target(self, widget: Gtk.Widget) -> None:
        """Set up drag and drop target for file attachments."""
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("enter", self._on_drop_enter)
        drop_target.connect("leave", self._on_drop_leave)
        drop_target.connect("drop", self._on_file_dropped)
        widget.add_controller(drop_target)

    def _on_drop_enter(
        self,
        drop_target: Gtk.DropTarget,
        x: float,
        y: float,
    ) -> Gdk.DragAction:
        """Handle drag enter event."""
        widget = drop_target.get_widget()
        widget.add_css_class("drop-target-active")
        return Gdk.DragAction.COPY

    def _on_drop_leave(self, drop_target: Gtk.DropTarget) -> None:
        """Handle drag leave event."""
        widget = drop_target.get_widget()
        widget.remove_css_class("drop-target-active")

    def _on_file_dropped(
        self,
        drop_target: Gtk.DropTarget,
        value: Gio.File,
        x: float,
        y: float,
    ) -> bool:
        """Handle file dropped on input area."""
        widget = drop_target.get_widget()
        widget.remove_css_class("drop-target-active")

        file_path = Path(value.get_path())
        self._attach_file(file_path)
        return True

    # ========== Attachment Handling ==========

    def _on_attach_clicked(self, button: Gtk.Button) -> None:
        """Handle attach button click - open file chooser."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Attach Files")

        # Create filter for supported file types
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All Supported Files")
        for ext in IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS:
            all_filter.add_suffix(ext.lstrip("."))

        image_filter = Gtk.FileFilter()
        image_filter.set_name("Images")
        for ext in IMAGE_EXTENSIONS:
            image_filter.add_suffix(ext.lstrip("."))

        doc_filter = Gtk.FileFilter()
        doc_filter.set_name("Documents")
        for ext in DOCUMENT_EXTENSIONS:
            doc_filter.add_suffix(ext.lstrip("."))

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(all_filter)
        filters.append(image_filter)
        filters.append(doc_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(all_filter)

        dialog.open_multiple(self, None, self._on_files_selected)

    def _on_files_selected(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
    ) -> None:
        """Handle files selected from file chooser."""
        try:
            files = dialog.open_multiple_finish(result)
            for i in range(files.get_n_items()):
                gfile = files.get_item(i)
                file_path = Path(gfile.get_path())
                self._attach_file(file_path)
        except GLib.Error as e:
            if e.code != Gtk.DialogError.DISMISSED:
                self.toast_overlay.add_toast(Adw.Toast(title=f"Failed to select files: {e.message}"))

    def _attach_file(self, path: Path) -> None:
        """Attach a file to the pending message."""
        # Validate the file
        is_valid, error = validate_attachment(path)
        if not is_valid:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Cannot attach: {error}"))
            return

        # Create pending attachment
        attachment = create_pending_attachment(path)
        if attachment is None:
            self.toast_overlay.add_toast(Adw.Toast(title="Unsupported file type"))
            return

        # Check for duplicates
        for existing in self._pending_attachments:
            if existing.path == path:
                self.toast_overlay.add_toast(Adw.Toast(title="File already attached"))
                return

        # Add to pending list and UI
        self._pending_attachments.append(attachment)
        self._attachment_preview_bar.add_attachment(attachment)

    def _on_attachment_remove(self, attachment: PendingAttachment) -> None:
        """Handle removal of an attachment."""
        if attachment in self._pending_attachments:
            self._pending_attachments.remove(attachment)
        self._attachment_preview_bar.remove_attachment(attachment)

    def _clear_attachments(self) -> None:
        """Clear all pending attachments."""
        self._pending_attachments.clear()
        self._attachment_preview_bar.clear()

    def _on_web_search_toggled(self, button: Gtk.ToggleButton) -> None:
        """Handle web search toggle button."""
        self._web_search_enabled = button.get_active()

        # Update button appearance
        if self._web_search_enabled:
            button.add_css_class("web-search-active")
            mode_label = "Standard" if self._web_search_mode == "standard" else "Deep"
            button.set_tooltip_text(f"Web search: {mode_label} (right-click to configure)")
        else:
            button.remove_css_class("web-search-active")
            button.set_tooltip_text("Enable web search (right-click to configure)")

        # Save preference
        self._save_web_search_settings()

    def _on_web_search_right_click(
        self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        """Show web search config popover on right-click."""
        self.web_search_popover.popup()

    def _on_web_search_long_press(
        self, gesture: Gtk.GestureLongPress, x: float, y: float
    ) -> None:
        """Show web search config popover on long-press."""
        self.web_search_popover.popup()

    def _on_web_search_settings_changed(
        self, popover: object, mode: str, provider: str
    ) -> None:
        """Handle web search settings change from popover."""
        self._web_search_mode = mode
        self._web_search_provider = provider

        # If mode is "off", disable web search
        if mode == "off":
            self._web_search_enabled = False
            self.web_search_btn.set_active(False)
        elif not self._web_search_enabled:
            # If selecting a non-off mode and search is disabled, enable it
            self._web_search_enabled = True
            self.web_search_btn.set_active(True)

        # Update tooltip
        if self._web_search_enabled:
            mode_label = "Standard" if mode == "standard" else "Deep"
            self.web_search_btn.set_tooltip_text(f"Web search: {mode_label} (right-click to configure)")

        # Save preference
        self._save_web_search_settings()

        # Close popover
        self.web_search_popover.popdown()

    def _on_send(self, widget: Gtk.Widget) -> None:
        """Handle send button click."""
        if self._is_sending:
            return

        text = self.message_entry.get_text().strip()

        # Must have text or attachments
        if not text and not self._pending_attachments:
            return

        # Get selected model
        selected_idx = self.model_selector.get_selected()
        if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(self._model_ids):
            return

        model_id = self._model_ids[selected_idx]

        # Add user message to UI (with attachment indicator if any)
        display_text = text
        if self._pending_attachments:
            attachment_count = len(self._pending_attachments)
            attachment_label = "attachment" if attachment_count == 1 else "attachments"
            if text:
                display_text = f"{text}\n\n📎 {attachment_count} {attachment_label}"
            else:
                display_text = f"📎 {attachment_count} {attachment_label}"

        user_widget = MessageWidget(role="user", content=display_text)
        self.messages_list.append(user_widget)

        # Clear input and disable
        self.message_entry.set_text("")
        self._set_sending_state(True)

        # Capture attachments before clearing
        attachments_to_send = list(self._pending_attachments)
        self._clear_attachments()

        # Start upload and streaming in background
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        def stream_response() -> None:
            import asyncio

            from nanochat.api.client import NanoChatClient
            from nanochat.api.models import (
                GenerateMessageRequest,
                ImageAttachment,
                DocumentAttachment,
            )

            async def do_upload_and_stream() -> None:
                # Upload attachments first
                if attachments_to_send:
                    GLib.idle_add(
                        lambda: self.toast_overlay.add_toast(
                            Adw.Toast(title="Uploading attachments...")
                        )
                    )

                    async with NanoChatClient(url, key) as client:
                        for attachment in attachments_to_send:
                            if attachment.is_uploaded:
                                continue
                            try:
                                content = attachment.path.read_bytes()
                                storage_id, file_url = await client.upload_file(
                                    content,
                                    attachment.filename,
                                    attachment.mime_type,
                                )
                                attachment.storage_id = storage_id
                                
                                # Handle URL construction based on type
                                if attachment.attachment_type == AttachmentType.IMAGE:
                                    # Images need full URL for external models (e.g. OpenAI)
                                    if file_url.startswith('/'):
                                        file_url = f"{url}{file_url}"
                                    attachment.url = file_url
                                else:
                                    # Documents are processed by backend - try relative URL
                                    # to avoid potential DNS/loopback issues
                                    attachment.url = file_url
                                    
                            except Exception as e:
                                attachment.upload_error = str(e)
                                GLib.idle_add(
                                    self._show_error,
                                    f"Failed to upload {attachment.filename}: {e}"
                                )

                # Build attachment lists
                images = []
                documents = []

                for attachment in attachments_to_send:
                    if not attachment.is_uploaded:
                        continue

                    if attachment.attachment_type == AttachmentType.IMAGE:
                        images.append(ImageAttachment(
                            url=attachment.url,
                            storage_id=attachment.storage_id,
                            file_name=attachment.filename,
                        ))
                    else:
                        documents.append(DocumentAttachment(
                            url=attachment.url,
                            storage_id=attachment.storage_id,
                            file_name=attachment.filename,
                            file_type=attachment.document_type.value if attachment.document_type else "text",
                        ))

                # Mutable state for accumulating content
                state = {"accumulated_content": "", "conversation_id": None}

                def on_event(event_type: str, event_data: dict) -> None:
                    """Handle SSE events from the stream."""
                    if event_type == "message_start":
                        # Set conversation ID from message_start event
                        conv_id = event_data.get("conversation_id")
                        if conv_id:
                            state["conversation_id"] = conv_id
                            GLib.idle_add(self._set_conversation_id, conv_id)

                    elif event_type == "delta":
                        # Accumulate content and update UI
                        delta_content = event_data.get("content", "")
                        state["accumulated_content"] += delta_content
                        GLib.idle_add(self._update_assistant_message, state["accumulated_content"])

                    elif event_type == "message_complete":
                        # Generation complete - refresh title only if it's a new chat
                        conv_id = state.get("conversation_id")
                        if conv_id:
                            def schedule_title_refresh() -> bool:
                                """Schedule title refresh on main thread."""
                                def do_refresh() -> bool:
                                    self._refresh_conversation_title(conv_id)
                                    return False  # Don't repeat
                                # Schedule refresh after 1 second delay
                                GLib.timeout_add(1000, do_refresh)
                                return False  # Don't repeat idle_add
                            # Use idle_add first to get to main thread, then timeout_add
                            GLib.idle_add(schedule_title_refresh)

                    elif event_type == "error":
                        # Handle error event
                        error_msg = event_data.get("error", "Unknown error")
                        GLib.idle_add(self._show_error, error_msg)

                # Build request
                request_kwargs = {
                    "message": text if text else None,
                    "model_id": model_id,
                    "conversation_id": self._current_conversation_id,
                }

                if self._current_assistant_id:
                    request_kwargs["assistant_id"] = self._current_assistant_id

                if self._web_search_enabled and self._web_search_mode != "off":
                    request_kwargs["web_search_enabled"] = True
                    request_kwargs["web_search_mode"] = self._web_search_mode
                    request_kwargs["web_search_provider"] = self._web_search_provider

                if images:
                    request_kwargs["images"] = images
                if documents:
                    request_kwargs["documents"] = documents

                request = GenerateMessageRequest(**request_kwargs)

                try:
                    async with NanoChatClient(url, key) as client:
                        await client.stream_generate_message(request, on_event)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    GLib.idle_add(self._show_error, str(e))
                finally:
                    GLib.idle_add(self._set_sending_state, False)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(do_upload_and_stream())
                loop.close()
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
                GLib.idle_add(self._set_sending_state, False)

        thread = threading.Thread(target=stream_response, daemon=True)
        thread.start()

    def _set_sending_state(self, is_sending: bool) -> None:
        """Set the sending state of the UI."""
        self._is_sending = is_sending
        self.message_entry.set_sensitive(not is_sending)
        self.send_btn.set_sensitive(not is_sending)

        if is_sending:
            self.message_entry.set_placeholder_text("Generating response...")
            self.send_btn.add_css_class("generating")
            self.send_btn.set_icon_name("media-playback-stop-symbolic")
            self.send_btn.set_tooltip_text("Stop generating")
        else:
            self.message_entry.set_placeholder_text("Type a message...")
            self.send_btn.remove_css_class("generating")
            self.send_btn.set_icon_name("mail-send-symbolic")
            self.send_btn.set_tooltip_text("Send Message")

    def _update_assistant_message(self, content: str) -> None:
        """Update or create assistant message widget."""
        # Find last assistant message
        child = self.messages_list.get_last_child()
        if child and isinstance(child, MessageWidget) and child.role == "assistant":
            # Update existing
            child.update_content(content)
        else:
            # Create new
            widget = MessageWidget(role="assistant", content=content)
            self.messages_list.append(widget)

    def _show_error(self, error: str) -> None:
        """Show error message to user and log it."""
        logger.error(f"Error: {error}")

        toast = Adw.Toast.new(f"Error: {error}")
        toast.set_timeout(5)  # 5 seconds
        self.toast_overlay.add_toast(toast)

    def _set_conversation_id(self, conversation_id: str) -> None:
        """Set the current conversation ID."""
        self._current_conversation_id = conversation_id

    def _refresh_conversation_title(self, conversation_id: str) -> None:
        """Refresh the title of a specific conversation if it's 'New Chat' or new.

        Only fetches from API and updates the sidebar if the current title
        is 'New Chat' or if the conversation isn't in our list yet.
        """
        # Find the current title in our conversations list
        current_title = None
        for conv in self._conversations:
            if conv.id == conversation_id:
                current_title = conv.title
                break

        # Only refresh if:
        # - conversation not in list yet (new conversation)
        # - title is "New Chat"
        if current_title is not None and current_title != "New Chat":
            return

        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

        def fetch_and_update() -> None:
            from nanochat.api.client import NanoChatClient

            async def get_conv() -> object:
                async with NanoChatClient(url, key) as client:
                    return await client.get_conversation(conversation_id)

            try:
                loop = asyncio.new_event_loop()
                conv = loop.run_until_complete(get_conv())
                loop.close()

                # Update on main thread
                GLib.idle_add(self._update_or_add_conversation_row, conv)

            except Exception as e:
                logger.error(f"Failed to refresh conversation title: {e}")

        thread = threading.Thread(target=fetch_and_update, daemon=True)
        thread.start()

    def _update_or_add_conversation_row(self, conv: Conversation) -> None:
        """Update or add a conversation row in the sidebar."""
        conversation_id = conv.id
        new_title = conv.title

        # Check if conversation exists in list
        found = False
        for i, existing in enumerate(self._conversations):
            if existing.id == conversation_id:
                # Replace with updated conversation
                self._conversations[i] = conv
                found = True
                break

        # Save to database (needed for foreign key constraints when saving messages)
        try:
            self.database.save_conversations([conv])
        except Exception as e:
            logger.error(f"Error saving conversation to DB: {e}")

        if not found:
            # Add to beginning of list (most recent)
            self._conversations.insert(0, conv)
            # Create and add new row at the top
            row = self._create_conversation_row(conv)
            self.conversation_list.prepend(row)
            # Select the new row
            self.conversation_list.select_row(row)
        else:
            # Find and update the existing row in the UI
            child = self.conversation_list.get_first_child()
            while child is not None:
                if isinstance(child, Adw.ActionRow) and child.get_name() == conversation_id:
                    child.set_title(new_title)
                    break
                child = child.get_next_sibling()

    def new_conversation(self) -> None:
        """Start a new conversation."""
        # Clear current conversation
        self._current_conversation_id = None

        # Clear messages
        child = self.messages_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.messages_list.remove(child)
            child = next_child

        # Clear attachments
        self._clear_attachments()

        # Clear selection in list
        self.conversation_list.unselect_all()

    def reload_data(self) -> None:
        """Reload conversations and models (called after setup)."""
        self._load_models()
        self._load_assistants()
        self._load_conversations()
