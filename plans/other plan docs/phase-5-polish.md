# Phase 5: Polish and Release

**Version**: v0.5.0 → v1.0.0  
**Branch**: `v0.5.0`  
**Prerequisites**: Phase 4 complete (v0.4.0)

---

## Overview

Phase 5 focuses on polish, theming, accessibility, and preparing for public release. This phase transforms the application from a functional tool into a polished, user-friendly product ready for distribution.

---

## Pre-Phase Tasks

### Human Tasks

1. **Create branch from v0.4.0**
   ```bash
   git checkout v0.4.0
   git checkout -b v0.5.0
   git push -u origin v0.5.0
   ```

2. **Gather user feedback** from previous phases
3. **Review accessibility guidelines** (GNOME HIG)
4. **Prepare app store assets** (screenshots, descriptions)

---

## Implementation Tasks

### Task 5.1: Catppuccin Theme Support

**Goal**: Add Catppuccin color palette support

**Reference**: https://catppuccin.com/palette

**Files to create:**
- `src/nanochat/ui/themes/catppuccin.py`
- `data/styles/catppuccin-latte.css`
- `data/styles/catppuccin-mocha.css`

**Implementation:**

```python
# src/nanochat/ui/themes/catppuccin.py
"""Catppuccin theme definitions."""

CATPPUCCIN_LATTE = {
    "rosewater": "#dc8a78",
    "flamingo": "#dd7878",
    "pink": "#ea76cb",
    "mauve": "#8839ef",
    "red": "#d20f39",
    "maroon": "#e64553",
    "peach": "#fe640b",
    "yellow": "#df8e1d",
    "green": "#40a02b",
    "teal": "#179299",
    "sky": "#04a5e5",
    "sapphire": "#209fb5",
    "blue": "#1e66f5",
    "lavender": "#7287fd",
    "text": "#4c4f69",
    "subtext1": "#5c5f77",
    "subtext0": "#6c6f85",
    "overlay2": "#7c7f93",
    "overlay1": "#8c8fa1",
    "overlay0": "#9ca0b0",
    "surface2": "#acb0be",
    "surface1": "#bcc0cc",
    "surface0": "#ccd0da",
    "base": "#eff1f5",
    "mantle": "#e6e9ef",
    "crust": "#dce0e8"
}

CATPPUCCIN_MOCHA = {
    "rosewater": "#f5e0dc",
    "flamingo": "#f2cdcd",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "red": "#f38ba8",
    "maroon": "#eba0ac",
    "peach": "#fab387",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "teal": "#94e2d5",
    "sky": "#89dceb",
    "sapphire": "#74c7ec",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "text": "#cdd6f4",
    "subtext1": "#bac2de",
    "subtext0": "#a6adc8",
    "overlay2": "#9399b2",
    "overlay1": "#7f849c",
    "overlay0": "#6c7086",
    "surface2": "#585b70",
    "surface1": "#45475a",
    "surface0": "#313244",
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b"
}
```

**CSS Generation:**
```python
def generate_catppuccin_css(variant: str = "mocha") -> str:
    colors = CATPPUCCIN_MOCHA if variant == "mocha" else CATPPUCCIN_LATTE
    
    return f"""
    /* Catppuccin {variant.title()} */
    @define-color accent_color {colors['mauve']};
    @define-color accent_bg_color {colors['mauve']};
    @define-color accent_fg_color {colors['base']};
    
    @define-color window_bg_color {colors['base']};
    @define-color window_fg_color {colors['text']};
    
    @define-color view_bg_color {colors['mantle']};
    @define-color view_fg_color {colors['text']};
    
    @define-color headerbar_bg_color {colors['crust']};
    @define-color headerbar_fg_color {colors['text']};
    
    @define-color card_bg_color {colors['surface0']};
    @define-color card_fg_color {colors['text']};
    
    @define-color sidebar_bg_color {colors['mantle']};
    @define-color sidebar_fg_color {colors['text']};
    
    @define-color popover_bg_color {colors['surface0']};
    @define-color popover_fg_color {colors['text']};
    
    @define-color success_color {colors['green']};
    @define-color warning_color {colors['yellow']};
    @define-color error_color {colors['red']};
    """
```

**Theme application:**
```python
def apply_catppuccin_theme(variant: str):
    css = generate_catppuccin_css(variant)
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
```

**Acceptance Criteria:**
- [ ] Catppuccin Latte (light) theme works
- [ ] Catppuccin Mocha (dark) theme works
- [ ] Theme selectable in settings
- [ ] All UI elements styled consistently

---

### Task 5.2: Tokyo Night Theme Support

**Goal**: Add Tokyo Night color palette

