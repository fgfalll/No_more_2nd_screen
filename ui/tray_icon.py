"""
System tray icon module.

This module provides the system tray icon and context menu for the application.
"""

from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication, QMessageBox
)
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QObject, Signal, Qt

import sys
from pathlib import Path


class TrayIconManager(QObject):
    """Manages the system tray icon and menu."""

    # Signals
    toggle_protection = Signal()
    show_settings = Signal()
    exit_app = Signal()
    protection_toggled = Signal(bool)

    def __init__(self, parent=None):
        """
        Initialize the tray icon manager.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        self.protection_enabled = True
        self.tray_icon = None

    def create_tray_icon(self):
        """Create and set up the system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False

        # Create the icon
        icon = self._create_status_icon(True)

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(icon)

        # Create context menu
        menu = self._create_menu()
        self.tray_icon.setContextMenu(menu)

        # Set tooltip
        self.update_tooltip()

        # Connect activation signal (single click)
        self.tray_icon.activated.connect(self.on_activated)

        # Show the tray icon
        self.tray_icon.show()

        return True

    def _create_menu(self) -> QMenu:
        """
        Create the context menu for the tray icon.

        Returns:
            QMenu with all actions
        """
        menu = QMenu()

        # Toggle Protection action
        self.action_toggle = QAction("Disable Protection", menu)
        self.action_toggle.triggered.connect(self._on_toggle_protection)
        menu.addAction(self.action_toggle)

        menu.addSeparator()

        # Settings action
        action_settings = QAction("Settings...", menu)
        action_settings.triggered.connect(self.show_settings.emit)
        menu.addAction(action_settings)

        # About action
        action_about = QAction("About", menu)
        action_about.triggered.connect(self._show_about)
        menu.addAction(action_about)

        menu.addSeparator()

        # Exit action
        action_exit = QAction("Exit", menu)
        action_exit.triggered.connect(self.exit_app.emit)
        menu.addAction(action_exit)

        return menu

    def _create_status_icon(self, enabled: bool) -> QIcon:
        """
        Create a status icon programmatically.

        Args:
            enabled: True for green (enabled), False for gray (disabled)

        Returns:
            QIcon with the appropriate color
        """
        # Create a pixmap
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        # Create painter
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Choose color based on state
        if enabled:
            # Green circle for enabled
            color = QColor(0, 200, 0)
        else:
            # Gray circle for disabled
            color = QColor(128, 128, 128)

        painter.setBrush(color)
        painter.setPen(Qt.NoPen)

        # Draw a circle
        margin = 4
        painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

        # Add a "P" for projector/protection
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(28)
        painter.setFont(font)

        painter.drawText(pixmap.rect(), Qt.AlignCenter, "P")

        painter.end()

        return QIcon(pixmap)

    def update_icon(self, enabled: bool):
        """
        Update the tray icon based on protection state.

        Args:
            enabled: True if protection is enabled, False otherwise
        """
        self.protection_enabled = enabled

        if self.tray_icon:
            icon = self._create_status_icon(enabled)
            self.tray_icon.setIcon(icon)

            # Update menu text
            if enabled:
                self.action_toggle.setText("Disable Protection")
            else:
                self.action_toggle.setText("Enable Protection")

            self.update_tooltip()

    def update_tooltip(self):
        """Update the tray icon tooltip."""
        if self.tray_icon:
            status = "enabled" if self.protection_enabled else "disabled"
            self.tray_icon.setToolTip(f"No More 2nd Screen\nProtection: {status}")

    def _on_toggle_protection(self):
        """Handle toggle protection action."""
        self.protection_enabled = not self.protection_enabled
        self.update_icon(self.protection_enabled)
        self.toggle_protection.emit()
        self.protection_toggled.emit(self.protection_enabled)

    def _show_about(self):
        """Show about dialog."""
        about_text = """
        <h3>No More 2nd Screen</h3>
        <p>Version 1.0</p>
        <p>Automatically moves non-whitelisted applications from projector monitors to the main display.</p>
        <p><b>Key Features:</b></p>
        <ul>
        <li>Protect projector monitors by restricting them to whitelisted apps</li>
        <li>PowerPoint only allowed in slideshow/presentation mode</li>
        <li>System tray application for easy management</li>
        <li>Customizable whitelist and monitor selection</li>
        </ul>
        <p><b>License:</b> Source-available for personal and non-commercial use only.</p>
        <p>Commercial use requires explicit permission from the author.</p>
        """

        QMessageBox.information(
            None,
            "About No More 2nd Screen",
            about_text
        )

    def on_activated(self, reason):
        """
        Handle tray icon activation.

        Args:
            reason: Activation reason
        """
        # Double-click or middle-click shows settings
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.MiddleClick):
            self.show_settings.emit()

    def show_message(self, title: str, message: str, icon_type=QSystemTrayIcon.Information):
        """
        Show a balloon message from the tray icon.

        Args:
            title: Message title
            message: Message body
            icon_type: Type of icon to display
        """
        if self.tray_icon and QSystemTrayIcon.supportsMessages():
            self.tray_icon.showMessage(title, message, icon_type, 3000)

    def hide(self):
        """Hide the tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
