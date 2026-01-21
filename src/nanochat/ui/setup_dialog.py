"""Setup/configuration dialog."""

import asyncio
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from typing import Callable, Optional
from gi.repository import Gtk, Adw, GLib, Gdk

from nanochat.data.settings import SettingsManager
from nanochat.data.secrets import SecretsManager
from nanochat import version


class SetupDialog(Adw.PreferencesWindow):  # type: ignore[misc]
    """Setup dialog for backend URL and API key."""

    def __init__(
        self,
        parent: Gtk.Window,
        settings_manager: SettingsManager,
        secrets_manager: SecretsManager,
        on_saved: Optional[Callable[[], None]] = None,
        on_theme_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("NanoChat Setup")
        self.set_default_size(500, 400)

        self._settings_manager = settings_manager
        self._secrets_manager = secrets_manager
        self._on_saved = on_saved
        self._theme_changed_callback = on_theme_changed
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

        # UI page for appearance settings
        ui_page = Adw.PreferencesPage()
        ui_page.set_title("Appearance")
        ui_page.set_icon_name("applications-graphics-symbolic")
        self.add(ui_page)

        # Appearance group
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title("Appearance")
        appearance_group.set_description("Customize the look and feel")
        ui_page.add(appearance_group)

        # Theme selector
        self.theme_row = Adw.ComboRow()
        self.theme_row.set_title("Theme")
        self.theme_row.set_subtitle("Choose your preferred color scheme")

        # Create theme options
        theme_list = Gtk.StringList()
        theme_list.append("System")
        theme_list.append("Light")
        theme_list.append("Dark")
        self.theme_row.set_model(theme_list)

        # Set current selection
        current_theme = self._settings_manager.settings.ui.theme
        theme_map = {"system": 0, "light": 1, "dark": 2}
        self.theme_row.set_selected(theme_map.get(current_theme, 0))

        # Connect to selection change for live theme updates
        self.theme_row.connect("notify::selected", self._on_theme_changed)

        appearance_group.add(self.theme_row)

        # About page
        about_page = Adw.PreferencesPage()
        about_page.set_title("About")
        about_page.set_icon_name("help-about-symbolic")
        self.add(about_page)

        # Version group
        version_group = Adw.PreferencesGroup()
        version_group.set_title("Version Information")
        about_page.add(version_group)

        # App name and version
        version_row = Adw.ActionRow()
        version_row.set_title("Version")
        version_row.set_subtitle(version.__version__)
        version_row.set_icon_name("starred-symbolic")
        version_group.add(version_row)

        # App name
        name_row = Adw.ActionRow()
        name_row.set_title("Application")
        name_row.set_subtitle(version.APP_NAME)
        version_group.add(name_row)

        # Links group
        links_group = Adw.PreferencesGroup()
        links_group.set_title("Links")
        about_page.add(links_group)

        # GitHub repository
        github_row = Adw.ActionRow()
        github_row.set_title("GitHub Repository")
        github_row.set_subtitle("Source code and issues")
        github_row.set_icon_name("web-browser-symbolic")
        github_row.set_activatable(True)
        github_row.connect("activated", self._on_github_clicked)
        links_group.add(github_row)

        # Bug reports
        issues_row = Adw.ActionRow()
        issues_row.set_title("Report Issues")
        issues_row.set_subtitle("Bug reports and feature requests")
        issues_row.set_icon_name("emblem-important-symbolic")
        issues_row.set_activatable(True)
        issues_row.connect("activated", self._on_issues_clicked)
        links_group.add(issues_row)

        # Info group
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Info")
        about_page.add(info_group)

        # Developer
        developer_row = Adw.ActionRow()
        developer_row.set_title("Developer")
        developer_row.set_subtitle(version.DEVELOPER_NAME)
        info_group.add(developer_row)

        # Copyright
        copyright_row = Adw.ActionRow()
        copyright_row.set_title("Copyright")
        copyright_row.set_subtitle(version.COPYRIGHT)
        info_group.add(copyright_row)

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

    def _on_theme_changed(self, row: Adw.ComboRow, pspec: object) -> None:
        """Handle theme selection change - applies immediately."""
        theme_map = {0: "system", 1: "light", 2: "dark"}
        selected_theme = theme_map.get(row.get_selected(), "system")

        # Update settings
        if self._settings_manager.settings.ui.theme != selected_theme:
            self._settings_manager.settings.ui.theme = selected_theme
            self._settings_manager.save()

            # Notify app to reload theme
            if self._theme_changed_callback:
                self._theme_changed_callback()

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
            saved = True

        if key:
            self._secrets_manager.set_api_key(key)
            saved = True

        # Save theme selection
        theme_map = {0: "system", 1: "light", 2: "dark"}
        selected_theme = theme_map.get(self.theme_row.get_selected(), "system")
        if self._settings_manager.settings.ui.theme != selected_theme:
            self._settings_manager.settings.ui.theme = selected_theme
            saved = True

        if saved:
            self._settings_manager.save()

        # Call callback if settings were saved
        if saved and self._on_saved:
            self._on_saved()

    def _on_github_clicked(self, row: Adw.ActionRow) -> None:
        """Handle GitHub repository link click."""
        try:
            Gtk.show_uri(None, version.GITHUB_URL, Gdk.CURRENT_TIME)
        except Exception as e:
            # Fallback: show URL in a dialog
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="GitHub Repository",
                body=version.GITHUB_URL,
            )
            dialog.add_response("copy", "Copy URL")
            dialog.add_response("close", "Close")
            dialog.set_default_response("copy")
            dialog.set_close_response("close")

            def copy_url(response: str, dialog: Adw.MessageDialog) -> None:
                if response == "copy":
                    clipboard = Gdk.Display.get_default().get_clipboard()
                    clipboard.set(version.GITHUB_URL)
                dialog.destroy()

            dialog.connect("response", copy_url)
            dialog.present()

    def _on_issues_clicked(self, row: Adw.ActionRow) -> None:
        """Handle issues link click."""
        try:
            Gtk.show_uri(None, version.ISSUES_URL, Gdk.CURRENT_TIME)
        except Exception as e:
            # Fallback: show URL in a dialog
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Report Issues",
                body=version.ISSUES_URL,
            )
            dialog.add_response("copy", "Copy URL")
            dialog.add_response("close", "Close")
            dialog.set_default_response("copy")
            dialog.set_close_response("close")

            def copy_url(response: str, dialog: Adw.MessageDialog) -> None:
                if response == "copy":
                    clipboard = Gdk.Display.get_default().get_clipboard()
                    clipboard.set(version.ISSUES_URL)
                dialog.destroy()

            dialog.connect("response", copy_url)
            dialog.present()