**Reference**: https://github.com/enkia/tokyo-night-vscode-theme

```python
# src/nanochat/ui/themes/tokyo_night.py
"""Tokyo Night theme definitions."""

TOKYO_NIGHT = {
    # Background colors
    "bg": "#1a1b26",
    "bg_dark": "#16161e",
    "bg_highlight": "#292e42",
    "terminal_black": "#414868",
    
    # Foreground colors
    "fg": "#c0caf5",
    "fg_dark": "#a9b1d6",
    "fg_gutter": "#3b4261",
    
    # Text colors
    "dark3": "#545c7e",
    "dark5": "#737aa2",
    "comment": "#565f89",
    
    # Accent colors
    "blue": "#7aa2f7",
    "cyan": "#7dcfff",
    "blue1": "#2ac3de",
    "blue2": "#0db9d7",
    "blue5": "#89ddff",
    "magenta": "#bb9af7",
    "purple": "#9d7cd8",
    "orange": "#ff9e64",
    "yellow": "#e0af68",
    "green": "#9ece6a",
    "teal": "#1abc9c",
    "red": "#f7768e",
    "red1": "#db4b4b"
}

TOKYO_NIGHT_LIGHT = {
    "bg": "#d5d6db",
    "bg_dark": "#c0c1c6",
    "bg_highlight": "#b4b5b9",
    "fg": "#343b58",
    "fg_dark": "#4c505e",
    "blue": "#34548a",
    "cyan": "#0f4b6e",
    "green": "#33635c",
    "magenta": "#5a4a78",
    "orange": "#965027",
    "red": "#8c4351",
    "yellow": "#8f5e15"
}
```

**Acceptance Criteria:**
- [ ] Tokyo Night (dark) theme works
- [ ] Tokyo Night Light theme works
- [ ] Theme selectable in settings

---

### Task 5.3: Theme Manager

**Goal**: Centralized theme management with persistence

**Files to create:**
- `src/nanochat/ui/themes/manager.py`

```python
class ThemeManager:
    """Manages application themes."""
    
    THEMES = {
        "system": "System Default",
        "light": "Light",
        "dark": "Dark",
        "catppuccin-latte": "Catppuccin Latte",
        "catppuccin-mocha": "Catppuccin Mocha",
        "tokyo-night": "Tokyo Night",
        "tokyo-night-light": "Tokyo Night Light"
    }
    
    def __init__(self, settings_manager):
        self._settings = settings_manager
        self._provider = Gtk.CssProvider()
    
    def get_available_themes(self) -> dict[str, str]:
        return self.THEMES.copy()
    
    def get_current_theme(self) -> str:
        return self._settings.settings.ui.theme
    
    def apply_theme(self, theme_id: str):
        """Apply the specified theme."""
        # Remove previous custom CSS
        Gtk.StyleContext.remove_provider_for_display(
            Gdk.Display.get_default(),
            self._provider
        )
        
        manager = Adw.StyleManager.get_default()
        
        if theme_id == "system":
            manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
        elif theme_id == "light":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme_id == "dark":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif theme_id.startswith("catppuccin"):
            variant = "latte" if "latte" in theme_id else "mocha"
            scheme = Adw.ColorScheme.FORCE_LIGHT if variant == "latte" else Adw.ColorScheme.FORCE_DARK
            manager.set_color_scheme(scheme)
            self._apply_custom_css(generate_catppuccin_css(variant))
        elif theme_id.startswith("tokyo"):
            is_light = "light" in theme_id
            scheme = Adw.ColorScheme.FORCE_LIGHT if is_light else Adw.ColorScheme.FORCE_DARK
            manager.set_color_scheme(scheme)
            self._apply_custom_css(generate_tokyo_night_css(is_light))
        
        # Save preference
        self._settings.settings.ui.theme = theme_id
        self._settings.save()
    
    def _apply_custom_css(self, css: str):
        self._provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self._provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
```

**Theme selector in settings:**
```python
# In SetupDialog
theme_group = Adw.PreferencesGroup()
theme_group.set_title("Appearance")

theme_row = Adw.ComboRow()
theme_row.set_title("Theme")
themes = self._theme_manager.get_available_themes()
theme_row.set_model(Gtk.StringList.new(list(themes.values())))
theme_row.connect("notify::selected", self._on_theme_changed)
```

**Acceptance Criteria:**
- [ ] Theme selector shows all themes
- [ ] Theme changes apply immediately
- [ ] Theme preference persists
- [ ] Custom themes override correctly

---

### Task 5.4: Responsive Layout

**Goal**: Support different window sizes gracefully

**Implementation:**

