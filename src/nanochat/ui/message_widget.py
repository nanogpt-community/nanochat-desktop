"""Widget for displaying a single chat message."""

import re
from collections.abc import Callable
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Pango, Gdk, GLib

# Pre-compiled regex patterns for markdown parsing (performance optimization)
_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"\*([^*]+)\*")

# Security: Only allow safe URL schemes for links
_ALLOWED_URL_SCHEMES = ("http://", "https://", "mailto:")

# Maximum content length to prevent DoS via extremely long messages
_MAX_CONTENT_LENGTH = 5000


class MessageWidget(Adw.Bin):  # type: ignore[misc]
    """Widget for displaying a single chat message with metadata and actions."""

    def __init__(
        self,
        role: str,
        content: str,
        model_id: Optional[str] = None,
        token_count: Optional[int] = None,
        cost_usd: Optional[float] = None,
        response_time_ms: Optional[int] = None,
        starred: bool = False,
        on_regenerate: Optional[Callable[[], None]] = None,
        on_star: Optional[Callable[[bool], None]] = None,
        **kwargs: object,
    ) -> None:
        """Initialize a message widget.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            model_id: ID of the model used (for assistant messages)
            token_count: Number of tokens used
            cost_usd: Cost in USD
            response_time_ms: Response time in milliseconds
            starred: Whether the message is starred
            on_regenerate: Callback when regenerate is clicked
            on_star: Callback when star toggle is clicked
        """
        super().__init__(**kwargs)

        self.role = role
        self.content = content
        self.model_id = model_id
        self.token_count = token_count
        self.cost_usd = cost_usd
        self.response_time_ms = response_time_ms
        self.starred = starred
        self.on_regenerate = on_regenerate
        self.on_star = on_star

        self._content_label: Optional[Gtk.Label] = None
        self._copy_btn: Optional[Gtk.Button] = None
        self._regen_btn: Optional[Gtk.Button] = None
        self._star_btn: Optional[Gtk.Button] = None
        self._metadata_box: Optional[Gtk.Box] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the message UI with metadata and actions."""
        # Main container with message widget class for CSS targeting
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        container.add_css_class("message-widget")

        # Add role-specific CSS class
        if self.role == "user":
            container.add_css_class("user")
        else:
            container.add_css_class("assistant")

        # Header row with role label
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_hexpand(True)

        # Role label with improved styling
        role_label = Gtk.Label()
        role_label.set_halign(Gtk.Align.START)
        role_label.set_hexpand(True)
        role_label.add_css_class("message-role-label")

        if self.role == "user":
            role_label.set_text("You")
            role_label.add_css_class("user")
        else:
            role_label.set_text("Assistant")
            role_label.add_css_class("assistant")

        header_box.append(role_label)

        # Action buttons (copy, regenerate, star)
        self._build_action_buttons(header_box)
        container.append(header_box)

        # Content container with card-like styling
        content_frame = Adw.Bin()
        content_frame.add_css_class("message-content")

        # Render content with basic markdown
        # Apply length limit only to user input, not server responses
        content_to_render = self.content
        if self.role == "user" and len(content_to_render) > _MAX_CONTENT_LENGTH:
            content_to_render = content_to_render[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
        rendered_content = self._render_markdown(content_to_render)

        # Content label with better typography
        self._content_label = Gtk.Label(label=rendered_content)
        self._content_label.set_halign(Gtk.Align.START)
        self._content_label.set_hexpand(True)
        self._content_label.set_wrap(True)
        self._content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._content_label.set_xalign(0.0)
        self._content_label.set_selectable(True)
        self._content_label.add_css_class("body")

        # Use Pango markup for formatted content
        self._content_label.set_use_markup(True)

        content_frame.set_child(self._content_label)
        container.append(content_frame)

        # Metadata footer (model, tokens, cost, time)
        if self.role == "assistant":
            self._metadata_box = self._add_metadata_footer()
            container.append(self._metadata_box)

        # Add hover controller for showing/hiding action buttons
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self._on_mouse_enter)
        motion_controller.connect("leave", self._on_mouse_leave)
        container.add_controller(motion_controller)

        # Initially hide action buttons
        self._set_action_buttons_opacity(0)

        self.set_child(container)

    def _build_action_buttons(self, parent: Gtk.Box) -> None:
        """Build and add action buttons to the parent container.

        Args:
            parent: The parent box to add buttons to
        """
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        actions_box.set_halign(Gtk.Align.END)
        actions_box.add_css_class("message-actions")

        # Regenerate button (assistant only)
        if self.role == "assistant" and self.on_regenerate:
            self._regen_btn = Gtk.Button(icon_name="view-refresh-symbolic")
            self._regen_btn.add_css_class("flat")
            self._regen_btn.add_css_class("circular")
            self._regen_btn.set_tooltip_text("Regenerate response")
            self._regen_btn.set_valign(Gtk.Align.CENTER)
            self._regen_btn.connect("clicked", lambda _: self.on_regenerate())
            actions_box.append(self._regen_btn)

        # Star button (assistant only)
        if self.role == "assistant" and self.on_star:
            star_icon = "starred-symbolic" if self.starred else "non-starred-symbolic"
            self._star_btn = Gtk.Button(icon_name=star_icon)
            self._star_btn.add_css_class("flat")
            self._star_btn.add_css_class("circular")
            self._star_btn.set_tooltip_text("Star message" if not self.starred else "Unstar message")
            self._star_btn.set_valign(Gtk.Align.CENTER)
            self._star_btn.connect("clicked", self._on_star_clicked)
            actions_box.append(self._star_btn)

        # Copy button (always)
        self._copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        self._copy_btn.add_css_class("flat")
        self._copy_btn.add_css_class("circular")
        self._copy_btn.add_css_class("message-copy-btn")
        self._copy_btn.set_tooltip_text("Copy message")
        self._copy_btn.set_valign(Gtk.Align.CENTER)
        self._copy_btn.connect("clicked", self._on_copy_clicked)
        actions_box.append(self._copy_btn)

        parent.append(actions_box)

    def _add_metadata_footer(self) -> Gtk.Box:
        """Add metadata footer with model, tokens, cost, and time.

        Returns:
            The metadata box widget
        """
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        metadata_box.add_css_class("message-metadata")

        # Model ID
        if self.model_id:
            model_label = Gtk.Label(label=self.model_id)
            model_label.add_css_class("dim-label")
            model_label.add_css_class("caption")
            model_label.add_css_class("caption-heading")
            metadata_box.append(model_label)

        # Token count
        if self.token_count is not None:
            tokens_label = Gtk.Label(label=f"{self.token_count:,} tokens")
            tokens_label.add_css_class("dim-label")
            tokens_label.add_css_class("caption")
            metadata_box.append(tokens_label)

        # Cost
        if self.cost_usd is not None:
            if self.cost_usd < 0.01:
                cost_str = f"${self.cost_usd * 1000:.1f}k"  # Display in mills for small values
            else:
                cost_str = f"${self.cost_usd:.4f}" if self.cost_usd < 0.01 else f"${self.cost_usd:.2f}"
            cost_label = Gtk.Label(label=cost_str)
            cost_label.add_css_class("dim-label")
            cost_label.add_css_class("caption")
            metadata_box.append(cost_label)

        # Response time
        if self.response_time_ms is not None and self.response_time_ms > 0:
            time_seconds = self.response_time_ms / 1000.0
            if time_seconds < 1:
                time_label = Gtk.Label(label=f"{self.response_time_ms}ms")
            else:
                time_label = Gtk.Label(label=f"{time_seconds:.1f}s")
            time_label.add_css_class("dim-label")
            time_label.add_css_class("caption")
            metadata_box.append(time_label)

        return metadata_box

    def _set_action_buttons_opacity(self, opacity: float) -> None:
        """Set opacity for all action buttons.

        Args:
            opacity: Opacity value (0.0 to 1.0)
        """
        if self._copy_btn:
            self._copy_btn.set_opacity(opacity)
        if self._regen_btn:
            self._regen_btn.set_opacity(opacity)
        if self._star_btn:
            self._star_btn.set_opacity(opacity)

    def _on_mouse_enter(
        self,
        controller: Gtk.EventControllerMotion,
        x: float,
        y: float,
    ) -> None:
        """Show action buttons on hover."""
        self._set_action_buttons_opacity(1)

    def _on_mouse_leave(self, controller: Gtk.EventControllerMotion) -> None:
        """Hide action buttons when mouse leaves."""
        self._set_action_buttons_opacity(0)

    def _on_copy_clicked(self, button: Gtk.Button) -> None:
        """Copy message content to clipboard."""
        # Get the raw content (without markdown rendering)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self.content)

        # Show feedback by temporarily changing icon
        button.set_icon_name("object-select-symbolic")
        button.set_tooltip_text("Copied!")

        # Reset icon after delay
        def reset_icon() -> bool:
            button.set_icon_name("edit-copy-symbolic")
            button.set_tooltip_text("Copy message")
            return False  # Don't repeat

        GLib.timeout_add(1500, reset_icon)

        # Also show toast if we can find the toast overlay
        self._show_copy_toast()

    def _on_star_clicked(self, button: Gtk.Button) -> None:
        """Handle star button click."""
        if self.on_star:
            # Toggle starred state
            self.starred = not self.starred

            # Update icon
            star_icon = "starred-symbolic" if self.starred else "non-starred-symbolic"
            button.set_icon_name(star_icon)
            button.set_tooltip_text("Unstar message" if self.starred else "Star message")

            # Call callback
            self.on_star(self.starred)

    def _show_copy_toast(self) -> None:
        """Try to show a toast notification for copy action."""
        # Walk up the widget hierarchy to find a ToastOverlay
        widget = self.get_parent()
        while widget is not None:
            if hasattr(widget, "toast_overlay"):
                widget.toast_overlay.add_toast(Adw.Toast(title="Copied to clipboard"))
                return
            # Check if this IS a ToastOverlay
            if isinstance(widget, Adw.ToastOverlay):
                widget.add_toast(Adw.Toast(title="Copied to clipboard"))
                return
            widget = widget.get_parent()

    def _render_markdown(self, text: str) -> str:
        """Convert basic markdown to Pango markup.

        Supports:
        - **bold** → <b>
        - *italic* → <i>
        - `inline code` → <tt>
        - ```code blocks``` → formatted blocks
        - [links](url) → clickable links (http/https/mailto only)

        Security: URLs are validated to only allow safe schemes.
        """
        if not text:
            return ""

        # Process in order: code blocks, inline code, links, bold, italic
        # Each replacement returns a list of (text, is_markup) tuples

        parts: list[tuple[str, bool]] = [(text, False)]

        # Helper to process parts list
        def process_parts(
            regex: re.Pattern[str],
            replacer: Callable[[re.Match[str]], str],
        ) -> list[tuple[str, bool]]:
            new_parts: list[tuple[str, bool]] = []
            for part_text, is_markup in parts:
                if is_markup:
                    new_parts.append((part_text, True))
                else:
                    last_end = 0
                    for match in regex.finditer(part_text):
                        # Add text before match
                        if match.start() > last_end:
                            new_parts.append((part_text[last_end:match.start()], False))
                        # Add replacement (markup)
                        new_parts.append((replacer(match), True))
                        last_end = match.end()
                    # Add remaining text
                    if last_end < len(part_text):
                        new_parts.append((part_text[last_end:], False))
            return new_parts

        # Code blocks ```code```
        def replace_code_block(match: re.Match[str]) -> str:
            code = match.group(2)
            escaped = GLib.markup_escape_text(code)
            # Use simple gray background (#f0f0f0) - alpha() and padding not supported in Pango
            return f'<span font_family="monospace" bgcolor="#f0f0f0">{escaped}</span>'

        parts = process_parts(_CODE_BLOCK_RE, replace_code_block)

        # Inline code `code`
        def replace_inline_code(match: re.Match[str]) -> str:
            code = match.group(1)
            escaped = GLib.markup_escape_text(code)
            # Use <span> instead of <tt> because <tt> doesn't support attributes
            # Use simple gray background (#f5f5f5) - alpha() not supported in Pango
            return f'<span font_family="monospace" bgcolor="#f5f5f5">{escaped}</span>'

        parts = process_parts(_INLINE_CODE_RE, replace_inline_code)

        # Links [text](url) - with URL scheme validation
        def replace_link(match: re.Match[str]) -> str:
            text_content = match.group(1)
            url = match.group(2)

            # Security: Only allow safe URL schemes
            if not url.lower().startswith(_ALLOWED_URL_SCHEMES):
                # Render as plain text, not a clickable link
                return GLib.markup_escape_text(match.group(0))

            escaped_text = GLib.markup_escape_text(text_content)
            escaped_url = GLib.markup_escape_text(url)
            return f'<a href="{escaped_url}">{escaped_text}</a>'

        parts = process_parts(_LINK_RE, replace_link)

        # Bold **text**
        def replace_bold(match: re.Match[str]) -> str:
            content = match.group(1)
            escaped = GLib.markup_escape_text(content)
            return f"<b>{escaped}</b>"

        parts = process_parts(_BOLD_RE, replace_bold)

        # Italic *text*
        def replace_italic(match: re.Match[str]) -> str:
            content = match.group(1)
            escaped = GLib.markup_escape_text(content)
            return f"<i>{escaped}</i>"

        parts = process_parts(_ITALIC_RE, replace_italic)

        # Combine parts
        result = []
        for part_text, is_markup in parts:
            if is_markup:
                result.append(part_text)
            else:
                result.append(GLib.markup_escape_text(part_text))

        return "".join(result)

    def update_content(self, content: str) -> None:
        """Update message content (for streaming).

        Args:
            content: New content to display
        """
        self.content = content
        if self._content_label:
            # Apply length limit only to user input, not server responses
            content_to_render = content
            if self.role == "user" and len(content_to_render) > _MAX_CONTENT_LENGTH:
                content_to_render = content_to_render[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
            self._content_label.set_label(self._render_markdown(content_to_render))

    def update_metadata(
        self,
        token_count: Optional[int] = None,
        cost_usd: Optional[float] = None,
        response_time_ms: Optional[int] = None,
    ) -> None:
        """Update metadata display.

        Args:
            token_count: New token count
            cost_usd: New cost in USD
            response_time_ms: New response time in milliseconds
        """
        if token_count is not None:
            self.token_count = token_count
        if cost_usd is not None:
            self.cost_usd = cost_usd
        if response_time_ms is not None:
            self.response_time_ms = response_time_ms

        # Rebuild metadata footer
        if self._metadata_box:
            parent = self._metadata_box.get_parent()
            if parent:
                parent.remove(self._metadata_box)
            self._metadata_box = self._add_metadata_footer()
            parent.append(self._metadata_box)
