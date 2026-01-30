"""
Settings dialog module.

This module provides the settings UI for managing the whitelist,
enabling/disabling protection, and autostart settings.
"""

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QMessageBox, QDialogButtonBox, QWidget,
    QGroupBox, QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import win32gui
import win32con
import win32process
import psutil


class SettingsDialog(QDialog):
    """Settings dialog for the application."""

    # Signal emitted when settings are changed
    settings_changed = Signal()

    def __init__(self, config, whitelist, parent=None):
        """
        Initialize the settings dialog.

        Args:
            config: Configuration dictionary
            whitelist: Whitelist instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config = config
        self.whitelist = whitelist

        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)

        # General Settings Group
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()

        self.chk_enable_protection = QCheckBox("Enable protection on startup")
        self.chk_autostart = QCheckBox("Start with Windows")

        # Check interval setting
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Check interval (ms):")
        self.spin_interval = QSpinBox()
        self.spin_interval.setMinimum(100)
        self.spin_interval.setMaximum(5000)
        self.spin_interval.setSingleStep(100)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.spin_interval)
        interval_layout.addStretch()

        general_layout.addWidget(self.chk_enable_protection)
        general_layout.addWidget(self.chk_autostart)
        general_layout.addLayout(interval_layout)
        general_group.setLayout(general_layout)

        # Protected Monitors Group
        monitors_group = QGroupBox("Protected Monitor Indices")
        monitors_layout = QHBoxLayout()
        monitors_label = QLabel("Monitor indices to protect:")
        self.spin_monitors = QSpinBox()
        self.spin_monitors.setMinimum(2)
        self.spin_monitors.setMaximum(9)
        self.spin_monitors.setValue(3)
        monitors_info = QLabel("(e.g., 3 = protect monitors 2 & 3)")
        monitors_layout.addWidget(monitors_label)
        monitors_layout.addWidget(self.spin_monitors)
        monitors_layout.addWidget(monitors_info)
        monitors_layout.addStretch()
        monitors_group.setLayout(monitors_layout)

        # Whitelist Group
        whitelist_group = QGroupBox("Whitelisted Applications")
        whitelist_layout = QVBoxLayout()

        # Info label
        info_label = QLabel("These applications are allowed on projector monitors:")
        info_label.setFont(QFont("", 9))
        whitelist_layout.addWidget(info_label)

        # Whitelist list
        self.list_whitelist = QListWidget()
        self.list_whitelist.setMinimumHeight(150)
        whitelist_layout.addWidget(self.list_whitelist)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.btn_add_process = QPushButton("Add Process...")
        self.btn_add_executable = QPushButton("Add by Name...")
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setEnabled(False)

        buttons_layout.addWidget(self.btn_add_process)
        buttons_layout.addWidget(self.btn_add_executable)
        buttons_layout.addWidget(self.btn_remove)
        buttons_layout.addStretch()

        whitelist_layout.addLayout(buttons_layout)
        whitelist_group.setLayout(whitelist_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        self.button_box.accepted.connect(self.ok_clicked)
        self.button_box.rejected.connect(self.reject)

        # Add all to main layout
        layout.addWidget(general_group)
        layout.addWidget(monitors_group)
        layout.addWidget(whitelist_group)
        layout.addStretch()
        layout.addWidget(self.button_box)

        # Connect signals
        self.list_whitelist.itemSelectionChanged.connect(self.on_selection_changed)
        self.btn_add_process.clicked.connect(self.add_process_by_window)
        self.btn_add_executable.clicked.connect(self.add_process_by_name)
        self.btn_remove.clicked.connect(self.remove_process)

    def load_settings(self):
        """Load settings from config."""
        self.chk_enable_protection.setChecked(self.config.get('protection_enabled', True))
        self.chk_autostart.setChecked(self.config.get('autostart', False))
        self.spin_interval.setValue(self.config.get('check_interval_ms', 500))

        # Load protected monitors
        protected = self.config.get('protected_monitors', [2, 3])
        if protected:
            self.spin_monitors.setValue(max(protected))

        # Load whitelist
        self.refresh_whitelist_list()

    def refresh_whitelist_list(self):
        """Refresh the whitelist display."""
        self.list_whitelist.clear()

        all_whitelisted = self.whitelist.get_all()

        for process_name in all_whitelisted:
            item = QListWidgetItem(process_name)

            # Mark default entries
            if self.whitelist.is_default(process_name):
                item.setForeground(Qt.darkGray)
                item.setText(f"{process_name} (default)")

            self.list_whitelist.addItem(item)

    def on_selection_changed(self):
        """Handle selection change in whitelist."""
        has_selection = len(self.list_whitelist.selectedItems()) > 0
        self.btn_remove.setEnabled(has_selection)

        # Don't allow removing default entries
        if has_selection:
            item = self.list_whitelist.selectedItems()[0]
            text = item.text()
            if text.endswith("(default)"):
                self.btn_remove.setEnabled(False)

    def add_process_by_window(self):
        """Add a process by selecting from running windows."""
        dialog = WindowPickerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            process_name = dialog.get_selected_process()
            if process_name:
                self.whitelist.add(process_name, custom=True)
                self.refresh_whitelist_list()

    def add_process_by_name(self):
        """Add a process by entering the executable name."""
        from PySide6.QtWidgets import QInputDialog

        process_name, ok = QInputDialog.getText(
            self,
            "Add Process by Name",
            "Enter the executable name (e.g., NOTEPAD.EXE):"
        )

        if ok and process_name:
            self.whitelist.add(process_name, custom=True)
            self.refresh_whitelist_list()

    def remove_process(self):
        """Remove selected process from whitelist."""
        current_item = self.list_whitelist.currentItem()
        if current_item:
            text = current_item.text()

            # Extract process name (remove "(default)" suffix if present)
            if " (default)" in text:
                process_name = text.replace(" (default)", "")
            else:
                process_name = text

            # Don't remove default entries
            if self.whitelist.is_default(process_name):
                QMessageBox.warning(
                    self,
                    "Cannot Remove",
                    "Cannot remove default whitelisted applications."
                )
                return

            self.whitelist.remove(process_name)
            self.refresh_whitelist_list()

    def apply_settings(self):
        """Apply the current settings."""
        # Update config
        self.config['protection_enabled'] = self.chk_enable_protection.isChecked()
        self.config['check_interval_ms'] = self.spin_interval.value()

        # Update protected monitors
        max_monitor = self.spin_monitors.value()
        self.config['protected_monitors'] = list(range(2, max_monitor + 1))

        # Update autostart
        self.set_autostart(self.chk_autostart.isChecked())

        # Save config
        self.save_config()

        # Emit signal
        self.settings_changed.emit()

        QMessageBox.information(self, "Settings", "Settings applied successfully.")

    def ok_clicked(self):
        """Handle OK button click."""
        self.apply_settings()
        self.accept()

    def set_autostart(self, enabled):
        """
        Enable or disable application autostart.

        Args:
            enabled: True to enable autostart, False to disable
        """
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_SET_VALUE
            )

            if enabled:
                # Get the path to the executable
                app_path = sys.executable
                # If running as python script, use the python interpreter
                if app_path.endswith("python.exe"):
                    # Try to get the main script path
                    import os
                    script_path = os.path.abspath("main.py")
                    app_path = f'"{app_path}" "{script_path}"'

                winreg.SetValueEx(
                    key,
                    "NoMore2ndScreen",
                    0,
                    winreg.REG_SZ,
                    app_path
                )
            else:
                try:
                    winreg.DeleteValue(key, "NoMore2ndScreen")
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
            self.config['autostart'] = enabled

        except Exception as e:
            QMessageBox.warning(
                self,
                "Autostart Error",
                f"Could not set autostart: {e}"
            )

    def save_config(self):
        """Save configuration to file."""
        import json
        from pathlib import Path

        script_dir = Path(__file__).parent.parent
        config_path = script_dir / "config.json"

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Could not save configuration: {e}"
            )


class WindowPickerDialog(QDialog):
    """Dialog for picking a running window/application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Running Application")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self.selected_process = None

        self.setup_ui()

    def setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)

        label = QLabel("Select a running application to add to the whitelist:")
        layout.addWidget(label)

        self.list_windows = QListWidget()
        layout.addWidget(self.list_windows)

        # Refresh button
        refresh_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        refresh_layout.addStretch()
        refresh_layout.addWidget(self.btn_refresh)
        layout.addLayout(refresh_layout)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect signals
        self.btn_refresh.clicked.connect(self.refresh_windows)
        self.list_windows.itemDoubleClicked.connect(lambda: self.accept())

        # Load initial windows
        self.refresh_windows()

    def refresh_windows(self):
        """Refresh the list of running windows."""
        self.list_windows.clear()

        windows = self.get_running_windows()

        for title, process_name in windows:
            display_text = f"{title} ({process_name})"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, process_name)
            self.list_windows.addItem(item)

    def get_running_windows(self):
        """Get a list of visible windows with their process names."""
        windows = []

        def enum_callback(hwnd, _):
            # Only visible windows
            if not win32gui.IsWindowVisible(hwnd):
                return True

            # Get window title
            try:
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True

                # Get process name
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid:
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name().upper()

                        # Skip system processes
                        if process_name in ['SYSTEM', 'IDLE PROCESS']:
                            return True

                        windows.append((title, process_name))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            except Exception:
                pass

            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            pass

        # Sort by title and remove duplicates
        seen = set()
        unique_windows = []
        for title, process_name in sorted(windows, key=lambda x: x[0]):
            key = (title, process_name)
            if key not in seen:
                seen.add(key)
                unique_windows.append((title, process_name))

        return unique_windows

    def get_selected_process(self):
        """Get the selected process name."""
        current_item = self.list_windows.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
