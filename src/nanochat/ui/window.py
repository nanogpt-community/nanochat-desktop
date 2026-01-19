"""Main application window."""

import asyncio
import logging
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk

from nanochat.api.models import Conversation, Message
from nanochat.data.database import Database
from nanochat.data.secrets import SecretsManager
from nanochat.data.settings import SettingsManager
from nanochat.ui.message_widget import MessageWidget

logger = logging.getLogger(__name__)


class NanoChatWindow(Adw.ApplicationWindow):  # type: ignore[misc]
    """Main window with sidebar and chat area."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        secrets_manager: SecretsManager,
        database: Database,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)

        self.settings_manager = settings_manager
        self.secrets_manager = secrets_manager
        self.database = database
        self._model_ids: list[str] = []
        self._conversations: list[Conversation] = []
        self._current_conversation_id: str | None = None
        self._current_messages: list[Message] = []
        self._is_sending: bool = False
        # Track when we last fetched each conversation from API (for cache freshness)
        self._conversation_fetch_time: dict[str, float] = {}
        self._cache_stale_seconds: int = 300  # 5 minutes
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

        self.set_default_size(1200, 800)
        self.set_title("NanoChat")

        self._setup_ui()
        self._setup_keyboard_shortcuts()

        # Connect to map signal for loading after UI is ready
        self.connect("map", self._on_map)

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

        # Model selector dropdown
        self.model_selector = Gtk.DropDown()
        self.model_selector.set_tooltip_text("Select Model")
        self._model_change_handler = self.model_selector.connect(
            "notify::selected", self._on_model_changed
        )
        header.set_title_widget(self.model_selector)

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
        """Create message input area."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_bottom(12)
        box.add_css_class("linked")
        box.add_css_class("chat-input-box")

        # Text entry
        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text("Type a message...")
        self.message_entry.set_hexpand(True)
        self.message_entry.set_sensitive(True)
        self.message_entry.connect("activate", self._on_send)
        box.append(self.message_entry)

        # Send button
        self.send_btn = Gtk.Button(icon_name="mail-send-symbolic")
        self.send_btn.set_tooltip_text("Send Message")
        self.send_btn.add_css_class("suggested-action")
        self.send_btn.add_css_class("send-button")
        self.send_btn.set_sensitive(True)
        self.send_btn.connect("clicked", self._on_send)
        box.append(self.send_btn)

        return box

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

        def fetch() -> list[object] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_models() -> list[object]:
                async with NanoChatClient(url, key) as client:
                    models = await client.get_models()
                    return [m for m in models if m.enabled]

            try:
                loop = asyncio.new_event_loop()
                models = loop.run_until_complete(get_models())
                loop.close()
                return models
            except Exception as e:
                return e

        def on_complete(models: list[object] | Exception) -> None:
            if isinstance(models, Exception):
                logger.error(f"Failed to load models: {models}")
                return

            model_names = Gtk.StringList()
            self._model_ids = []
            for model in models:
                model_names.append(model.name)  # type: ignore[attr-defined]
                self._model_ids.append(model.id)  # type: ignore[attr-defined]

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

    def _load_conversations(self, force_refresh: bool = False) -> None:
        """Load conversations from DB and then sync with API.

        Args:
            force_refresh: If True, skip cache and fetch directly from API
        """
        # 1. Load from local DB first (should be instant), unless force refresh
        if not force_refresh:
            try:
                local_conversations = self.database.get_conversations()
                logger.info(f"Loaded {len(local_conversations)} conversations from cache")
                if local_conversations:
                    self._update_conversation_list(local_conversations)
            except Exception as e:
                logger.error(f"Error loading local conversations: {e}")

        # 2. Sync with API (in background)
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

        # Show refresh button as loading
        self.refresh_btn.set_sensitive(False)
        self._is_loading_conversations = True

        def fetch() -> list[Conversation] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_convs() -> list[Conversation]:
                async with NanoChatClient(url, key) as client:
                    return await client.get_conversations()

            try:
                loop = asyncio.new_event_loop()
                convs = loop.run_until_complete(get_convs())
                loop.close()
                return convs
            except Exception as e:
                return e

        def on_complete(conversations: list[Conversation] | Exception) -> None:
            # Re-enable refresh button
            self.refresh_btn.set_sensitive(True)
            self._is_loading_conversations = False

            if isinstance(conversations, Exception):
                logger.error(f"Failed to load conversations from API: {conversations}")
                # Show toast for error
                self.toast_overlay.add_toast(Adw.Toast(title="Failed to refresh conversations"))
                return

            logger.info(f"Loaded {len(conversations)} conversations from API")

            # Save to DB
            try:
                self.database.save_conversations(conversations)
                logger.debug(f"Saved {len(conversations)} conversations to cache")
            except Exception as e:
                logger.error(f"Error saving conversations to DB: {e}")

            self._update_conversation_list(conversations)

            # Show success toast if this was a manual refresh
            if force_refresh:
                self.toast_overlay.add_toast(
                    Adw.Toast(title=f"Refreshed {len(conversations)} conversations")
                )

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

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
        """Load messages for a conversation from DB and optionally sync with API."""
        import time

        self._current_conversation_id = conversation_id

        # If an API sync is already in progress for this conversation, just wait for it
        if conversation_id in self._syncing_conversations:
            logger.debug(f"API sync already in progress for {conversation_id[:8]}...")
            return

        # Check cache freshness BEFORE loading (to know if we should sync)
        current_time = time.time()
        last_fetch = self._conversation_fetch_time.get(conversation_id, 0)
        cache_is_stale = (current_time - last_fetch) > self._cache_stale_seconds

        # 1. Load from DB first (should be instant)
        local_messages = []
        try:
            local_messages = self.database.get_messages(conversation_id)
            logger.debug(f"Loaded {len(local_messages)} messages from cache for {conversation_id[:8]}...")
        except Exception as e:
            logger.error(f"Error loading local messages: {e}")

        # 2. Update UI with cached messages (if any) - defer API sync to allow UI to render
        has_messages = len(local_messages) > 0
        if has_messages:
            self._update_messages_list(local_messages, from_cache=True)

        # 3. Skip API sync if cache is fresh (has data and not stale)
        if has_messages and not cache_is_stale:
            logger.debug(f"Cache is fresh for {conversation_id[:8]}, skipping API sync")
            # Update fetch time so we know we've seen this conversation
            if conversation_id not in self._conversation_fetch_time:
                self._conversation_fetch_time[conversation_id] = current_time
            return

        # 4. Defer the API sync to run after the UI has rendered
        def start_api_sync() -> bool:
            self._sync_messages_from_api(conversation_id, cache_is_stale)
            return False  # Don't repeat

        GLib.idle_add(start_api_sync)

    def _sync_messages_from_api(self, conversation_id: str, cache_is_stale: bool) -> None:
        """Sync messages from API in background thread."""
        import time

        # Skip if already syncing this conversation
        if conversation_id in self._syncing_conversations:
            logger.debug(
                f"Skipping duplicate sync for {conversation_id[:8]}... (already in progress)"
            )
            return

        self._syncing_conversations.add(conversation_id)
        logger.debug(f"Syncing {conversation_id[:8]}... with API")

        # Show loading indicator
        self._show_loading_indicator("Retrieving messages...")

        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            self._hide_loading_indicator()
            return

        current_time = time.time()

        def fetch() -> list[Message] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_msgs() -> list[Message]:
                async with NanoChatClient(url, key) as client:
                    return await client.get_messages(conversation_id)

            try:
                loop = asyncio.new_event_loop()
                msgs = loop.run_until_complete(get_msgs())
                loop.close()
                return msgs
            except Exception as e:
                return e

        def on_complete(messages: list[Message] | Exception) -> None:
            self._hide_loading_indicator()
            # Remove from in-progress set
            self._syncing_conversations.discard(conversation_id)

            if isinstance(messages, Exception):
                logger.error(f"Failed to load messages from API: {messages}")
                self.toast_overlay.add_toast(Adw.Toast(title="Failed to load messages"))
                return

            # Update fetch time FIRST before any UI updates
            self._conversation_fetch_time[conversation_id] = time.time()

            logger.debug(f"Loaded {len(messages)} messages from API for {conversation_id[:8]}...")

            # Save to DB
            try:
                self.database.save_messages(messages)
            except Exception as e:
                logger.error(f"Error saving messages to DB: {e}")

            # Only update if we're still looking at the same conversation
            if self._current_conversation_id == conversation_id:
                self._update_messages_list(messages, from_cache=False)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

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
        # Clear cache timestamps to force refresh
        self._conversation_fetch_time.clear()
        # Reload conversations
        self._load_conversations(force_refresh=True)

    def _on_send(self, widget: Gtk.Widget) -> None:
        """Handle send button click."""
        if self._is_sending:
            return

        text = self.message_entry.get_text().strip()
        if not text:
            return

        # Get selected model
        selected_idx = self.model_selector.get_selected()
        if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(self._model_ids):
            return

        model_id = self._model_ids[selected_idx]

        # Add user message to UI
        user_widget = MessageWidget(role="user", content=text)
        self.messages_list.append(user_widget)

        # Clear input and disable
        self.message_entry.set_text("")
        self._set_sending_state(True)

        # Start SSE streaming
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        def stream_response() -> None:
            from nanochat.api.client import NanoChatClient
            from nanochat.api.models import GenerateMessageRequest

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

            async def do_stream() -> None:
                request = GenerateMessageRequest(
                    message=text,
                    model_id=model_id,
                    conversation_id=self._current_conversation_id,
                )

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
                loop.run_until_complete(do_stream())
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

        # Clear selection in list
        self.conversation_list.unselect_all()

    def reload_data(self) -> None:
        """Reload conversations and models (called after setup)."""
        self._load_models()
        self._load_conversations()
