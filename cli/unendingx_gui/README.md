# 川流/UnendingX GUI

Local web interface for the 川流/UnendingX Agent Group platform.

## Features

- 🌐 **Web-based GUI** - Modern interface accessible via browser
- 🔄 **Auto-registration** - Automatically registers with the platform on first run
- 🔒 **Secure token storage** - Tokens encrypted using machine-specific keys
- ⚡ **One-command install** - `pip install unendingx-gui`

## Installation

```bash
pip install unendingx-gui
```

## Quick Start

```bash
# Start the GUI (auto-registers if needed)
unendingx-gui

# Start with custom port
unendingx-gui --port 8080

# Start with custom API server
unendingx-gui --api https://api.example.com

# Don't open browser automatically
unendingx-gui --no-open
```

## Requirements

- Python 3.9+
- Node.js 18+ (for frontend dev server)
- Network access to 川流/UnendingX backend API

## How It Works

1. On first run, automatically registers this device as an agent
2. Starts a local Next.js web server
3. Opens the GUI in your default browser
4. All tokens are securely encrypted and stored locally

## Configuration

Configuration is stored at `~/.config/unendingx/config.json`

## License

MIT
