"""Assistants management dialog."""

import asyncio
import logging
import threading
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, GObject, Gtk

from nanochat.api.client import NanoChatClient
from nanochat.api.models import (
    Assistant,
    CreateAssistantRequest,
    UpdateAssistantRequest,
)
from nanochat.ui.assistant_editor import AssistantEditorDialog

logger = logging.getLogger(__name__)


class AssistantsDialog(Adw.Dialog):
    """Dialog for managing assistants."""

    __gtype_name__ = "AssistantsDialog"

    # Signal emitted when assistants change (for refreshing UI elsewhere)
    __gsignals__ = {
        "assistants-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(
        self,
        backend_url: str,
        api_key: str,
        model_list: list[tuple[str, str]] | None = None,
    ) -> None:
        """Initialize the assistants dialog.

        Args:
            backend_url: API backend URL
            api_key: API authentication key
            model_list: List of (model_id, model_name) tuples
        """
        super().__init__()

        self._backend_url = backend_url
        self._api_key = api_key
        self._model_list = model_list or []
        self._assistants: list[Assistant] = []
        self._assistant_rows: list[Adw.ActionRow] = []  # Track rows we create

        self.set_title("Assistants")
        self.set_content_width(500)
        self.set_content_height(600)

        self._setup_ui()
        self._load_assistants()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        # Main toolbar view
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        # Close button
        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda _: self.close())
        header.pack_start(close_btn)

        # New assistant button
        new_btn = Gtk.Button(icon_name="list-add-symbolic")
        new_btn.set_tooltip_text("New Assistant")
        new_btn.connect("clicked", self._on_new_assistant)
        header.pack_end(new_btn)

        toolbar_view.add_top_bar(header)

        # Toast overlay for notifications
        self._toast_overlay = Adw.ToastOverlay()

        # Content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._content_box.set_margin_top(12)
        self._content_box.set_margin_bottom(12)
        self._content_box.set_margin_start(12)
        self._content_box.set_margin_end(12)

        # Loading spinner (shown initially)
        self._loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._loading_box.set_valign(Gtk.Align.CENTER)
        self._loading_box.set_vexpand(True)

        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        self._loading_box.append(spinner)

        loading_label = Gtk.Label(label="Loading assistants...")
        loading_label.add_css_class("dim-label")
        self._loading_box.append(loading_label)

        self._content_box.append(self._loading_box)

        # Assistants list (hidden initially)
        self._assistants_group = Adw.PreferencesGroup()
        self._assistants_group.set_visible(False)

        self._content_box.append(self._assistants_group)

        scrolled.set_child(self._content_box)
        self._toast_overlay.set_child(scrolled)
        toolbar_view.set_content(self._toast_overlay)

        self.set_child(toolbar_view)

    def _load_assistants(self) -> None:
        """Load assistants from API."""
        def fetch() -> list[Assistant] | Exception:
            async def get_assistants() -> list[Assistant]:
                async with NanoChatClient(self._backend_url, self._api_key) as client:
                    return await client.get_assistants()

            try:
                loop = asyncio.new_event_loop()
                assistants = loop.run_until_complete(get_assistants())
                loop.close()
                return assistants
            except Exception as e:
                return e

        def on_complete(result: list[Assistant] | Exception) -> None:
            self._loading_box.set_visible(False)
            self._assistants_group.set_visible(True)

            if isinstance(result, Exception):
                logger.error(f"Failed to load assistants: {result}")
                self._toast_overlay.add_toast(Adw.Toast(title="Failed to load assistants"))
                return

            self._assistants = result
            self._update_assistants_list()

        def thread_func() -> None:
            result = fetch()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _update_assistants_list(self) -> None:
        """Update the assistants list UI."""
        # Remove only the rows we created
        for row in self._assistant_rows:
            self._assistants_group.remove(row)
        self._assistant_rows.clear()

        # Add assistant rows and track them
        for assistant in self._assistants:
            row = self._create_assistant_row(assistant)
            self._assistants_group.add(row)
            self._assistant_rows.append(row)

    def _create_assistant_row(self, assistant: Assistant) -> Adw.ActionRow:
        """Create a row for an assistant."""
        row = Adw.ActionRow()
        row.set_title(assistant.name)

        # Build subtitle with details
        subtitle_parts = []
        if assistant.is_default:
            subtitle_parts.append("Default")
        if assistant.description:
            subtitle_parts.append(assistant.description)
        if subtitle_parts:
            row.set_subtitle(" • ".join(subtitle_parts))

        # Default indicator
        if assistant.is_default:
            default_icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
            default_icon.add_css_class("accent")
            default_icon.set_tooltip_text("Default Assistant")
            row.add_prefix(default_icon)

        # Button box for actions
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        button_box.set_valign(Gtk.Align.CENTER)

        # Set as default button (only if not already default)
        if not assistant.is_default:
            default_btn = Gtk.Button(icon_name="emblem-default-symbolic")
            default_btn.add_css_class("flat")
            default_btn.set_tooltip_text("Set as Default")
            default_btn.connect("clicked", lambda _, a=assistant: self._on_set_default(a))
            button_box.append(default_btn)

        # Edit button
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.add_css_class("flat")
        edit_btn.set_tooltip_text("Edit")
        edit_btn.connect("clicked", lambda _, a=assistant: self._on_edit_assistant(a))
        button_box.append(edit_btn)

        # Delete button (disabled for default assistant)
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.set_tooltip_text("Delete")
        delete_btn.set_sensitive(not assistant.is_default)
        if assistant.is_default:
            delete_btn.set_tooltip_text("Cannot delete default assistant")
        delete_btn.connect("clicked", lambda _, a=assistant: self._on_delete_assistant(a))
        button_box.append(delete_btn)

        row.add_suffix(button_box)

        return row

    def _on_new_assistant(self, button: Gtk.Button) -> None:
        """Handle new assistant button click."""
        editor = AssistantEditorDialog(assistant=None, model_list=self._model_list)
        editor.connect("save-requested", self._on_create_assistant)
        editor.present(self)

    def _on_edit_assistant(self, assistant: Assistant) -> None:
        """Handle edit assistant button click."""
        editor = AssistantEditorDialog(assistant=assistant, model_list=self._model_list)
        editor.connect("save-requested", lambda dialog, *args: self._on_update_assistant(assistant.id, dialog, *args))
        editor.present(self)

    def _on_create_assistant(
        self,
        dialog: AssistantEditorDialog,
        name: str,
        description: str,
        system_prompt: str,
        model_id: str,
        web_mode: str,
        web_provider: str,
    ) -> None:
        """Handle create assistant request."""
        request = CreateAssistantRequest(
            name=name,
            description=description if description else None,
            system_prompt=system_prompt,
            default_model_id=model_id if model_id else None,
            default_web_search_mode=web_mode if web_mode else None,
            default_web_search_provider=web_provider if web_provider else None,
        )

        def create() -> Assistant | Exception:
            async def do_create() -> Assistant:
                async with NanoChatClient(self._backend_url, self._api_key) as client:
                    return await client.create_assistant(request)

            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(do_create())
                loop.close()
                return result
            except Exception as e:
                return e

        def on_complete(result: Assistant | Exception) -> None:
            if isinstance(result, Exception):
                logger.error(f"Failed to create assistant: {result}")
                self._toast_overlay.add_toast(Adw.Toast(title="Failed to create assistant"))
                return

            dialog.close()
            self._toast_overlay.add_toast(Adw.Toast(title=f"Created \"{result.name}\""))
            self._load_assistants()
            self.emit("assistants-changed")

        def thread_func() -> None:
            result = create()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _on_update_assistant(
        self,
        assistant_id: str,
        dialog: AssistantEditorDialog,
        name: str,
        description: str,
        system_prompt: str,
        model_id: str,
        web_mode: str,
        web_provider: str,
    ) -> None:
        """Handle update assistant request."""
        request = UpdateAssistantRequest(
            name=name,
            description=description if description else None,
            system_prompt=system_prompt,
            default_model_id=model_id if model_id else None,
            default_web_search_mode=web_mode if web_mode else None,
            default_web_search_provider=web_provider if web_provider else None,
        )

        def update() -> Assistant | Exception:
            async def do_update() -> Assistant:
                async with NanoChatClient(self._backend_url, self._api_key) as client:
                    return await client.update_assistant(assistant_id, request)

            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(do_update())
                loop.close()
                return result
            except Exception as e:
                return e

        def on_complete(result: Assistant | Exception) -> None:
            if isinstance(result, Exception):
                logger.error(f"Failed to update assistant: {result}")
                self._toast_overlay.add_toast(Adw.Toast(title="Failed to update assistant"))
                return

            dialog.close()
            self._toast_overlay.add_toast(Adw.Toast(title=f"Updated \"{result.name}\""))
            self._load_assistants()
            self.emit("assistants-changed")

        def thread_func() -> None:
            result = update()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _on_set_default(self, assistant: Assistant) -> None:
        """Handle set as default button click."""
        def set_default() -> None | Exception:
            async def do_set() -> None:
                async with NanoChatClient(self._backend_url, self._api_key) as client:
                    await client.set_default_assistant(assistant.id)

            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(do_set())
                loop.close()
                return None
            except Exception as e:
                return e

        def on_complete(result: None | Exception) -> None:
            if isinstance(result, Exception):
                logger.error(f"Failed to set default: {result}")
                self._toast_overlay.add_toast(Adw.Toast(title="Failed to set default"))
                return

            self._toast_overlay.add_toast(Adw.Toast(title=f"\"{assistant.name}\" is now default"))
            self._load_assistants()
            self.emit("assistants-changed")

        def thread_func() -> None:
            result = set_default()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _on_delete_assistant(self, assistant: Assistant) -> None:
        """Handle delete assistant button click."""
        # Show confirmation dialog
        confirm = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Delete Assistant?",
            body=f"Are you sure you want to delete \"{assistant.name}\"? This cannot be undone.",
        )
        confirm.add_response("cancel", "Cancel")
        confirm.add_response("delete", "Delete")
        confirm.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        confirm.set_default_response("cancel")
        confirm.set_close_response("cancel")

        def on_response(dialog: Adw.MessageDialog, response: str) -> None:
            if response == "delete":
                self._do_delete_assistant(assistant)

        confirm.connect("response", on_response)
        confirm.present()

    def _do_delete_assistant(self, assistant: Assistant) -> None:
        """Actually delete the assistant."""
        def delete() -> None | Exception:
            async def do_delete() -> None:
                async with NanoChatClient(self._backend_url, self._api_key) as client:
                    await client.delete_assistant(assistant.id)

            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(do_delete())
                loop.close()
                return None
            except Exception as e:
                return e

        def on_complete(result: None | Exception) -> None:
            if isinstance(result, Exception):
                logger.error(f"Failed to delete assistant: {result}")
                self._toast_overlay.add_toast(Adw.Toast(title="Failed to delete assistant"))
                return

            self._toast_overlay.add_toast(Adw.Toast(title=f"Deleted \"{assistant.name}\""))
            self._load_assistants()
            self.emit("assistants-changed")

        def thread_func() -> None:
            result = delete()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()
