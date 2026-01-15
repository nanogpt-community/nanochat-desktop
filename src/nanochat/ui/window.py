"""Main application window."""

import asyncio
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

from nanochat.ui.message_widget import MessageWidget
from nanochat.data.database import Database
from nanochat.data.settings import SettingsManager
from nanochat.data.secrets import SecretsManager
from nanochat.api.models import Conversation, Message


class NanoChatWindow(Adw.ApplicationWindow):  # type: ignore[misc]
    """Main window with sidebar and chat area."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        secrets_manager: SecretsManager,
        database: Database,
        **kwargs: object
    ) -> None:
        super().__init__(**kwargs)

        self.settings_manager = settings_manager
        self.secrets_manager = secrets_manager
        self.database = database
        self._model_ids: list[str] = []
        self._conversations: list[Conversation] = []
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
        self.conversation_list.connect("selected-rows-changed", self._on_conversation_selected)

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
        self._model_change_handler = self.model_selector.connect("notify::selected", self._on_model_changed)
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
                print(f"Failed to load models: {models}")
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

    def _load_conversations(self) -> None:
        """Load conversations from DB and then sync with API."""
        # 1. Load from local DB first
        try:
            local_conversations = self.database.get_conversations()
            self._update_conversation_list(local_conversations)
        except Exception as e:
            print(f"Error loading local conversations: {e}")

        # 2. Sync with API
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

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
            if isinstance(conversations, Exception):
                print(f"Failed to load conversations: {conversations}")
                return

            # Save to DB
            try:
                self.database.save_conversations(conversations)
            except Exception as e:
                print(f"Error saving conversations to DB: {e}")

            self._update_conversation_list(conversations)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _update_conversation_list(self, conversations: list[Conversation]) -> None:
        """Update the conversation list UI."""
        self._conversations = conversations

        # Clear list
        child = self.conversation_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.conversation_list.remove(child)
            child = next_child

        # Add conversations
        for conv in conversations:
            row = self._create_conversation_row(conv)
            self.conversation_list.append(row)

            # Restore selection if this is the current conversation
            if self._current_conversation_id and conv.id == self._current_conversation_id:
                self.conversation_list.select_row(row)

    def _create_conversation_row(self, conv: Conversation) -> Adw.ActionRow:
        """Create a row for the conversation list with delete button."""
        row = Adw.ActionRow()
        row.set_title(conv.title)
        row.set_name(conv.id)

        # Delete button
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.add_css_class("flat")
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
            print(f"Error deleting from DB: {e}")

        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        def delete_task() -> None:
            if not url or not key:
                return

            # Delete from API
            try:
                from nanochat.api.client import NanoChatClient
                import asyncio
                
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

    def _on_conversation_selected(self, list_box: Gtk.ListBox) -> None:
        """Handle conversation selection."""
        selected_row = list_box.get_selected_row()
        if selected_row:
            conv_id = selected_row.get_name()  # type: ignore[attr-defined]
            self._load_messages(conv_id)

    def _load_messages(self, conversation_id: str) -> None:
        """Load messages for a conversation from DB and then sync."""
        self._current_conversation_id = conversation_id
        
        # 1. Load from DB
        try:
            local_messages = self.database.get_messages(conversation_id)
            self._update_messages_list(local_messages)
        except Exception as e:
            print(f"Error loading local messages: {e}")

        # 2. Sync with API
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        if not url or not key:
            return

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
            if isinstance(messages, Exception):
                print(f"Failed to load messages: {messages}")
                return

            # Save to DB
            try:
                self.database.save_messages(messages)
            except Exception as e:
                print(f"Error saving messages to DB: {e}")

            # Only update if we're still looking at the same conversation
            if self._current_conversation_id == conversation_id:
                self._update_messages_list(messages)

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _update_messages_list(self, messages: list[Message]) -> None:
        """Update the messages list UI."""
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

        # Start polling for response
        url = self.settings_manager.settings.server.backend_url
        key = self.secrets_manager.get_api_key()

        def stream_response() -> None:
            from nanochat.api.client import NanoChatClient
            from nanochat.api.models import GenerateMessageRequest

            async def do_poll() -> None:
                request = GenerateMessageRequest(
                    message=text,
                    model_id=model_id,
                    conversation_id=self._current_conversation_id,
                )

                try:
                    # Send the message (returns immediately with conversation_id)
                    async with NanoChatClient(url, key) as client:
                        response = await client._request("POST", "/api/generate-message", json=request.model_dump(exclude_none=True, by_alias=True))

                        if "conversation_id" in response:
                            new_conv_id = response["conversation_id"]
                            GLib.idle_add(self._set_conversation_id, new_conv_id)

                            # Poll for messages and conversation status
                            last_assistant_content = ""
                            last_message_count = 0
                            max_polls = 600  # 5 minutes at 0.5s intervals
                            poll_count = 0

                            while poll_count < max_polls:
                                poll_count += 1
                                await asyncio.sleep(0.5)

                                # Check conversation status (generating field)
                                try:
                                    conversation = await client.get_conversation(new_conv_id)
                                except Exception:
                                    # If we can't get conversation, fall back to checking messages only
                                    conversation = None

                                # Get messages
                                messages = await client.get_messages(new_conv_id)

                                # Check for new/updated messages
                                if len(messages) > 0:
                                    # Look for assistant messages
                                    for msg in messages:
                                        if msg.role == "assistant" and msg.content:
                                            # Only update if content has changed
                                            if msg.content != last_assistant_content:
                                                last_assistant_content = msg.content
                                                GLib.idle_add(self._update_assistant_message, msg.content)

                                    # Check if generation is complete
                                    # - conversation.generating is False, OR
                                    # - we have an even number of messages (user+assistant pairs) with complete content
                                    generation_complete = False

                                    if conversation is not None:
                                        if not conversation.generating:
                                            generation_complete = True
                                    else:
                                        # Fallback: check if last message is a complete assistant response
                                        if len(messages) >= 2 and messages[-1].role == "assistant" and messages[-1].content:
                                            generation_complete = True

                                    if generation_complete:
                                        # Final update to ensure we have the latest content
                                        if messages[-1].role == "assistant" and messages[-1].content:
                                            GLib.idle_add(self._update_assistant_message, messages[-1].content)
                                        GLib.idle_add(self._load_conversations)
                                        break

                            # If max polls reached, still reload conversations
                            if poll_count >= max_polls:
                                GLib.idle_add(self._load_conversations)

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    GLib.idle_add(self._show_error, str(e))
                finally:
                    GLib.idle_add(self._set_sending_state, False)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(do_poll())
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
        """Show error message to user and log it."""
        print(f"Error: {error}")
        
        toast = Adw.Toast.new(f"Error: {error}")
        toast.set_timeout(5)  # 5 seconds
        self.toast_overlay.add_toast(toast)

    def _set_conversation_id(self, conversation_id: str) -> None:
        """Set the current conversation ID."""
        self._current_conversation_id = conversation_id

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
