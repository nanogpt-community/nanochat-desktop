"""Web search configuration popover."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk


class WebSearchConfigPopover(Gtk.Popover):
    """Popover for configuring web search options."""

    __gtype_name__ = "WebSearchConfigPopover"

    # Signals for when settings change
    __gsignals__ = {
        "settings-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # (mode, provider)
    }

    # Available modes with descriptions
    MODES = [
        ("off", "Off", "Web search disabled"),
        ("standard", "Standard", "Quick web search"),
        ("deep", "Deep", "Comprehensive research"),
    ]

    # Available providers with descriptions
    PROVIDERS = [
        ("tavily", "Tavily", "General purpose search (Recommended)"),
        ("linkup", "Linkup", "Fast and efficient"),
        ("exa", "Exa", "AI-optimized search"),
        ("kagi", "Kagi", "Privacy-focused search"),
    ]

    def __init__(self, initial_mode: str = "standard", initial_provider: str = "tavily") -> None:
        super().__init__()

        self._current_mode = initial_mode
        self._current_provider = initial_provider

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the popover UI."""
        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Mode section
        mode_label = Gtk.Label(label="Search Mode")
        mode_label.add_css_class("heading")
        mode_label.set_halign(Gtk.Align.START)
        box.append(mode_label)

        # Mode selection (radio-like buttons using Gtk.CheckButton with groups)
        mode_group = Adw.PreferencesGroup()
        self._mode_buttons: dict[str, Gtk.CheckButton] = {}
        first_mode_btn = None

        for mode_id, mode_name, mode_desc in self.MODES:
            row = Adw.ActionRow()
            row.set_title(mode_name)
            row.set_subtitle(mode_desc)

            check = Gtk.CheckButton()
            check.set_valign(Gtk.Align.CENTER)
            if first_mode_btn is None:
                first_mode_btn = check
            else:
                check.set_group(first_mode_btn)

            if mode_id == self._current_mode:
                check.set_active(True)

            check.connect("toggled", self._on_mode_changed, mode_id)
            self._mode_buttons[mode_id] = check

            row.add_prefix(check)
            row.set_activatable_widget(check)
            mode_group.add(row)

        box.append(mode_group)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(8)
        separator.set_margin_bottom(8)
        box.append(separator)

        # Provider section
        provider_label = Gtk.Label(label="Search Provider")
        provider_label.add_css_class("heading")
        provider_label.set_halign(Gtk.Align.START)
        box.append(provider_label)

        # Provider selection
        provider_group = Adw.PreferencesGroup()
        self._provider_buttons: dict[str, Gtk.CheckButton] = {}
        first_provider_btn = None

        for provider_id, provider_name, provider_desc in self.PROVIDERS:
            row = Adw.ActionRow()
            row.set_title(provider_name)
            row.set_subtitle(provider_desc)

            check = Gtk.CheckButton()
            check.set_valign(Gtk.Align.CENTER)
            if first_provider_btn is None:
                first_provider_btn = check
            else:
                check.set_group(first_provider_btn)

            if provider_id == self._current_provider:
                check.set_active(True)

            check.connect("toggled", self._on_provider_changed, provider_id)
            self._provider_buttons[provider_id] = check

            row.add_prefix(check)
            row.set_activatable_widget(check)
            provider_group.add(row)

        box.append(provider_group)

        self.set_child(box)

    def _on_mode_changed(self, button: Gtk.CheckButton, mode_id: str) -> None:
        """Handle mode selection change."""
        if button.get_active():
            self._current_mode = mode_id
            self.emit("settings-changed", self._current_mode, self._current_provider)

    def _on_provider_changed(self, button: Gtk.CheckButton, provider_id: str) -> None:
        """Handle provider selection change."""
        if button.get_active():
            self._current_provider = provider_id
            self.emit("settings-changed", self._current_mode, self._current_provider)

    @property
    def mode(self) -> str:
        """Get the current mode."""
        return self._current_mode

    @property
    def provider(self) -> str:
        """Get the current provider."""
        return self._current_provider

    def set_mode(self, mode: str) -> None:
        """Set the mode programmatically."""
        if mode in self._mode_buttons:
            self._mode_buttons[mode].set_active(True)
            self._current_mode = mode

    def set_provider(self, provider: str) -> None:
        """Set the provider programmatically."""
        if provider in self._provider_buttons:
            self._provider_buttons[provider].set_active(True)
            self._current_provider = provider
