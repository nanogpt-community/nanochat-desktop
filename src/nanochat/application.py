"""GTK4/Libadwaita Application."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, Adw, GLib, Gtk, Gdk

from nanochat.data.settings import SettingsManager
from nanochat.data.secrets import SecretsManager
from nanochat.data.database import Database


class NanoChatApplication(Adw.Application):
    """Main application class."""

    def __init__(self) -> None:
        super().__init__(
            application_id="com.nanogpt.NanoChat",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.settings_manager = SettingsManager()
        self.secrets_manager = SecretsManager()
        self.database = Database()
        self._window: object = None

    def do_startup(self) -> None:
        """Called when the application starts."""
        Adw.Application.do_startup(self)
        self._setup_actions()
        self._load_css()
        self._apply_theme()

    def do_activate(self) -> None:
        """Called when the application is activated."""
        if not self._window:
            from nanochat.ui.window import NanoChatWindow
            self._window = NanoChatWindow(
                application=self,
                settings_manager=self.settings_manager,
                secrets_manager=self.secrets_manager,
                database=self.database,
            )

        self._window.present()  # type: ignore[attr-defined]

        # Check if setup is needed
        if not self._is_configured():
            self._show_setup_dialog()

    def _setup_actions(self) -> None:
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

    def _show_setup_dialog(self) -> None:
        """Show setup dialog."""
        from nanochat.ui.setup_dialog import SetupDialog

        dialog = SetupDialog(
            self._window,  # type: ignore[arg-type]
            self.settings_manager,
            self.secrets_manager,
            on_saved=self._on_setup_complete,
            on_theme_changed=lambda: self._apply_theme(),
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

    def _load_css(self) -> None:
        """Load custom CSS stylesheet."""
        css = """
/* NanoChat Desktop Custom Styles */

/* ========== Message Widgets ========== */

.message-widget {
    padding: 0;
    margin: 0;
}

.message-widget.user .message-content {
    background-color: alpha(@accent_color, 0.1);
    border-radius: 12px;
    border-left: 3px solid @accent_color;
    padding: 12px 16px;
}

.message-widget.assistant .message-content {
    background-color: alpha(@window_bg_color, 0.5);
    border-radius: 12px;
    padding: 12px 16px;
}

.message-role-label {
    font-size: 0.85em;
    font-weight: 600;
    margin-bottom: 4px;
    opacity: 0.8;
}

.message-role-label.user {
    color: @accent_color;
}

.message-role-label.assistant {
    color: @dim_label_color;
}

.message-content {
    font-size: 0.95em;
    line-height: 1.5;
}

.message-content text {
    background-color: transparent;
}

/* ========== Code Blocks ========== */

message-content code,
.message-content tt {
    font-family: "Monospace", "Courier New", monospace;
    background-color: alpha(@shade_color, 0.15);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
}

.message-content pre {
    background-color: alpha(@shade_color, 0.2);
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}

.message-content pre code {
    background-color: transparent;
    padding: 0;
}

/* ========== Conversation List ========== */

.conversation-row {
    padding: 8px 12px;
    border-radius: 8px;
    margin: 2px 4px;
    transition: background-color 150ms ease;
}

.conversation-row:hover {
    background-color: alpha(@shade_color, 0.1);
}

.conversation-row:selected {
    background-color: alpha(@accent_color, 0.2);
}

.conversation-row .conversation-title {
    font-weight: 500;
}

.conversation-row .conversation-time {
    font-size: 0.85em;
    opacity: 0.7;
}

/* ========== Delete Button (Hover Reveal) ========== */

.delete-button {
    opacity: 0;
    transition: opacity 200ms ease;
}

.conversation-row:hover .delete-button,
.message-widget:hover .delete-button {
    opacity: 1;
}

.delete-button:hover {
    background-color: alpha(@error_color, 0.15);
    color: @error_color;
}

/* ========== Chat Input Area ========== */

.chat-input-box {
    padding: 12px;
    background-color: @headerbar_bg_color;
    border-top: 1px solid alpha(@shade_color, 0.1);
}

.chat-input-box entry {
    border-radius: 20px;
    padding: 8px 16px;
    min-height: 24px;
}

.chat-input-box entry:focus {
    border-color: @accent_color;
    box-shadow: 0 0 0 2px alpha(@accent_color, 0.3);
}

/* ========== Send Button ========== */

.send-button {
    border-radius: 50%;
    min-width: 40px;
    min-height: 40px;
    padding: 0;
}

.send-button.suggested-action {
    background-color: @accent_color;
}

.send-button.suggested-action:hover {
    background-color: shade(@accent_color, 1.1);
}

.send-button.generating {
    background-color: @error_color;
}

/* ========== Sidebar ========== */

.sidebar {
    background-color: @sidebar_bg_color;
    border-right: 1px solid alpha(@shade_color, 0.1);
}

.sidebar-header {
    padding: 8px;
    border-bottom: 1px solid alpha(@shade_color, 0.1);
}

/* ========== Empty State ========== */

.empty-state {
    padding: 32px;
    opacity: 0.6;
}

.empty-state icon {
    font-size: 48px;
    margin-bottom: 16px;
}

.empty-state label {
    font-size: 1.1em;
}

/* ========== Scrollbar Styling ========== */

scrolledwindow scrollbar {
    opacity: 0;
    transition: opacity 200ms ease;
}

scrolledwindow:hover scrollbar {
    opacity: 1;
}

scrolledwindow scrollbar slider {
    border-radius: 4px;
    min-width: 8px;
    min-height: 8px;
    background-color: alpha(@shade_color, 0.5);
}

scrolledwindow scrollbar slider:hover {
    background-color: alpha(@shade_color, 0.7);
}
"""

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _apply_theme(self) -> None:
        """Apply the selected theme."""
        manager = Adw.StyleManager.get_default()
        theme = self.settings_manager.settings.ui.theme

        if theme == "system":
            manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
        elif theme == "light":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def reload_theme(self) -> None:
        """Reload theme (call after settings change)."""
        self._apply_theme()