Use Libadwaita's adaptive components:

```python
class NanoChatWindow(Adw.ApplicationWindow):
    def _setup_ui(self):
        # Use NavigationSplitView for responsive sidebar
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_collapsed(False)
        self.split_view.set_sidebar_width_fraction(0.25)
        self.split_view.set_min_sidebar_width(200)
        self.split_view.set_max_sidebar_width(400)
        
        # Connect to size changes
        self.connect("notify::default-width", self._on_size_changed)
    
    def _on_size_changed(self, window, param):
        width = window.get_width()
        
        # Collapse sidebar on narrow windows
        if width < 600:
            self.split_view.set_collapsed(True)
        else:
            self.split_view.set_collapsed(False)
```

**Breakpoint handling:**
```python
# Define breakpoints
BREAKPOINTS = {
    "compact": 400,   # Phone-like
    "medium": 600,    # Small tablet
    "expanded": 840   # Desktop
}

def _get_breakpoint(self, width: int) -> str:
    if width < BREAKPOINTS["compact"]:
        return "compact"
    elif width < BREAKPOINTS["medium"]:
        return "medium"
    else:
        return "expanded"
```

**Acceptance Criteria:**
- [ ] Sidebar collapses on narrow windows
- [ ] Content remains usable at all sizes
- [ ] Minimum window size enforced
- [ ] Smooth transitions between layouts

---

### Task 5.5: Accessibility Improvements

**Goal**: Ensure app is accessible to all users

**Implementation:**

1. **Proper labels and tooltips:**
```python
# Every interactive element needs accessible name
button.set_tooltip_text("Send message")
button.get_accessible().set_name("Send message button")

# Or use accessible properties
button.set_property("accessible-label", "Send message")
```

2. **Keyboard navigation:**
```python
# Ensure all actions are keyboard accessible
def _setup_keyboard_nav(self):
    # Tab order
    self.message_entry.grab_focus()
    
    # Arrow key navigation in lists
    self.conversation_list.set_activate_on_single_click(False)
```

3. **High contrast support:**
```css
/* Ensure sufficient contrast */
@media (prefers-contrast: more) {
    .message-bubble {
        border: 2px solid @borders;
    }
    
    .dim-label {
        opacity: 0.8;  /* Don't fully dim */
    }
}
```

4. **Screen reader support:**
```python
# Announce dynamic content
def _announce(self, message: str):
    """Announce message to screen readers."""
    announcer = Gtk.Accessible()
    announcer.announce(message, Gtk.AccessibleAnnouncementPriority.MEDIUM)
```

5. **Focus indicators:**
```css
/* Clear focus indicators */
:focus-visible {
    outline: 2px solid @accent_color;
    outline-offset: 2px;
}
```

**Acceptance Criteria:**
- [ ] All buttons have tooltips
- [ ] Keyboard navigation works throughout
- [ ] Tab order is logical
- [ ] Screen reader can read messages
- [ ] Focus visually clear
- [ ] High contrast mode supported

---

### Task 5.6: Error Handling and Recovery

**Goal**: Graceful error handling with user-friendly messages

**Implementation:**

1. **Error dialog:**
```python
class ErrorDialog(Adw.MessageDialog):
    """Dialog for displaying errors."""
    
    def __init__(self, parent, title: str, message: str, details: str = None):
        super().__init__()
        self.set_transient_for(parent)
        self.set_heading(title)
        self.set_body(message)
        
        if details:
            self.set_extra_child(
                Gtk.Label(label=details, selectable=True, wrap=True)
            )
        
        self.add_response("close", "Close")
        self.set_default_response("close")
```

2. **Network error handling:**
```python
async def _safe_api_call(self, coro):
    """Wrap API calls with error handling."""
    try:
        return await coro
    except ConnectionError:
        self._show_toast("Cannot connect to server")
        return None
    except AuthenticationError:
        self._show_error_dialog(
            "Authentication Error",
            "Your API key is invalid or expired.",
            "Please check your settings."
        )
        self._show_setup_dialog()
        return None
    except RateLimitError:
        self._show_toast("Rate limit exceeded. Please wait.")
        return None
    except Exception as e:
        self._show_error_dialog(
            "Error",
            "An unexpected error occurred.",
            str(e)
        )
        return None
```

