# NanoChat Desktop

A modern, native Linux desktop client for the NanoChat API, built with Python, GTK4, and Libadwaita.

![Status](https://img.shields.io/badge/Status-Beta-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)

## Features

- **Native UI:** Clean, modern interface designed for GNOME (Libadwaita).
- **Persistent Chat:** Local caching (SQLite) allows you to view conversations offline.
- **Model Selection:** Choose from available AI models; your selection is remembered.
- **Secure:** API keys are stored safely in your system's keyring (Libsecret).
- **History:** Manage your conversation history (view, delete).
- **Cross-Distro:** Available as Flatpak for all Linux distributions.

## Installation

### Flatpak (Recommended)

The recommended way to install NanoChat Desktop is via Flatpak:

```bash
# Install from Flathub (once available)
flatpak install flathub com.nanogpt.NanoChat

# Or install from a downloaded .flatpak file
flatpak install com.nanogpt.NanoChat-<version>.flatpak

# Run the application
flatpak run com.nanogpt.NanoChat
```

### Development Setup

If you want to contribute or run from source:

**Prerequisites:**
- Python 3.11 or higher
- GTK4 and Libadwaita development headers
- Libsecret development headers

**Fedora:**
```bash
sudo dnf install python3-devel gtk4-devel libadwaita-devel libsecret-devel
```

**Ubuntu/Debian:**
```bash
sudo apt install python3-dev libgtk-4-dev libadwaita-1-dev libsecret-1-dev
```

**From Source:**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nanogpt-community/nanochat-desktop.git
   cd nanochat-desktop
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

4. **Run the application:**
   ```bash
   nanochat
   ```

## Roadmap

See the [`plans/`](plans/) folder for detailed development plans and upcoming features:

**Phase 3 - Assistants and Projects:**
- Custom AI assistants with system prompts
- Project folders for organizing conversations
- Enhanced conversation management

**Phase 4 - Advanced Features:**
- Web search integration
- File attachments
- Usage analytics

**Phase 5 - Polish:**
- Additional themes and customization
- Accessibility improvements
- Store submission preparation

---

## Packaging

### Building the Flatpak

To build the Flatpak package locally:

```bash
# Install flatpak-builder
sudo dnf install flatpak-builder  # Fedora
sudo apt install flatpak-builder  # Ubuntu/Debian

# Install the GNOME runtime and SDK (if not already installed)
flatpak install flathub org.gnome.Platform//45
flatpak install flathub org.gnome.Sdk//45

# Build the Flatpak
flatpak-builder --user --install --force-clean build flatpak/com.nanogpt.NanoChat.yml

# Export as a single file
flatpak build-export export build
flatpak build-bundle export com.nanogpt.NanoChat-<version>.flatpak com.nanogpt.NanoChat
```

The Flatpak manifest is available at [`flatpak/com.nanogpt.NanoChat.yml`](flatpak/com.nanogpt.NanoChat.yml).

## License

MIT