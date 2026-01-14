"""Main application window."""

import asyncio
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

from nanochat.ui.message_widget import MessageWidget


class NanoChatWindow(Adw.ApplicationWindow):  # type: ignore[misc]
    """Main window with sidebar and chat area."""

    def __init__(self, settings_manager: object, secrets_manager: object, **kwargs: object) -> None:
        super().__init__(**kwargs)

        self.settings_manager = settings_manager
        self.secrets_manager = secrets_manager
        self._model_ids: list[str] = []
        self._conversations: list[object] = []
        self._current_conversation_id: str | None = None
        self._is_sending: bool = False

        self.set_default_size(1200, 800)
        self.set_title("NanoChat")

        self._setup_ui()

        # Connect to map signal for loading after UI is ready
        self.connect("map", self._on_map)

    def _setup_ui(self) -> None:
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
        self.conversation_list.connect("row-activated", self._on_conversation_selected)

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
        self.send_btn.set_sensitive(True)
        self.send_btn.connect("clicked", self._on_send)
        box.append(self.send_btn)

        return box

    def _on_map(self, widget: Gtk.Widget) -> None:
        """Handle window map event - load data after UI is ready."""
        if not self._model_ids:
            self._load_models()
        self._load_conversations()

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
                print(f"Failed to load models: {models}")
                return

            model_names = Gtk.StringList()
            self._model_ids = []
            for model in models:
                model_names.append(model.name)  # type: ignore[attr-defined]
                self._model_ids.append(model.id)  # type: ignore[attr-defined]

            self.model_selector.set_model(model_names)

            default = self.settings_manager.settings.chat.default_model
            if default in self._model_ids:
                idx = self._model_ids.index(default)
                self.model_selector.set_selected(idx)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _load_conversations(self) -> None:
        """Load conversations from API."""
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

        def fetch() -> list[object] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_convs() -> list[object]:
                async with NanoChatClient(url, key) as client:
                    return await client.get_conversations()

            try:
                loop = asyncio.new_event_loop()
                convs = loop.run_until_complete(get_convs())
                loop.close()
                return convs
            except Exception as e:
                return e

        def on_complete(conversations: list[object] | Exception) -> None:
            if isinstance(conversations, Exception):
                print(f"Failed to load conversations: {conversations}")
                return

            self._conversations = conversations

            # Clear list
            child = self.conversation_list.get_first_child()
            while child is not None:
                next_child = child.get_next_sibling()
                self.conversation_list.remove(child)
                child = next_child

            # Add conversations
            for conv in conversations:
                row = Adw.ActionRow()
                row.set_title(conv.title)  # type: ignore[attr-defined]
                # Don't show message count since API returns 0
                row.conv_id = conv.id  # type: ignore[attr-defined]
                self.conversation_list.append(row)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _on_conversation_selected(self, list_box: Gtk.ListBox, row: Adw.ActionRow) -> None:
        """Handle conversation selection."""
        conv_id = row.conv_id  # type: ignore[attr-defined]
        self._load_messages(conv_id)

    def _load_messages(self, conversation_id: str) -> None:
        """Load messages for a conversation."""
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        self._current_conversation_id = conversation_id

        if not url or not key:
            return

        def fetch() -> list[object] | Exception:
            from nanochat.api.client import NanoChatClient

            async def get_msgs() -> list[object]:
                async with NanoChatClient(url, key) as client:
                    return await client.get_messages(conversation_id)

            try:
                loop = asyncio.new_event_loop()
                msgs = loop.run_until_complete(get_msgs())
                loop.close()
                return msgs
            except Exception as e:
                return e

        def on_complete(messages: list[object] | Exception) -> None:
            if isinstance(messages, Exception):
                print(f"Failed to load messages: {messages}")
                return

            # Clear messages
            child = self.messages_list.get_first_child()
            while child is not None:
                next_child = child.get_next_sibling()
                self.messages_list.remove(child)
                child = next_child

            # Add messages
            for msg in messages:
                widget = MessageWidget(role=msg.role, content=msg.content)  # type: ignore[attr-defined]
                self.messages_list.append(widget)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

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

        # Start streaming response
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        def stream_response() -> None:
            from nanochat.api.client import (
                NanoChatClient,
                StreamEvent,
                ContentEvent,
                StreamCompleteEvent,
                StreamErrorEvent,
                GenerateMessageRequest,
            )

            async def do_stream() -> str | None:
                request = GenerateMessageRequest(
                    message=text,
                    model_id=model_id,
                    conversation_id=self._current_conversation_id,
                )

                async with NanoChatClient(url, key) as client:
                    # Create placeholder for assistant message
                    assistant_content = [""]

                    def update_ui(content: str) -> None:
                        assistant_content[0] = content
                        GLib.idle_add(self._update_assistant_message, content)

                    async for event in client.stream_message(request):
                        if isinstance(event, ContentEvent):
                            update_ui(assistant_content[0] + event.content)
                        elif isinstance(event, StreamCompleteEvent):
                            # Reload conversations to get the new/updated one
                            GLib.idle_add(self._load_conversations)
                            break
                        elif isinstance(event, StreamErrorEvent):
                            GLib.idle_add(self._show_error, event.error)
                            break

                    return assistant_content[0]

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(do_stream())
                loop.close()
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
            finally:
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
        else:
            self.message_entry.set_placeholder_text("Type a message...")

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
        """Show error message."""
        print(f"Error: {error}")

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
