# No More 2nd Screen

A Windows application that restricts projector monitor usage to only whitelisted applications.

## Features

- **Automatic Window Management**: Automatically moves non-whitelisted applications from projector monitors back to the primary monitor
- **Smart PowerPoint Detection**: PowerPoint is only allowed on projectors during slideshow/presentation mode
- **Whitelist Management**: Add/remove applications from the whitelist with a user-friendly interface
- **Monitor Selection**: Choose which monitors to protect (works with extended desktop mode)
- **System Tray Application**: Runs silently in the background with easy access to settings
- **Auto-Start Option**: Optionally start with Windows

## How It Works

The application monitors all open windows and checks if they are on protected (projector) monitors. When a non-whitelisted application window is detected on a protected monitor, it is automatically moved back to the primary monitor.

**Special Behavior:**
- **PowerPoint** - Only allowed on protected monitors when in slideshow/presentation mode. Regular PowerPoint windows are moved to the primary monitor.
- **OBS Studio** - Whitelisted by default for streaming/recording scenarios
- **Other applications** - Must be manually added to the whitelist

## Installation

### Option 1: Run from Source

1. Install Python 3.10 or higher
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```

### Option 2: Build Executable

1. Install Python 3.10 or higher
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Build the executable:
   - **Windows**: Run `build.bat`
   - **Manual**: Run `python build_exe.py`

This will create a standalone executable in the `dist` folder that can be run without Python installed.

## Usage

Run the application:
```
python main.py
```

The application will start in the system tray. You can:
- **Double-click** the tray icon to open settings
- **Right-click** to access the context menu with options to enable/disable protection
- Use the **Settings** dialog to manage your whitelist and configure protected monitors

## Settings Dialog

The Settings dialog allows you to:

- **Enable/disable protection** on startup
- **Set autostart** to run with Windows
- **Adjust check interval** (how often to check windows, in milliseconds)
- **Select monitors to protect** from the list of detected displays
- **Manage whitelist**:
  - Add processes by selecting from running applications
  - Add processes by entering executable name manually
  - Remove any whitelisted application
- **Set primary monitor** (change main display)

## Default Whitelisted Applications

- OBS Studio (OBS64.EXE, OBS32.EXE)

Note: PowerPoint is NOT in the default whitelist because it has special handling - it's only allowed on protected monitors during slideshow presentations.

## Requirements

- Windows 10/11
- Python 3.10+
- PySide6
- pywin32
- psutil

## License

**Source-available for personal and non-commercial use only.**

This software is source-available and free for personal, non-commercial use. Commercial use requires explicit permission from the author.

**Important:** This license is NOT "open source" according to the Open Source Definition because it restricts commercial use. It is a "source-available" license that allows you to view and modify the source code for personal/non-commercial purposes.

## Configuration

The application stores its configuration in `config.json`:

```json
{
    "autostart": false,
    "protection_enabled": true,
    "check_interval_ms": 500,
    "protected_monitors": [],
    "whitelist": ["OBS64.EXE", "OBS32.EXE"],
    "custom_whitelist": []
}
```

## Projector Monitor Detection

The application works best when your displays are configured in **Extend** mode in Windows display settings.

- **Extend mode**: Each monitor is treated as a separate display - you can select which ones to protect
- **Duplicate/Clone mode**: Windows treats cloned displays as a single logical display - the application will see all monitors sharing the same coordinates

For proper multi-monitor protection, use **Extend** mode in Windows Display Settings.

## Troubleshooting

**Q: Application doesn't detect my second monitor**
- Make sure your monitors are in "Extend" mode, not "Duplicate" mode
- Click the "Refresh" button in the Settings dialog

**Q: PowerPoint keeps getting moved**
- Normal: PowerPoint is only allowed during slideshow. Start your presentation (F5) and it will be allowed on the projector.

**Q: How do I allow an application on the projector?**
- Open Settings → Whitelist section → Click "Add Process" or "Add by Name"
- Find the application and add it to the whitelist

## Version

1.5
