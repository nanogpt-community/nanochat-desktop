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
- **Cross-Distro:** Packaging support for Flatpak and AppImage.

## Installation

### Prerequisites

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

### Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/nanochat-desktop-v2.git
    cd nanochat-desktop-v2
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -e .[dev]
    ```

4.  **Run the application:**
    ```bash
    python -m nanochat
    ```

## Packaging

### Flatpak
Manifest available in `flatpak/com.nanogpt.NanoChat.yml`.

### AppImage
Configuration available in `appimage/AppImageBuilder.yml`.

## License

MIT