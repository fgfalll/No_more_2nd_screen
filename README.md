# No More 2nd Screen

A Windows application that restricts projector monitor usage to only whitelisted applications.

## Features

- **Automatic Window Management**: Automatically moves non-whitelisted applications from projector monitors back to the primary monitor
- **Whitelist System**: Pre-configured whitelist for PowerPoint and OBS Studio, with ability to add custom applications
- **System Tray Operation**: Runs silently in the system tray with easy access to settings
- **Multi-Monitor Support**: Works with multiple projector monitors (monitors 2 & 3 by default)
- **Customizable Protection**: Configure which monitors to protect and adjust check intervals

## Installation

1. Install Python 3.10 or higher
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```
python main.py
```

The application will start in the system tray. You can:
- **Double-click** the tray icon to open settings
- **Right-click** to access the context menu with options to enable/disable protection
- Use the **Settings** dialog to manage your whitelist

## Whitelisted Applications (Default)

- PowerPoint (POWERPNT.EXE)
- OBS Studio (OBS64.EXE, OBS32.EXE)

## Configuration

The application stores its configuration in `config.json`:

```json
{
    "autostart": false,
    "protection_enabled": true,
    "check_interval_ms": 500,
    "protected_monitors": [2, 3],
    "whitelist": [
        "POWERPNT.EXE",
        "OBS64.EXE",
        "OBS32.EXE"
    ],
    "custom_whitelist": []
}
```

## Requirements

- Windows 10/11
- Python 3.10+
- PySide6
- pywin32
- psutil

## License

MIT License