3. **Recovery mechanisms:**
```python
def _setup_reconnection(self):
    """Attempt to reconnect on connection loss."""
    self._reconnect_attempts = 0
    self._max_reconnect_attempts = 3
    
async def _attempt_reconnect(self):
    if self._reconnect_attempts >= self._max_reconnect_attempts:
        self._show_error_dialog(
            "Connection Lost",
            "Unable to reconnect to server.",
            "Please check your network connection."
        )
        return
    
    self._reconnect_attempts += 1
    self._show_toast(f"Reconnecting... (attempt {self._reconnect_attempts})")
    
    await asyncio.sleep(2 ** self._reconnect_attempts)  # Exponential backoff
    
    if await self._api_client.test_connection():
        self._reconnect_attempts = 0
        self._show_toast("Connected")
    else:
        await self._attempt_reconnect()
```

**Acceptance Criteria:**
- [ ] Network errors show friendly messages
- [ ] Auth errors prompt re-authentication
- [ ] Rate limits handled gracefully
- [ ] Automatic reconnection attempted
- [ ] User can always dismiss errors

---

### Task 5.7: Performance Optimization

**Goal**: Ensure smooth performance

**Implementation:**

1. **Lazy loading:**
```python
# Only load visible conversations
def _load_conversations_lazy(self):
    # Load first 20
    conversations = await self._api_client.get_conversations(limit=20)
    self._populate_conversation_list(conversations)
    
    # Load more on scroll
    self._conversation_list.connect(
        "edge-reached", 
        self._on_edge_reached
    )

async def _on_edge_reached(self, widget, pos):
    if pos == Gtk.PositionType.BOTTOM:
        await self._load_more_conversations()
```

2. **Message virtualization:**
```python
# Use ListView with factory for efficient rendering
factory = Gtk.SignalListItemFactory()
factory.connect("setup", self._on_message_setup)
factory.connect("bind", self._on_message_bind)
factory.connect("unbind", self._on_message_unbind)

list_view = Gtk.ListView(factory=factory)
list_view.set_model(self._messages_model)
```

3. **Background sync:**
```python
# Sync in background, don't block UI
async def _background_sync(self):
    while True:
        await asyncio.sleep(60)  # Every minute
        await self._sync_conversations()
```

4. **Cache management:**
```python
def _cleanup_cache(self):
    """Remove old cached data."""
    cache_dir = get_cache_dir()
    cutoff = datetime.now() - timedelta(days=7)
    
    for file in cache_dir.iterdir():
        if file.stat().st_mtime < cutoff.timestamp():
            file.unlink()
```

**Acceptance Criteria:**
- [ ] App launches quickly (<2s)
- [ ] Scrolling is smooth
- [ ] Large conversation lists perform well
- [ ] Memory usage stays reasonable
- [ ] No UI freezes during API calls

---

### Task 5.8: App Icon and Branding

**Goal**: Create polished app icon and branding

**Human Tasks:**

1. Create app icon:
   - 512x512 PNG for high-res displays
   - 256x256, 128x128, 64x64, 48x48, 32x32, 16x16 sizes
   - SVG source file

2. Icon design guidelines:
   - Simple, recognizable silhouette
   - Works at small sizes
   - Follows GNOME icon guidelines
   - Consider Catppuccin/Tokyo Night accent colors

**Files to create:**
```
data/icons/
├── hicolor/
│   ├── scalable/
│   │   └── apps/
│   │       └── com.nanogpt.NanoChat.svg
│   ├── 512x512/
│   │   └── apps/
│   │       └── com.nanogpt.NanoChat.png
│   └── ... (other sizes)
└── symbolic/
    └── com.nanogpt.NanoChat-symbolic.svg
```

**Desktop file:**
```ini
[Desktop Entry]
Name=NanoChat
Comment=AI Chat Client
Exec=nanochat
Icon=com.nanogpt.NanoChat
Type=Application
Categories=Network;Chat;
Keywords=chat;ai;gpt;llm;
StartupNotify=true
```

**Acceptance Criteria:**
- [ ] Icon crisp at all sizes
- [ ] Icon follows platform guidelines
- [ ] Desktop file complete
- [ ] App appears in app menu

---

### Task 5.9: Flatpak Metadata

**Goal**: Complete Flatpak metadata for app store

