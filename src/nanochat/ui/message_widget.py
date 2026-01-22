"""Widget for displaying a single chat message."""

import re
from collections.abc import Callable
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Pango, Gdk, GLib

# Syntax highlighting support
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatter import Formatter
    _PYGMENTS_AVAILABLE = True
except ImportError:
    _PYGMENTS_AVAILABLE = False

# Pre-compiled regex patterns for markdown parsing (performance optimization)
_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"\*([^*]+)\*")
# New patterns for extended markdown
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$")  # Headers
_BLOCKQUOTE_RE = re.compile(r"^>\s*(.+)$")  # Blockquotes
_HR_RE = re.compile(r"^(?:-{3,}|\*{3,})\s*$")  # Horizontal rules
_LIST_RE = re.compile(r"^([*\-+]|\d+\.)\s+(.+)$")  # Lists (unordered and ordered)
_TABLE_RE = re.compile(r"^\|(.+)\|$")  # Table rows
_TABLE_SEPARATOR_RE = re.compile(r"^\|[\s\-:]+\|$")  # Table separator (e.g., |---|)

# Security: Only allow safe URL schemes for links
_ALLOWED_URL_SCHEMES = ("http://", "https://", "mailto:")

# Maximum content length to prevent DoS via extremely long messages
_MAX_CONTENT_LENGTH = 5000


class PangoFormatter(Formatter):
    """Custom Pygments formatter that outputs Pango markup.

    Pygments token types are mapped to Pango markup spans with
    appropriate foreground colors for syntax highlighting.
    """

    # Map pygments token types to Pango foreground colors
    # Colors chosen to match common syntax highlighting themes
    TOKEN_COLORS = {
        # Keywords (if, def, class, return, etc.)
        "Token.Keyword": "#0000ff",  # Blue
        "Token.Keyword.Constant": "#0000ff",
        "Token.Keyword.Declaration": "#0000ff",
        "Token.Keyword.Namespace": "#0000ff",
        "Token.Keyword.Type": "#0000ff",
        "Token.Keyword.Reserved": "#0000ff",
        # Names (function names, class names)
        "Token.Name": "#000000",
        "Token.Name.Function": "#000000",
        "Token.Name.Class": "#a31515",  # Dark red
        "Token.Name.Exception": "#a31515",
        "Token.Name.Decorator": "#a31515",
        "Token.Name.Builtin": "#a31515",
        "Token.Name.Builtin.Pseudo": "#a31515",
        # Operators
        "Token.Operator": "#000000",
        "Token.Operator.Word": "#0000ff",
        # Strings
        "Token.Literal.String": "#a31515",  # Dark red
        "Token.Literal.String.Single": "#a31515",
        "Token.Literal.String.Double": "#a31515",
        "Token.Literal.String.Triple": "#a31515",
        "Token.Literal.String.Char": "#a31515",
        # Numbers
        "Token.Literal.Number": "#098658",  # Green
        "Token.Literal.Number.Integer": "#098658",
        "Token.Literal.Number.Float": "#098658",
        "Token.Literal.Number.Hex": "#098658",
        "Token.Literal.Number.Oct": "#098658",
        # Comments
        "Token.Comment": "#008000",  # Green
        "Token.Comment.Single": "#008000",
        "Token.Comment.Multi": "#008000",
        "Token.Comment.Special": "#008000",
        "Token.Comment.Preproc": "#0000ff",  # Blue for preprocessor
        # Other
        "Token.Punctuation": "#000000",
        "Token.Text": "#000000",
        "Token.Text.Whitespace": "#000000",
        "Token.Generic": "#000000",
        "Token.Generic.Error": "#ff0000",  # Red
        "Token.Generic.Heading": "#000000",
        "Token.Generic.Subheading": "#000000",
        "Token.Generic.Deleted": "#ff0000",
        "Token.Generic.Inserted": "#008000",
        "Token.Generic.Emph": "#000000",
        "Token.Generic.Strong": "#000000",
        "Token.Generic.Prompt": "#000000",
        "Token.Generic.Output": "#000000",
        "Token.Generic.Traceback": "#ff0000",
    }

    def __init__(self, **options: object) -> None:
        super().__init__(**options)

    def format(self, tokensource: tuple[tuple[object, str], ...]) -> str:
        """Format tokens as Pango markup.

        Args:
            tokensource: Iterator of (token_type, value) pairs from pygments

        Returns:
            Pango markup string with color spans
        """
        output = []
        for token_type, value in tokensource:
            # Get the token type string
            token_str = str(token_type)

            # Look up color for this token type
            color = self.TOKEN_COLORS.get(token_str, None)

            # Escape the value for Pango markup
            escaped = GLib.markup_escape_text(value)

            if color and value.strip():  # Only add span if we have a color and non-whitespace
                output.append(f'<span foreground="{color}">{escaped}</span>')
            else:
                output.append(escaped)

        return "".join(output)


