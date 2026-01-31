"""
Settings dialog module.

This module provides the settings UI for managing the whitelist,
enabling/disabling protection, autostart settings, and monitor configuration
with support for combined displays and primary monitor selection.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QMessageBox,
    QDialogButtonBox,
    QWidget,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QHeaderView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import sys
import win32gui
import win32con
import win32process
import psutil

from core.monitor_info import (
    get_monitors,
    get_monitor_groups,
    set_primary_monitor,
    get_primary_device_name,
    MonitorGroup,
)


class SettingsDialog(QDialog):
    """Settings dialog for the application."""

    settings_changed = Signal()

    def __init__(self, config, whitelist, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.config = config
        self.whitelist = whitelist

        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)

        # Track if settings have been modified
        self._modified = False
        self._original_config = self.config.copy()

        self.setup_ui()
        self.load_settings()
        self.refresh_whitelist_list()
        self._load_monitor_groups()

    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)

        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()

        self.chk_enable_protection = QCheckBox("Enable protection on startup")
        self.chk_autostart = QCheckBox("Start with Windows")

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

        monitors_group = QGroupBox("Protected Monitors")
        monitors_layout = QVBoxLayout()

        info_label = QLabel(
            "Select monitors to protect. Windows will be prevented from "
            "moving non-whitelisted applications to these monitors."
        )
        info_label.setFont(QFont("", 9))
        info_label.setWordWrap(True)
        monitors_layout.addWidget(info_label)

        self.tree_monitors = QTreeWidget()
        self.tree_monitors.setHeaderHidden(True)
        self.tree_monitors.setMinimumHeight(200)
        self.tree_monitors.setColumnCount(1)
        self.tree_monitors.setHeaderLabels(["Monitors"])
        self.tree_monitors.setHeaderLabels(["Monitors"])
        monitors_layout.addWidget(self.tree_monitors)

        refresh_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_set_primary = QPushButton("Set as Primary")
        self.btn_set_primary.setEnabled(False)
        refresh_layout.addStretch()
        refresh_layout.addWidget(self.btn_set_primary)
        refresh_layout.addWidget(self.btn_refresh)
        monitors_layout.addLayout(refresh_layout)

        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("", 9))
        self.lbl_status.setStyleSheet("color: gray;")
        monitors_layout.addWidget(self.lbl_status)

        monitors_group.setLayout(monitors_layout)

        whitelist_group = QGroupBox("Whitelisted Applications")
        whitelist_layout = QVBoxLayout()

        info_label = QLabel("These applications are allowed on projector monitors:")
        info_label.setFont(QFont("", 9))
        whitelist_layout.addWidget(info_label)

        self.list_whitelist = QListWidget()
        self.list_whitelist.setMinimumHeight(150)
        whitelist_layout.addWidget(self.list_whitelist)

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

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(
            self.apply_settings
        )
        self.button_box.accepted.connect(self.ok_clicked)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(general_group)
        layout.addWidget(monitors_group)
        layout.addWidget(whitelist_group)
        layout.addStretch()
        layout.addWidget(self.button_box)

        self.list_whitelist.itemSelectionChanged.connect(self.on_selection_changed)
        self.btn_add_process.clicked.connect(self.add_process_by_window)
        self.btn_add_executable.clicked.connect(self.add_process_by_name)
        self.btn_remove.clicked.connect(self.remove_process)
        self.btn_refresh.clicked.connect(self._load_monitor_groups)
        self.btn_set_primary.clicked.connect(self.set_primary_monitor)
        self.tree_monitors.itemChanged.connect(self._update_status_label)
        self.tree_monitors.itemSelectionChanged.connect(self._on_monitor_selection_changed)
        self.tree_monitors.itemChanged.connect(self._mark_modified)

        # Track modifications to UI controls
        self.chk_enable_protection.stateChanged.connect(self._mark_modified)
        self.chk_autostart.stateChanged.connect(self._mark_modified)
        self.spin_interval.valueChanged.connect(self._mark_modified)

    def _mark_modified(self):
        """Mark settings as modified."""
        self._modified = True

    def _has_changes(self) -> bool:
        """Check if settings have been modified."""
        return self._modified

    def load_settings(self):
        """Load settings from config into UI controls."""
        self.chk_enable_protection.setChecked(
            self.config.get("protection_enabled", True)
        )
        self.chk_autostart.setChecked(
            self.config.get("autostart", False)
        )
        self.spin_interval.setValue(
            self.config.get("check_interval_ms", 500)
        )

    def _load_monitor_groups(self):
        """Load monitor groups and build tree view."""
        self.tree_monitors.clear()

        self.monitor_groups = get_monitor_groups()
        self.current_primary = get_primary_device_name()

        for group in self.monitor_groups:
            group_item = QTreeWidgetItem(self.tree_monitors)
            group_item.setText(0, f"{group.icon} {group.name}")
            
            font = QFont()
            if group.is_primary:
                font.setBold(True)
                font.setPointSize(10)
                group_item.setFont(0, font)
            elif group.is_clone:
                font.setItalic(True)
                group_item.setFont(0, font)

            group_item.setData(0, Qt.UserRole, group)
            group_item.setExpanded(True)

            for device_name in group.device_names:
                device_item = QTreeWidgetItem(group_item)
                device_item.setFlags(device_item.flags() | Qt.ItemIsUserCheckable)
                device_item.setText(0, device_name.split("\\")[-1])
                
                is_protected = device_name in self._get_protected_devices()
                device_item.setCheckState(0, Qt.Checked if is_protected else Qt.Unchecked)

                if device_name == self.current_primary:
                    font = QFont()
                    font.setItalic(True)
                    device_item.setFont(0, font)

        self.tree_monitors.resizeColumnToContents(0)
        self._update_status_label()

    def _get_protected_devices(self) -> list:
        """Get list of protected device names."""
        protected = self.config.get("protected_monitors", [])
        return protected if protected else []

    def _update_status_label(self):
        """Update the status label."""
        protected = self._get_protected_devices()
        monitor_groups = self.monitor_groups
        total_monitors = sum(len(g.device_names) for g in monitor_groups if not g.is_clone)

        if not total_monitors:
            self.lbl_status.setText("No monitors to protect")
            self.lbl_status.setStyleSheet("color: orange;")
        elif len(protected) == 0:
            self.lbl_status.setText(f"{total_monitors} monitor(s) available - no protection")
            self.lbl_status.setStyleSheet("color: orange;")
        elif len(protected) >= total_monitors:
            self.lbl_status.setText(f"All {total_monitors} monitors protected")
            self.lbl_status.setStyleSheet("color: red;")
        else:
            self.lbl_status.setText(f"{len(protected)} of {total_monitors} monitors protected")
            self.lbl_status.setStyleSheet("color: green;")

    def refresh_whitelist_list(self):
        """Refresh the whitelist display."""
        self.list_whitelist.clear()

        all_whitelisted = self.whitelist.get_all()

        for process_name in all_whitelisted:
            item = QListWidgetItem(process_name)
            item.setForeground(Qt.black)
            self.list_whitelist.addItem(item)

    def on_selection_changed(self):
        """Handle selection change in whitelist."""
        has_selection = len(self.list_whitelist.selectedItems()) > 0
        self.btn_remove.setEnabled(has_selection)

    def _on_monitor_selection_changed(self):
        """Handle selection change in monitors tree."""
        selected_items = self.tree_monitors.selectedItems()
        if selected_items:
            # Only allow setting a monitor as primary if it's not already primary
            item = selected_items[0]
            group = item.data(0, Qt.UserRole)
            if isinstance(group, MonitorGroup) and not group.is_primary:
                self.btn_set_primary.setEnabled(True)
            else:
                self.btn_set_primary.setEnabled(False)
        else:
            self.btn_set_primary.setEnabled(False)

    def set_primary_monitor(self):
        """Set the selected monitor as primary."""
        selected_items = self.tree_monitors.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        group = item.data(0, Qt.UserRole)

        if not isinstance(group, MonitorGroup):
            return

        if group.is_primary:
            QMessageBox.information(self, "Info", "This monitor is already set as primary.")
            return

        # Get the device name from the group
        if not group.device_names:
            QMessageBox.warning(self, "Error", "No device name found for this monitor.")
            return

        device_name = group.device_names[0]

        reply = QMessageBox.question(
            self,
            "Set Primary Monitor",
            f"Set {group.name} as the primary monitor?\n\n"
            "This will change your Windows display settings and may move all windows to this monitor.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                success = set_primary_monitor(device_name)
                if success:
                    self.config["primary_monitor"] = device_name
                    self._load_monitor_groups()  # Refresh the display
                    QMessageBox.information(
                        self, "Success", f"{group.name} has been set as the primary monitor."
                    )
                else:
                    QMessageBox.warning(
                        self, "Error", "Failed to set primary monitor. You may need administrator privileges."
                    )
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to set primary monitor: {e}")

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
        process_name, ok = QInputDialog.getText(
            self,
            "Add Process by Name",
            "Enter the executable name (e.g., NOTEPAD.EXE):",
        )

        if ok and process_name:
            self.whitelist.add(process_name, custom=True)
            self.refresh_whitelist_list()

    def remove_process(self):
        """Remove selected process from whitelist."""
        current_item = self.list_whitelist.currentItem()
        if current_item:
            text = current_item.text()

            if "(default)" in text:
                process_name = text.replace(" (default)", "")
            else:
                process_name = text

            if self.whitelist.is_default(process_name):
                QMessageBox.warning(
                    self,
                    "Cannot Remove",
                    "Cannot remove default whitelisted applications.",
                )
                return

            self.whitelist.remove(process_name)
            self.refresh_whitelist_list()

    def apply_settings(self):
        """Apply the current settings."""
        self.config["protection_enabled"] = self.chk_enable_protection.isChecked()
        self.config["check_interval_ms"] = self.spin_interval.value()

        protected_devices = self._get_selected_protected_devices()

        if protected_devices:
            self.config["protected_monitors"] = protected_devices
        else:
            self.config["protected_monitors"] = []

        self.set_autostart(self.chk_autostart.isChecked())

        self.save_config()

        self.settings_changed.emit()

        # Reset modified flag after applying
        self._modified = False

    def _get_selected_protected_devices(self) -> list:
        """Get the list of selected protected device names."""
        protected = []

        iterator = QTreeWidgetItemIterator(self.tree_monitors)
        while iterator.value():
            item = iterator.value()
            # Only process child items (devices), not group items
            if item.parent() is not None:
                if item.checkState(0) == Qt.Checked:
                    # Get the device name from the parent group's data
                    parent = item.parent()
                    group = parent.data(0, Qt.UserRole)
                    if isinstance(group, MonitorGroup):
                        # Get the device name from the item text (e.g., "DISPLAY1")
                        device_short_name = item.text(0)
                        # Convert short name to full device name
                        for device_name in group.device_names:
                            if device_name.endswith(device_short_name) or device_short_name in device_name:
                                protected.append(device_name)
                                break

            iterator += 1

        return protected

    def ok_clicked(self):
        """Handle OK button click."""
        if self._has_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to apply them before closing?",
                QMessageBox.Apply | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Apply,
            )

            if reply == QMessageBox.Apply:
                self.apply_settings()
                self.accept()
            elif reply == QMessageBox.Discard:
                # Discard changes and close
                self.accept()
            else:  # Cancel
                return
        else:
            self.accept()

    def set_autostart(self, enabled):
        """
        Enable or disable application autostart.

        Args:
            enabled: True to enable, False to disable
        """
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )

            if enabled:
                app_path = sys.executable
                if app_path.endswith("python.exe"):
                    import os
                    script_path = os.path.abspath("main.py")
                    app_path = f'"{app_path}" "{script_path}"'

                winreg.SetValueEx(key, "NoMore2ndScreen", 0, winreg.REG_SZ, app_path)
                self.config["autostart"] = True
            else:
                try:
                    winreg.DeleteValue(key, "NoMore2ndScreen")
                except FileNotFoundError:
                    pass

                self.config["autostart"] = False

            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(self, "Autostart Error", f"Could not set autostart: {e}")

    def save_config(self):
        """Save configuration to file."""
        import json
        from pathlib import Path

        script_dir = Path(__file__).parent
        config_path = script_dir / "config.json"

        try:
            existing_config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)

            existing_config["autostart"] = self.config.get("autostart", False)
            existing_config["protection_enabled"] = self.config.get(
                "protection_enabled", True
            )
            existing_config["check_interval_ms"] = self.config.get(
                "check_interval_ms", 500
            )

            protected_devices = self._get_selected_protected_devices()
            existing_config["protected_monitors"] = protected_devices if protected_devices else []

            primary_monitor = self.config.get("primary_monitor", "")
            if primary_monitor:
                existing_config["primary_monitor"] = primary_monitor

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing_config, f, indent=4)

        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save configuration: {e}")


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
        self.list_windows.setMinimumHeight(200)
        layout.addWidget(self.list_windows)

        refresh_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        refresh_layout.addStretch()
        refresh_layout.addWidget(self.btn_refresh)
        layout.addLayout(refresh_layout)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

        self.list_windows.itemDoubleClicked.connect(lambda: self.accept())

        self.btn_refresh.clicked.connect(self.refresh_windows)

    def refresh_windows(self):
        """Refresh the list of running windows."""
        self.list_windows.clear()

        windows = self.get_running_windows()

        for title, process_name in windows:
            item = QListWidgetItem(f"{title} ({process_name})")
            item.setData(Qt.UserRole, process_name)
            self.list_windows.addItem(item)

    def get_running_windows(self):
        """Get a list of visible windows with their process names."""
        windows = []

        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True

            try:
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True

                # Skip certain system window classes
                try:
                    class_name = win32gui.GetClassName(hwnd)
                    if class_name in ["Shell_TrayWnd", "Progman", "WorkerW", "DV2Host"]:
                        return True
                except Exception:
                    pass

                process_name = "Unknown"
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid:
                        try:
                            process = psutil.Process(pid)
                            process_name = process.name().upper()

                            # Skip system processes
                            if process_name in ["SYSTEM", "IDLE PROCESS", "SYSTEM IDLE PROCESS"]:
                                return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            process_name = "Unknown"
                except Exception:
                    process_name = "Unknown"

                windows.append((title, process_name))
                return True
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            pass

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
