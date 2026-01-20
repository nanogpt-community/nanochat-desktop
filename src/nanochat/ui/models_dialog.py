"""Models management dialog for viewing and managing model favorites."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GObject, Gtk

from nanochat.api.models import Model
from nanochat.data.settings import SettingsManager


class ModelsDialog(Adw.Dialog):
    """Dialog for managing models (viewing and favoriting)."""

    __gtype_name__ = "ModelsDialog"

    __gsignals__ = {
        "models-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, settings_manager: SettingsManager, models: list[Model]) -> None:
        """Initialize the models dialog.

        Args:
            settings_manager: Settings manager for storing favorites
            models: List of Model objects to display
        """
        super().__init__(title="Manage Models")
        self._settings_manager = settings_manager
        self._models = models
        self._model_rows: list[Adw.ActionRow] = []

        self.set_content_width(500)
        self.set_content_height(600)

        self._setup_ui()
        self._update_models_list()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Main content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)

        # Info text
        info = Gtk.Label(label="Favorite models will appear at the top of the model selector.")
        info.set_wrap(True)
        info.set_halign(Gtk.Align.START)
        info.add_css_class("dim-label")
        content.append(info)

        # Scrolled window for models list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # Clamp to constrain width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        clamp.set_tightening_threshold(300)

        # Models group (list)
        self._models_group = Adw.PreferencesGroup()
        self._models_group.set_title("Models")
        self._models_group.set_description("Click the star to favorite/unfavorite models")
        clamp.set_child(self._models_group)
        scrolled.set_child(clamp)
        content.append(scrolled)

        # Close button
        close_btn = Gtk.Button(label="Close")
        close_btn.add_css_class("pill")
        close_btn.add_css_class("suggested-action")
        close_btn.connect("clicked", lambda _: self.close())
        content.append(close_btn)

        self.set_child(content)

    def _update_models_list(self) -> None:
        """Update the models list UI."""
        # Remove only the rows we created
        for row in self._model_rows:
            self._models_group.remove(row)
        self._model_rows.clear()

        # Sort: favorites first, then alphabetically
        sorted_models = sorted(
            self._models,
            key=lambda m: (not m.is_favorite, m.name.lower())
        )

        # Add model rows
        for model in sorted_models:
            row = self._create_model_row(model)
            self._models_group.add(row)
            self._model_rows.append(row)

    def _create_model_row(self, model: Model) -> Adw.ActionRow:
        """Create a row for a single model."""
        row = Adw.ActionRow()
        row.set_title(model.name)
        row.set_title_lines(1)
        row.set_activatable(False)

        # Add subtitle with provider/info if available
        if model.description:
            row.set_subtitle(model.description)
            row.set_subtitle_lines(2)

        # Favorite star button
        star_btn = Gtk.Button()
        star_btn.set_icon_name(
            "starred-symbolic" if model.is_favorite else "non-starred-symbolic"
        )
        star_btn.set_valign(Gtk.Align.CENTER)
        star_btn.add_css_class("flat")
        star_btn.set_tooltip_text(
            "Remove from favorites" if model.is_favorite else "Add to favorites"
        )
        star_btn.connect("clicked", self._on_star_clicked, model, star_btn)
        row.add_suffix(star_btn)

        # Add favorite indicator class
        if model.is_favorite:
            row.add_css_class("favorite-model")

        return row

    def _on_star_clicked(self, button: Gtk.Button, model: Model, star_btn: Gtk.Button) -> None:
        """Handle star button click - update local storage."""
        # Toggle favorite status
        new_status = not model.is_favorite
        model.is_favorite = new_status

        # Update local settings
        favorites = self._settings_manager.settings.chat.favorite_models
        if new_status:
            # Add to favorites if not already there
            if model.id not in favorites:
                favorites.append(model.id)
        else:
            # Remove from favorites
            favorites = [fid for fid in favorites if fid != model.id]

        # Save to settings
        self._settings_manager.settings.chat.favorite_models = favorites
        self._settings_manager.save()

        # Update UI
        star_btn.set_icon_name(
            "starred-symbolic" if new_status else "non-starred-symbolic"
        )
        star_btn.set_tooltip_text(
            "Remove from favorites" if new_status else "Add to favorites"
        )

        # Find and update the row's CSS class
        for row in self._model_rows:
            if row.get_title() == model.name:
                if new_status:
                    row.add_css_class("favorite-model")
                else:
                    row.remove_css_class("favorite-model")
                break

        # Re-sort the list (favorites move to top)
        self._update_models_list()

        # Emit signal to update parent's dropdown
        self.emit("models-changed")

    def set_models(self, models: list[Model]) -> None:
        """Update the models list with new data."""
        self._models = models
        self._update_models_list()
