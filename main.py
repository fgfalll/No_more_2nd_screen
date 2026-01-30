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

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, QObject, Signal

from core.monitor_info import get_monitor_count, has_projectors
from core.whitelist import get_whitelist
from core.window_monitor import get_window_monitor
from ui.tray_icon import TrayIconManager
from ui.settings_dialog import SettingsDialog


class Application(QObject):
    """Main application controller."""

    def __init__(self, app):
        """
        Initialize the application.

        Args:
            app: QApplication instance
        """
        super().__init__()

        self.app = app
        self.config = {}
        self.check_interval = 500  # ms

        # Initialize components
        self.load_config()
        self.whitelist = get_whitelist()
        self.window_monitor = None
        self.tray_manager = TrayIconManager(self)

        # Set up monitoring timer
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.check_and_enforce)

        # Connect signals
        self.tray_manager.toggle_protection.connect(self.toggle_protection)
        self.tray_manager.show_settings.connect(self.show_settings)
        self.tray_manager.exit_app.connect(self.exit_application)

        # Initialize
        self.initialize_monitoring()
        self.initialize_tray()

    def load_config(self):
        """Load configuration from config.json."""
        config_path = Path(__file__).parent / "config.json"

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()
            self.save_config()

        self.check_interval = self.config.get('check_interval_ms', 500)

    def _get_default_config(self):
        """Get default configuration."""
        return {
            'autostart': False,
            'protection_enabled': True,
            'check_interval_ms': 500,
            'protected_monitors': [2, 3],
            'whitelist': [
                'POWERPNT.EXE',
                'OBS64.EXE',
                'OBS32.EXE'
            ],
            'custom_whitelist': []
        }

    def save_config(self):
        """Save configuration to config.json."""
        config_path = Path(__file__).parent / "config.json"

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def initialize_monitoring(self):
        """Initialize the window monitor."""
        protected_monitors = self.config.get('protected_monitors', [2, 3])

        self.window_monitor = get_window_monitor(protected_monitors)
        self.window_monitor.set_enabled(self.config.get('protection_enabled', True))

        # Set callback for moved windows
        self.window_monitor.on_window_moved = self.on_window_moved

        # Start monitoring timer
        self.monitor_timer.start(self.check_interval)

    def initialize_tray(self):
        """Initialize the system tray icon."""
        success = self.tray_manager.create_tray_icon()

        if not success:
            print("Warning: System tray is not available on this system.")
            print("The application will continue running but without tray icon.")

        # Set initial icon state
        protection_enabled = self.config.get('protection_enabled', True)
        self.tray_manager.update_icon(protection_enabled)

        # Show startup message
        monitor_count = get_monitor_count()
        if has_projectors():
            message = f"Protecting {len(self.window_monitor.protected_monitor_indices)} projector monitor(s)"
        else:
            message = "No projector monitors detected"

        if success:
            self.tray_manager.show_message(
                "No More 2nd Screen",
                f"Running - {message}"
            )

    def check_and_enforce(self):
        """Check windows and enforce projector restrictions."""
        if self.window_monitor:
            moved = self.window_monitor.check_and_enforce()
            # Could log moved windows here if needed

    def on_window_moved(self, hwnd, process_name, title):
        """
        Called when a window is moved back to primary monitor.

        Args:
            hwnd: Window handle
            process_name: Process name
            title: Window title
        """
        # Could show notification here if desired
        pass

    def toggle_protection(self):
        """Toggle protection on/off."""
        if self.window_monitor:
            current = self.window_monitor.is_enabled()
            new_state = not current
            self.window_monitor.set_enabled(new_state)

            # Update config
            self.config['protection_enabled'] = new_state
            self.save_config()

            # Show notification
            status = "enabled" if new_state else "disabled"
            if self.tray_manager:
                self.tray_manager.show_message(
                    "Protection Toggled",
                    f"Protection has been {status}"
                )

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self.config, self.whitelist)

        # Connect settings changed signal
        dialog.settings_changed.connect(self.on_settings_changed)

        dialog.exec()

    def on_settings_changed(self):
        """Handle settings changes."""
        # Reload monitoring configuration
        if self.window_monitor:
            protected_monitors = self.config.get('protected_monitors', [2, 3])
            self.window_monitor.set_protected_monitors(protected_monitors)
            self.window_monitor.set_enabled(self.config.get('protection_enabled', True))

            # Update timer interval
            new_interval = self.config.get('check_interval_ms', 500)
            if new_interval != self.check_interval:
                self.check_interval = new_interval
                self.monitor_timer.setInterval(self.check_interval)

        # Update tray icon
        if self.tray_manager:
            protection_enabled = self.config.get('protection_enabled', True)
            self.tray_manager.update_icon(protection_enabled)

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
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)

    # Don't show main window (system tray only)
    app.setQuitOnLastWindowClosed(False)

    # Create application controller
    controller = Application(app)

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
