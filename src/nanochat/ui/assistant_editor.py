"""Assistant editor dialog for creating/editing assistants."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk

from nanochat.api.models import Assistant


class AssistantEditorDialog(Adw.Dialog):
    """Dialog for creating or editing an assistant."""

    __gtype_name__ = "AssistantEditorDialog"

    # Signal emitted when save is clicked with valid data
    __gsignals__ = {
        "save-requested": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, str, str, str, str, str),  # name, description, system_prompt, model_id, web_mode, web_provider
        ),
    }

    # Web search mode options
    WEB_SEARCH_MODES = [
        ("", "No default"),
        ("off", "Off"),
        ("standard", "Standard"),
        ("deep", "Deep"),
    ]

    # Web search provider options
    WEB_SEARCH_PROVIDERS = [
        ("", "No default"),
        ("tavily", "Tavily"),
        ("linkup", "Linkup"),
        ("exa", "Exa"),
        ("kagi", "Kagi"),
    ]

    def __init__(
        self,
        assistant: Assistant | None = None,
        model_list: list[tuple[str, str]] | None = None,
    ) -> None:
        """Initialize the editor.

        Args:
            assistant: Existing assistant to edit, or None for new assistant
            model_list: List of (model_id, model_name) tuples for model dropdown
        """
        super().__init__()

        self._assistant = assistant
        self._model_list = model_list or []
        self._is_edit = assistant is not None

        self.set_title("Edit Assistant" if self._is_edit else "New Assistant")
        self.set_content_width(500)
        self.set_content_height(600)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        # Main toolbar view
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        # Cancel button
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        # Save button
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(save_btn)
        self._save_btn = save_btn

        toolbar_view.add_top_bar(header)

        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # === Basic Information Section ===
        basic_group = Adw.PreferencesGroup()
        basic_group.set_title("Basic Information")

        # Name entry
        self._name_row = Adw.EntryRow()
        self._name_row.set_title("Name")
        if self._assistant:
            self._name_row.set_text(self._assistant.name)
        self._name_row.connect("changed", self._on_field_changed)
        basic_group.add(self._name_row)

        # Description entry
        self._description_row = Adw.EntryRow()
        self._description_row.set_title("Description (optional)")
        if self._assistant and self._assistant.description:
            self._description_row.set_text(self._assistant.description)
        basic_group.add(self._description_row)

        content.append(basic_group)

        # === System Prompt Section ===
        prompt_group = Adw.PreferencesGroup()
        prompt_group.set_title("System Prompt")
        prompt_group.set_description("Instructions that define the assistant's behavior")

        # System prompt text view in a frame
        prompt_frame = Gtk.Frame()
        prompt_frame.set_margin_top(8)

        self._system_prompt_view = Gtk.TextView()
        self._system_prompt_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._system_prompt_view.set_top_margin(12)
        self._system_prompt_view.set_bottom_margin(12)
        self._system_prompt_view.set_left_margin(12)
        self._system_prompt_view.set_right_margin(12)
        self._system_prompt_view.set_vexpand(True)
        self._system_prompt_view.set_size_request(-1, 150)

        buffer = self._system_prompt_view.get_buffer()

        if self._assistant:
            buffer.set_text(self._assistant.system_prompt)

        buffer.connect("changed", self._on_field_changed)

        prompt_scrolled = Gtk.ScrolledWindow()
        prompt_scrolled.set_child(self._system_prompt_view)
        prompt_scrolled.set_min_content_height(150)
        prompt_scrolled.set_max_content_height(200)

        prompt_frame.set_child(prompt_scrolled)
        prompt_group.add(prompt_frame)

        content.append(prompt_group)

        # === Defaults Section ===
        defaults_group = Adw.PreferencesGroup()
        defaults_group.set_title("Default Settings")
        defaults_group.set_description("Optional defaults when using this assistant")

        # Default model dropdown
        model_row = Adw.ComboRow()
        model_row.set_title("Default Model")
        model_row.set_subtitle("Model to use by default")

        model_names = Gtk.StringList()
        model_names.append("No default")
        for _, model_name in self._model_list:
            model_names.append(model_name)
        model_row.set_model(model_names)

        # Set current selection
        if self._assistant and self._assistant.default_model_id:
            for i, (model_id, _) in enumerate(self._model_list):
                if model_id == self._assistant.default_model_id:
                    model_row.set_selected(i + 1)  # +1 for "No default"
                    break

        self._model_row = model_row
        defaults_group.add(model_row)

        # Web search mode dropdown
        web_mode_row = Adw.ComboRow()
        web_mode_row.set_title("Default Web Search Mode")
        web_mode_row.set_subtitle("Web search mode when using this assistant")

        web_mode_names = Gtk.StringList()
        for _, mode_name in self.WEB_SEARCH_MODES:
            web_mode_names.append(mode_name)
        web_mode_row.set_model(web_mode_names)

        # Set current selection
        if self._assistant and self._assistant.default_web_search_mode:
            for i, (mode_id, _) in enumerate(self.WEB_SEARCH_MODES):
                if mode_id == self._assistant.default_web_search_mode:
                    web_mode_row.set_selected(i)
                    break

        self._web_mode_row = web_mode_row
        defaults_group.add(web_mode_row)

        # Web search provider dropdown
        web_provider_row = Adw.ComboRow()
        web_provider_row.set_title("Default Web Search Provider")
        web_provider_row.set_subtitle("Search provider when using this assistant")

        web_provider_names = Gtk.StringList()
        for _, provider_name in self.WEB_SEARCH_PROVIDERS:
            web_provider_names.append(provider_name)
        web_provider_row.set_model(web_provider_names)

        # Set current selection
        if self._assistant and self._assistant.default_web_search_provider:
            for i, (provider_id, _) in enumerate(self.WEB_SEARCH_PROVIDERS):
                if provider_id == self._assistant.default_web_search_provider:
                    web_provider_row.set_selected(i)
                    break

        self._web_provider_row = web_provider_row
        defaults_group.add(web_provider_row)

        content.append(defaults_group)

        scrolled.set_child(content)
        toolbar_view.set_content(scrolled)

        self.set_child(toolbar_view)

        # Initial validation
        self._validate()

    def _on_field_changed(self, *args) -> None:
        """Handle field change - revalidate form."""
        self._validate()

    def _validate(self) -> bool:
        """Validate form fields and update save button state."""
        name = self._name_row.get_text().strip()
        buffer = self._system_prompt_view.get_buffer()
        start, end = buffer.get_bounds()
        system_prompt = buffer.get_text(start, end, False).strip()

        is_valid = len(name) > 0 and len(system_prompt) > 0
        self._save_btn.set_sensitive(is_valid)
        return is_valid

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        """Handle save button click."""
        if not self._validate():
            return

        name = self._name_row.get_text().strip()
        description = self._description_row.get_text().strip() or ""

        buffer = self._system_prompt_view.get_buffer()
        start, end = buffer.get_bounds()
        system_prompt = buffer.get_text(start, end, False).strip()

        # Get selected model
        model_idx = self._model_row.get_selected()
        model_id = ""
        if model_idx > 0 and model_idx <= len(self._model_list):
            model_id = self._model_list[model_idx - 1][0]

        # Get selected web search mode
        web_mode_idx = self._web_mode_row.get_selected()
        web_mode = self.WEB_SEARCH_MODES[web_mode_idx][0] if web_mode_idx < len(self.WEB_SEARCH_MODES) else ""

        # Get selected web search provider
        web_provider_idx = self._web_provider_row.get_selected()
        web_provider = self.WEB_SEARCH_PROVIDERS[web_provider_idx][0] if web_provider_idx < len(self.WEB_SEARCH_PROVIDERS) else ""

        self.emit("save-requested", name, description, system_prompt, model_id, web_mode, web_provider)
