"""
No More 2nd Screen - Application Entry Point

A Windows application that restricts projector monitor usage to only
whitelisted applications (PowerPoint, OBS Studio, and user-configurable apps).

Projector monitors (2 & 3) are protected - only whitelisted apps can be
displayed on them. All other windows are automatically moved back to the
primary monitor (1).
"""

import sys
import json
from pathlib import Path
from typing import List

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, QObject, Signal

from core.monitor_info import (
    get_monitor_count,
    has_projectors,
    get_monitors,
    get_monitor_groups,
    set_primary_monitor,
)
from core.whitelist import get_whitelist
from core.window_monitor import get_window_monitor
from ui.tray_icon import TrayIconManager
from ui.settings_dialog import SettingsDialog


class Application(QObject):
    """Main application controller."""

    def __init__(self, app):
        """Initialize the application."""
        super().__init__()

        self.app = app
        self.config = {}
        self.check_interval = 500

        self.load_config()

        self.whitelist = get_whitelist()

        self.window_monitor = None
        self.tray_manager = TrayIconManager(self)

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.check_and_enforce)

        self.tray_manager.toggle_protection.connect(self.toggle_protection)
        self.tray_manager.show_settings.connect(self.show_settings)
        self.tray_manager.exit_app.connect(self.exit_application)

        self.initialize_monitoring()

        self.initialize_tray()

    def load_config(self):
        """Load configuration from config.json."""
        config_path = Path(__file__).parent / "config.json"

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()
            self.save_config()

        self.check_interval = self.config.get("check_interval_ms", 500)

        self._migrate_config_if_needed()

    def _migrate_config_if_needed(self):
        """Migrate config from numeric indices to device names if needed."""
        protected = self.config.get("protected_monitors", [])

        if isinstance(protected, list) and protected:
            if isinstance(protected[0], int):
                monitors = get_monitors()
                device_names = []
                for idx in protected:
                    if 0 < idx <= len(monitors):
                        device_names.append(monitors[idx - 1].device_name)

                if device_names:
                    self.config["protected_monitors"] = device_names
                    self.save_config()

    def _get_default_config(self):
        """Get default configuration."""
        return {
            "autostart": False,
            "protection_enabled": True,
            "check_interval_ms": 500,
            "protected_monitors": [2, 3],
            "whitelist": ["OBS64.EXE", "OBS32.EXE"],
            "custom_whitelist": [],
        }

    def save_config(self):
        """Save configuration to config.json."""
        config_path = Path(__file__).parent / "config.json"

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            pass

    def initialize_monitoring(self):
        """Initialize the window monitor."""
        protected_devices = self.config.get("protected_monitors", ["\\\\.\\DISPLAY2", "\\\\.\\DISPLAY3"])
        primary_device = self.config.get("primary_monitor", None)

        self.window_monitor = get_window_monitor(protected_devices)
        if primary_device:
            self.window_monitor.set_primary_device(primary_device)

        self.window_monitor.set_enabled(self.config.get("protection_enabled", True))

        self.window_monitor.on_window_moved = self.on_window_moved

        self.monitor_timer.start(self.check_interval)

    def initialize_tray(self):
        """Initialize the system tray icon."""
        success = self.tray_manager.create_tray_icon()

        if not success:
            pass

        protection_enabled = self.config.get("protection_enabled", True)
        self.tray_manager.update_icon(protection_enabled)

        monitor_count = get_monitor_count()
        if has_projectors():
            protected_devices = self.config.get("protected_monitors", [])
            message = f"Protecting {len(protected_devices)} monitor(s)"
        else:
            message = "No projector monitors detected"

        if success:
            self.tray_manager.show_message("No More 2nd Screen", f"Running - {message}")

    def show_settings(self):
        """Show the settings dialog."""
        try:
            dialog = SettingsDialog(self.config, self.whitelist)

            dialog.settings_changed.connect(self.on_settings_changed)

            dialog.exec()
        except Exception as e:
            pass
            import traceback

            traceback.print_exc()

    def check_and_enforce(self):
        """Check windows and enforce projector restrictions."""
        if self.window_monitor:
            moved = self.window_monitor.check_and_enforce()

    def on_window_moved(self, hwnd, process_name, title):
        """Called when a window is moved back to primary monitor."""
        pass

    def on_settings_changed(self):
        """Handle settings changes."""
        if self.window_monitor:
            protected_devices = self.config.get("protected_monitors", [])

            primary_device = self.config.get("primary_monitor", None)

            self.window_monitor.set_protected_devices(protected_devices)
            if primary_device:
                self.window_monitor.set_primary_device(primary_device)

            self.window_monitor.set_enabled(self.config.get("protection_enabled", True))

            new_interval = self.config.get("check_interval_ms", 500)
            if new_interval != self.check_interval:
                self.check_interval = new_interval
                self.monitor_timer.setInterval(self.check_interval)

        if self.tray_manager:
            protection_enabled = self.config.get("protection_enabled", True)
            self.tray_manager.update_icon(protection_enabled)

    def toggle_protection(self):
        """Toggle protection on/off."""
        if self.window_monitor:
            current = self.window_monitor.is_enabled()
            new_state = not current
            self.window_monitor.set_enabled(new_state)
            self.config["protection_enabled"] = new_state
            self.save_config()
            status = "enabled" if new_state else "disabled"
            if self.tray_manager:
                self.tray_manager.show_message(
                    "Protection Toggled", f"Protection has been {status}"
                )

    def exit_application(self):
        """Exit the application."""
        # Stop timer
        self.monitor_timer.stop()

        # Hide tray icon
        if self.tray_manager:
            self.tray_manager.hide()

        # Quit application
        self.app.quit()


def main():
    """Main entry point."""
    import sys

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(False)

    try:
        controller = Application(app)
    except Exception as e:
        import traceback

        traceback.print_exc()
        sys.exit(1)

    try:
        sys.exit(app.exec())
    except Exception as e:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