**Files to create:**
- `flatpak/com.nanogpt.NanoChat.metainfo.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.nanogpt.NanoChat</id>
  <name>NanoChat</name>
  <summary>AI Chat Client for NanoChat API</summary>
  
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>MIT</project_license>
  
  <description>
    <p>
      NanoChat is a native Linux desktop client for the NanoChat API,
      providing a fast and intuitive interface for AI-powered conversations.
    </p>
    <p>Features:</p>
    <ul>
      <li>Stream AI responses in real-time</li>
      <li>Organize conversations with projects</li>
      <li>Customize AI behavior with assistants</li>
      <li>Web search integration</li>
      <li>Image and document attachments</li>
      <li>Beautiful themes including Catppuccin and Tokyo Night</li>
    </ul>
  </description>
  
  <launchable type="desktop-id">com.nanogpt.NanoChat.desktop</launchable>
  
  <screenshots>
    <screenshot type="default">
      <caption>Main chat interface</caption>
      <image>https://example.com/screenshots/chat.png</image>
    </screenshot>
    <screenshot>
      <caption>Dark theme with Catppuccin</caption>
      <image>https://example.com/screenshots/dark.png</image>
    </screenshot>
  </screenshots>
  
  <url type="homepage">https://github.com/user/nanochat-desktop-v2</url>
  <url type="bugtracker">https://github.com/user/nanochat-desktop-v2/issues</url>
  
  <developer_name>Your Name</developer_name>
  
  <releases>
    <release version="1.0.0" date="2025-XX-XX">
      <description>
        <p>First stable release!</p>
      </description>
    </release>
  </releases>
  
  <content_rating type="oars-1.1">
    <content_attribute id="social-chat">intense</content_attribute>
  </content_rating>
  
  <requires>
    <display_length compare="ge">360</display_length>
  </requires>
  
  <recommends>
    <control>keyboard</control>
    <control>pointing</control>
  </recommends>
</component>
```

**Screenshots to create:**
1. Main chat interface (light theme)
2. Main chat interface (dark theme)
3. Settings dialog
4. Assistants management

**Acceptance Criteria:**
- [ ] Metainfo validates with appstream-util
- [ ] Screenshots are high quality
- [ ] All required fields present
- [ ] Content rating appropriate

---

### Task 5.10: Documentation

**Goal**: Complete user and developer documentation

**Files to create:**
```
docs/
├── README.md           # Project overview
├── INSTALL.md          # Installation instructions
├── USAGE.md            # User guide
├── CONTRIBUTING.md     # Contributor guide
└── CHANGELOG.md        # Version history
```

**README.md sections:**
- Project description
- Screenshots
- Features
- Installation (Flatpak, AppImage, from source)
- Configuration
- Contributing
- License

**INSTALL.md sections:**
- System requirements
- Flatpak installation
- AppImage installation
- Building from source
- Dependencies

**USAGE.md sections:**
- First-time setup
- Starting a conversation
- Using assistants
- Using projects
- Keyboard shortcuts
- Customizing themes

**Acceptance Criteria:**
- [ ] README comprehensive
- [ ] Install instructions work
- [ ] Usage guide covers all features
- [ ] Changelog up to date

---

## Definition of Done - Phase 5 / v1.0.0

- [ ] All tasks completed
- [ ] All themes work correctly
- [ ] Accessibility audit passed
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Flatpak passes validation
- [ ] AppImage works
- [ ] Final testing on multiple distros:
  - [ ] Ubuntu 22.04+
  - [ ] Fedora 38+
  - [ ] Arch Linux
- [ ] Code reviewed
- [ ] Branch merged and tagged as `v1.0.0`
- [ ] Release created with binaries

---

## Release Checklist - v1.0.0

```bash
# Final version updates
# Set version to 1.0.0 in pyproject.toml and __init__.py

# Final testing
./run_all_tests.sh

# Build final packages
flatpak-builder --user --install build flatpak/com.nanogpt.NanoChat.yml
flatpak build-bundle ~/.local/share/flatpak/repo \
    nanochat-v1.0.0.flatpak com.nanogpt.NanoChat

python -m python_appimage build app -p 3.11 .
mv NanoChat-*.AppImage nanochat-v1.0.0-x86_64.AppImage

# Tag and release
git checkout v0.5.0
git tag -a v1.0.0 -m "Release v1.0.0 - First Stable Release"
git push origin v0.5.0 --tags

# Merge to main
git checkout main
git merge v0.5.0
git push origin main

# Create GitHub release
# Title: "v1.0.0 - First Stable Release"
# Upload:
#   - nanochat-v1.0.0.flatpak
#   - nanochat-v1.0.0-x86_64.AppImage
# Include:
#   - Full changelog
#   - Screenshots
#   - Installation instructions
```

---

## Post-Release

After v1.0.0:

1. **Submit to Flathub** (optional)
2. **Announce release** on relevant channels
3. **Monitor issues** for bug reports
4. **Plan v1.1.0** based on feedback

---

## Notes for LLM

When implementing Phase 5:

1. **Themes** - Test on both light and dark system themes
2. **Accessibility** - Use screen reader (Orca) to verify
3. **Performance** - Profile with GTK Inspector
4. **Documentation** - Keep it current as features change
5. **Screenshots** - High quality, representative of actual usage
6. **Metainfo** - Validate before release