class MessageWidget(Adw.Bin):  # type: ignore[misc]
    """Widget for displaying a single chat message with metadata and actions."""

    def __init__(
        self,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        model_id: Optional[str] = None,
        token_count: Optional[int] = None,
        cost_usd: Optional[float] = None,
        response_time_ms: Optional[int] = None,
        starred: bool = False,
        reasoning: Optional[str] = None,
        on_regenerate: Optional[Callable[[], None]] = None,
        on_star: Optional[Callable[[str, bool], None]] = None,
        **kwargs: object,
    ) -> None:
        """Initialize a message widget.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            message_id: ID of the message (for starring operations)
            model_id: ID of the model used (for assistant messages)
            token_count: Number of tokens used
            cost_usd: Cost in USD
            response_time_ms: Response time in milliseconds
            starred: Whether the message is starred
            reasoning: Model reasoning/thinking content (for reasoning models)
            on_regenerate: Callback when regenerate is clicked
            on_star: Callback when star toggle is clicked
        """
        super().__init__(**kwargs)

        self.message_id = message_id
        self.role = role
        self.content = content
        self.model_id = model_id
        self.token_count = token_count
        self.cost_usd = cost_usd
        self.response_time_ms = response_time_ms
        self.starred = starred
        self.reasoning = reasoning
        self.on_regenerate = on_regenerate
        self.on_star = on_star

        self._content_label: Optional[Gtk.Label] = None
        self._copy_btn: Optional[Gtk.Button] = None
        self._regen_btn: Optional[Gtk.Button] = None
        self._star_btn: Optional[Gtk.Button] = None
        self._metadata_box: Optional[Gtk.Box] = None
        self._reasoning_expander: Optional[Gtk.Expander] = None

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

        # Reasoning section (collapsible, for assistant messages with reasoning)
        if self.reasoning and self.role == "assistant":
            self._add_reasoning_section(container)

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

    def _add_reasoning_section(self, container: Gtk.Box) -> None:
        """Add collapsible reasoning section to the container.

        Args:
            container: The parent container to add the expander to
        """
        expander = Gtk.Expander()
        expander.set_label("💭 Thinking")
        expander.add_css_class("reasoning-expander")
        expander.set_expanded(False)  # Start collapsed

        # Reasoning content label
        reasoning_label = Gtk.Label(label=self.reasoning)
        reasoning_label.set_wrap(True)
        reasoning_label.set_xalign(0.0)
        reasoning_label.add_css_class("dim-label")
        reasoning_label.add_css_class("reasoning-content")

        expander.set_child(reasoning_label)
        container.append(expander)

        # Store reference for potential updates
        self._reasoning_expander = expander

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
        if self.on_star and self.message_id:
            # Toggle starred state
            self.starred = not self.starred

            # Update icon
            star_icon = "starred-symbolic" if self.starred else "non-starred-symbolic"
            button.set_icon_name(star_icon)
            button.set_tooltip_text("Unstar message" if self.starred else "Star message")

            # Call callback with message_id and new starred state
            self.on_star(self.message_id, self.starred)

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
        """Convert markdown to Pango markup.

        Supports:
        Block-level:
        - # Headers (H1-H6) with size attributes
        - - Unordered lists (with • bullets)
        - 1. Ordered lists (with numbers)
        - > Blockquotes (italic)
        - --- Horizontal rules
        - | Tables (with | delimiters)
        Inline:
        - **bold** → <b>
        - *italic* → <i>
        - `inline code` → <tt> with background
        - ```code blocks``` → formatted with syntax highlighting
        - [links](url) → clickable links (http/https/mailto only)

        Security: URLs are validated to only allow safe schemes.
        """
        if not text:
            return ""

        lines = text.split("\n")
        result_lines: list[str] = []
        in_code_block = False
        code_lines: list[str] = []
        code_lang = ""

        # First pass: handle code blocks and collect non-code lines
        for line in lines:
            # Check for code block start/end
            if line.strip().startswith("```"):
                if in_code_block:
                    # End code block - render it with syntax highlighting
                    in_code_block = False
                    if code_lines:
                        code = "\n".join(code_lines)
                        formatted_code = self._highlight_code(code, code_lang)
                        result_lines.append(formatted_code)
                    code_lines = []
                    code_lang = ""
                else:
                    # Start code block - extract language
                    in_code_block = True
                    code_lang = line.strip()[3:].strip()  # Get language after ```
                    code_lines = []
                continue

            if in_code_block:
                # Collect code lines
                code_lines.append(line)
            else:
                result_lines.append(line)

        # Second pass: process each line for block-level and inline formatting
        formatted_lines: list[str] = []
        in_list = False
        list_indent = 0
        in_table = False
        table_rows: list[list[str]] = []

        for line in result_lines:
            # Check for table row
            table_match = _TABLE_RE.match(line)
            if table_match:
                # Check if this is a separator row (|---|)
                if _TABLE_SEPARATOR_RE.match(line):
                    # Skip separator rows, but mark that we're in a table
                    if table_rows:
                        # We have collected header rows, render them
                        formatted_lines.extend(self._format_table(table_rows))
                        table_rows = []
                    in_table = True
                    continue

                # Parse the table row
                cells = [cell.strip() for cell in table_match.group(1).split("|")]
                table_rows.append(cells)
                continue

            # If we were in a table and now we're not, flush any remaining table
            if in_table and not table_match:
                if table_rows:
                    formatted_lines.extend(self._format_table(table_rows))
                    table_rows = []
                in_table = False

            # Skip empty lines (but add them for spacing between blocks)
            if not line.strip():
                formatted_lines.append("")
                # Reset list context on blank line
                in_list = False
                continue

            # Check for horizontal rule
            if _HR_RE.match(line):
                formatted_lines.append("")  # Add spacing before
                formatted_lines.append("—")  # Horizontal rule using em dash
                formatted_lines.append("")  # Add spacing after
                in_list = False
                continue

            # Check for header
            header_match = _HEADER_RE.match(line)
            if header_match:
                level = len(header_match.group(1))  # Number of # characters
                content = header_match.group(2)
                escaped_content = GLib.markup_escape_text(content)
                # Use size attribute: 1=xx-large, 2=x-large, 3=large, 4=medium, 5=small, 6=x-small
                size_map = {1: "xx-large", 2: "x-large", 3: "large", 4: "medium", 5: "small", 6: "x-small"}
                size_attr = size_map.get(level, "medium")
                formatted_lines.append(f'<span size="{size_attr}" weight="bold">{escaped_content}</span>')
                in_list = False
                continue

            # Check for blockquote
            blockquote_match = _BLOCKQUOTE_RE.match(line)
            if blockquote_match:
                content = blockquote_match.group(1)
                # Apply inline formatting and wrap in italics
                formatted = self._format_inline(content)
                formatted_lines.append(f"<i>{formatted}</i>")
                in_list = False
                continue

            # Check for list item
            list_match = _LIST_RE.match(line)
            if list_match:
                marker = list_match.group(1)
                content = list_match.group(2)
                # Determine list type and indent
                if marker in ("*", "-", "+"):
                    # Unordered list
                    formatted = self._format_inline(content)
                    formatted_lines.append(f" • {formatted}")
                else:
                    # Ordered list (marker ends with ".")
                    formatted = self._format_inline(content)
                    formatted_lines.append(f" {marker} {formatted}")
                in_list = True
                continue

            # Regular paragraph line - apply inline formatting
            formatted_lines.append(self._format_inline(line))

        # Flush any remaining table
        if table_rows:
            formatted_lines.extend(self._format_table(table_rows))

        # Join lines with newlines
        return "\n".join(formatted_lines)

    def _format_inline(self, text: str) -> str:
        """Apply inline markdown formatting (bold, italic, code, links).

        Args:
            text: Text to format

        Returns:
            Formatted text with Pango markup
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

        # Inline code `code`
        def replace_inline_code(match: re.Match[str]) -> str:
            code = match.group(1)
            escaped = GLib.markup_escape_text(code)
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

    def _highlight_code(self, code: str, lang: str) -> str:
        """Apply syntax highlighting to code using pygments.

        Args:
            code: The source code to highlight
            lang: The language identifier (e.g., "python", "javascript")

        Returns:
            Pango markup with syntax highlighting, or plain monospace text
            if pygments is not available or language is not recognized.
        """
        if not code:
            return ""

        # If pygments is not available, fall back to plain code
        if not _PYGMENTS_AVAILABLE:
            escaped = GLib.markup_escape_text(code)
            return f'<span font_family="monospace" bgcolor="#f0f0f0">{escaped}</span>'

        try:
            # Get the appropriate lexer for the language
            if lang:
                try:
                    lexer = get_lexer_by_name(lang)
                except Exception:
                    # Language not recognized, try to guess
                    try:
                        lexer = guess_lexer(code)
                    except Exception:
                        lexer = TextLexer()
            else:
                # No language specified, try to guess or use text
                try:
                    lexer = guess_lexer(code)
                except Exception:
                    lexer = TextLexer()

            # Highlight the code using our custom Pango formatter
            formatter = PangoFormatter()
            highlighted = highlight(code, lexer, formatter)

            # Wrap in monospace span with background
            return f'<span font_family="monospace" bgcolor="#f0f0f0">{highlighted}</span>'
        except Exception:
            # Fall back to plain code if highlighting fails
            escaped = GLib.markup_escape_text(code)
            return f'<span font_family="monospace" bgcolor="#f0f0f0">{escaped}</span>'

    def _format_table(self, rows: list[list[str]]) -> list[str]:
        """Format table rows as Pango markup.

        Args:
            rows: List of table rows, where each row is a list of cell contents

        Returns:
            List of formatted Pango markup strings representing the table
        """
        if not rows:
            return []

        # Find the maximum number of columns
        max_cols = max(len(row) for row in rows) if rows else 0
        if max_cols == 0:
            return []

        # Calculate column widths based on cell content
        col_widths: list[int] = [0] * max_cols
        for row in rows:
            for i, cell in enumerate(row):
                if i < max_cols:
                    # Apply inline formatting to cell content
                    formatted_cell = self._format_inline(cell)
                    # Strip markup for width calculation (rough approximation)
                    # We'll use a simpler approach: just count characters
                    col_widths[i] = max(col_widths[i], len(cell))

        # Format each row
        formatted_rows: list[str] = []
        for row_idx, row in enumerate(rows):
            # Build the row with column separators
            row_cells: list[str] = []
            for col_idx in range(max_cols):
                if col_idx < len(row):
                    # Apply inline formatting to cell content
                    cell_content = self._format_inline(row[col_idx])
                    row_cells.append(cell_content)
                else:
                    row_cells.append("")  # Empty cell

            # Join cells with " | " separator
            formatted_row = " | ".join(row_cells)

            # Make header row bold
            if row_idx == 0:
                formatted_row = f"<b>{formatted_row}</b>"

            formatted_rows.append(formatted_row)

        # Add spacing before and after table
        formatted_rows.insert(0, "")
        formatted_rows.append("")

        return formatted_rows

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

    def update_reasoning(self, reasoning: str) -> None:
        """Update reasoning content (for streaming).

        Args:
            reasoning: New reasoning content to display
        """
        self.reasoning = reasoning

        if self._reasoning_expander:
            # Update the label content
            child = self._reasoning_expander.get_child()
            if isinstance(child, Gtk.Label):
                child.set_label(reasoning)
