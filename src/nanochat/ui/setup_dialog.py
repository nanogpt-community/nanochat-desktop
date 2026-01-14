"""Setup/configuration dialog."""

import asyncio
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib


class SetupDialog(Adw.PreferencesWindow):  # type: ignore[misc]
    """Setup dialog for backend URL and API key."""

    def __init__(
        self,
        parent: object,
        settings_manager: object,
        secrets_manager: object,
        on_saved: object | None = None,
    ) -> None:
        super().__init__()

        self.set_transient_for(parent)  # type: ignore[arg-type]
        self.set_modal(True)
        self.set_title("NanoChat Setup")
        self.set_default_size(500, 400)

        self._settings_manager = settings_manager
        self._secrets_manager = secrets_manager
        self._on_saved = on_saved
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self) -> None:
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

    def _load_current_settings(self) -> None:
        """Load current settings into form."""
        settings = self._settings_manager.settings
        self.url_row.set_text(settings.server.backend_url)

        api_key = self._secrets_manager.get_api_key()
        if api_key:
            self.key_row.set_text(api_key)

    def _on_test_connection(self, button: Gtk.Button) -> None:
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
        def run_test() -> bool | str:
            from nanochat.api.client import NanoChatClient

            async def test() -> bool:
                async with NanoChatClient(url, key) as client:
                    return await client.test_connection()

            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(test())
                loop.close()
                return result
            except Exception as e:
                return str(e)

        def on_complete(success: bool | str) -> None:
            button.set_sensitive(True)
            if success is True:
                self.status_label.set_markup(
                    '<span color="green">✓ Connection successful</span>'
                )
            else:
                self.status_label.set_markup(f'<span color="red">✗ {success}</span>')

        # Run in thread
        def thread_func() -> None:
            result = run_test()
            GLib.idle_add(on_complete, result)

        thread = threading.Thread(target=thread_func)
        thread.start()

    def _on_save(self, button: Gtk.Button) -> None:
        """Save settings."""
        self._save_settings()
        self.close()

    def _on_close(self, window: Gtk.Widget) -> bool:
        """Handle window close."""
        self._save_settings()
        return False

    def _save_settings(self) -> None:
        """Save current form to settings."""
        url = self.url_row.get_text().strip()
        key = self.key_row.get_text().strip()

        saved = False
        if url:
            self._settings_manager.settings.server.backend_url = url
            self._settings_manager.save()
            saved = True

        if key:
            self._secrets_manager.set_api_key(key)
            saved = True

        # Call callback if settings were saved
        if saved and self._on_saved:
            self._on_saved()
