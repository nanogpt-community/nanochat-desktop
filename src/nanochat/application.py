"""GTK4/Libadwaita Application."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, GLib

from nanochat.data.settings import SettingsManager
from nanochat.data.secrets import SecretsManager


class NanoChatApplication:  # type: ignore[misc]
    """Main application class."""

    def __init__(self) -> None:
        from gi.repository import Adw

        self._app = Adw.Application(
            application_id="com.nanogpt.NanoChat",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._app.connect("startup", self._on_startup)
        self._app.connect("activate", self._on_activate)

        self.settings_manager = SettingsManager()
        self.secrets_manager = SecretsManager()
        self._window: object = None

    def _on_startup(self, app: object) -> None:
        """Called when the application starts."""
        self._setup_actions()

    def _on_activate(self, app: object) -> None:
        """Called when the application is activated."""
        if not self._window:
            from nanochat.ui.window import NanoChatWindow
            self._window = NanoChatWindow(
                application=self._app,
                settings_manager=self.settings_manager,
                secrets_manager=self.secrets_manager,
            )

        self._window.present()  # type: ignore[attr-defined]

        # Check if setup is needed
        if not self._is_configured():
            self._show_setup_dialog()

    def _setup_actions(self) -> None:
        """Set up application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self._app.quit())
        self._app.add_action(quit_action)
        self._app.set_accels_for_action("app.quit", ["<Control>q"])

        # Settings action
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self._on_settings)
        self._app.add_action(settings_action)
        self._app.set_accels_for_action("app.settings", ["<Control>comma"])

        # New chat action
        new_chat_action = Gio.SimpleAction.new("new-chat", None)
        new_chat_action.connect("activate", self._on_new_chat)
        self._app.add_action(new_chat_action)
        self._app.set_accels_for_action("app.new-chat", ["<Control>n"])

    def _is_configured(self) -> bool:
        """Check if app is configured."""
        has_url = bool(self.settings_manager.settings.server.backend_url)
        has_key = self.secrets_manager.has_api_key()
        return has_url and has_key

    def _show_setup_dialog(self) -> None:
        """Show setup dialog."""
        from nanochat.ui.setup_dialog import SetupDialog

        dialog = SetupDialog(
            self._window,  # type: ignore[arg-type]
            self.settings_manager,
            self.secrets_manager,
            on_saved=self._on_setup_complete,
        )
        dialog.present()

    def _on_setup_complete(self) -> None:
        """Called when setup dialog saves settings."""
        if self._window:
            self._window.reload_data()  # type: ignore[attr-defined]

    def _on_settings(self, action: object, param: object) -> None:
        """Handle settings action."""
        self._show_setup_dialog()

    def _on_new_chat(self, action: object, param: object) -> None:
        """Handle new chat action."""
        if self._window:
            self._window.new_conversation()  # type: ignore[attr-defined]

    def run(self, argv: list[str]) -> int:
        """Run the application."""
        return self._app.run(argv)
