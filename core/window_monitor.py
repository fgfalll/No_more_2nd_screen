"""
Window monitoring and enforcement module.

This module monitors all windows and enforces projector restrictions
by moving non-whitelisted windows back to the primary monitor.
"""

import win32gui
import win32con
import win32process
import win32api
import psutil
import time
from typing import Optional, Callable, Dict, Set, List
from dataclasses import dataclass

from .monitor_info import (
    get_primary_monitor,
    get_monitor_by_device_name,
    get_device_name_for_hmonitor,
    has_projectors,
    is_window_on_monitor,
)
from .whitelist import get_whitelist

VK_LBUTTON = 0x01


def _is_dragging() -> bool:
    """Check if user is actively dragging (left mouse button pressed)."""
    return (win32api.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0


@dataclass
class WindowMoveStats:
    """Statistics about moved windows."""

    total_moves: int = 0
    last_moved_process: str = ""
    last_moved_title: str = ""


class WindowMonitor:
    """
    Monitors windows and enforces projector restrictions.
    """

    def __init__(self, protected_device_names=None, whitelist=None):
        """
        Initialize the window monitor.

        Args:
            protected_device_names: List of device names to protect (e.g., ["\\\\.\\DISPLAY2", "\\\\.\\DISPLAY3"])
            whitelist: Whitelist instance (uses default if None)
        """
        if protected_device_names is None:
            protected_device_names = ["\\\\.\\DISPLAY2", "\\\\.\\DISPLAY3"]

        self.protected_device_names = protected_device_names
        self.primary_device = None  # NEW: Always allowed monitor
        self.whitelist = whitelist or get_whitelist()
        self.enabled = True
        self.stats = WindowMoveStats()

        self.on_window_moved: Optional[Callable] = None

        self._recently_moved: dict[int, float] = {}
        self._move_debounce_ms = 500
        self._was_dragging = False
        self._deferred_hwnds: Set[int] = set()

    def is_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """
        Enable or disable monitoring.

        Args:
            enabled: True to enable, False to disable
        """
        self.enabled = enabled

    def set_protected_devices(self, device_names: List[str]):
        """
        Set which device names to protect.

        Args:
            device_names: List of device names (e.g., ["\\\\.\\DISPLAY2", "\\\\.\\DISPLAY3"])
        """
        self.protected_device_names = device_names

    def _is_recently_moved(self, hwnd: int) -> bool:
        """Check if window was moved within the debounce period."""
        if hwnd in self._recently_moved:
            elapsed = time.time() - self._recently_moved[hwnd]
            if elapsed < self._move_debounce_ms / 1000.0:
                return True
        return False

    def _cleanup_old_entries(self):
        """Remove stale entries from recently_moved dict."""
        current_time = time.time()
        stale_threshold = current_time - (self._move_debounce_ms / 1000.0)
        self._recently_moved = {
            hwnd: ts
            for hwnd, ts in self._recently_moved.items()
            if ts >= stale_threshold
        }

    def set_primary_device(self, device_name: Optional[str]):
        """
        Set primary device (always allowed - protection turned OFF).

        Args:
            device_name: Device name to set as primary (e.g., "\\\\.\\DISPLAY2")
        """
        self.primary_device = device_name

    def get_process_name(self, hwnd: int) -> Optional[str]:
        """
        Get the process name for a window.

        Args:
            hwnd: Window handle

        Returns:
            Process name (uppercase) or None if not found.
        """
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid:
                process = psutil.Process(pid)
                return process.name().upper()
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            pass

        return None

    def is_valid_window(self, hwnd: int) -> bool:
        """
        Check if a window should be monitored.

        Args:
            hwnd: Window handle

        Returns:
            True if the window should be monitored, False otherwise.
        """
        if not win32gui.IsWindowVisible(hwnd):
            return False

        try:
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return False
        except Exception:
            return False

        try:
            class_name = win32gui.GetClassName(hwnd)
            if class_name in ["Shell_TrayWnd", "Progman", "WorkerW"]:
                return False
        except Exception:
            return False

        return True

    def is_window_on_device(self, hwnd: int, device_name: str) -> bool:
        """
        Check if a window is on a specific device.

        Args:
            hwnd: Window handle
            device_name: Device name (e.g., "\\\\.\\DISPLAY2")

        Returns:
            True if window center is on the device, False otherwise.
        """
        monitor = get_monitor_by_device_name(device_name)
        if monitor:
            return is_window_on_monitor(hwnd, monitor)
        return False

    def _is_powerpoint_in_slideshow(self, hwnd: int, process_name: str) -> bool:
        """Check if PowerPoint window is in slideshow/presentation mode."""
        if process_name != "POWERPNT.EXE":
            return False

        try:
            class_name = win32gui.GetClassName(hwnd)
            window_title = win32gui.GetWindowText(hwnd)

            # PowerPoint slideshow window class names:
            # - "PPTFrameClass" (main window - NOT slideshow)
            # - "screenClass" (slideshow window - this is what we want to allow)
            # Window is slideshow if class is "screenClass"

            return class_name == "screenClass"
        except Exception:
            return False

    def should_move_window(self, hwnd: int) -> tuple[bool, Optional[str]]:
        """
        Check if a window should be moved back to primary monitor.

        Args:
            hwnd: Window handle

        Returns:
            Tuple of (should_move, process_name)
        """
        if not self.enabled:
            return False, None

        process_name = self.get_process_name(hwnd)

        if not process_name:
            return True, None

        # Special handling for PowerPoint - only allow when in slideshow mode
        if process_name == "POWERPNT.EXE":
            if self._is_powerpoint_in_slideshow(hwnd, process_name):
                return False, process_name  # Allow PowerPoint in slideshow mode
            # PowerPoint NOT in slideshow mode - should be moved
            for device_name in self.protected_device_names:
                if self.is_window_on_device(hwnd, device_name):
                    return True, process_name
            return False, process_name

        if self.whitelist.is_whitelisted(process_name):
            return False, process_name

        # Skip if window is on the primary (always allowed) monitor
        if self.primary_device and self.is_window_on_device(hwnd, self.primary_device):
            return False, process_name

        for device_name in self.protected_device_names:
            if self.is_window_on_device(hwnd, device_name):
                return True, process_name

        return False, process_name

    def move_to_primary_monitor(self, hwnd: int) -> bool:
        """
        Move a window to the primary monitor.

        Args:
            hwnd: Window handle

        Returns:
            True if moved successfully, False otherwise.
        """
        primary_monitor = get_primary_monitor()
        if primary_monitor is None:
            return False

        try:
            # Get current window position and size
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            # Calculate new position on primary monitor
            # Center the window or place at top-left corner
            work_rect = primary_monitor.rc_work

            # Ensure window fits on the primary monitor
            if width > work_rect[2] - work_rect[0]:
                width = work_rect[2] - work_rect[0]
            if height > work_rect[3] - work_rect[1]:
                height = work_rect[3] - work_rect[1]

            # Position at top-left of work area with some padding
            new_x = work_rect[0] + 20
            new_y = work_rect[1] + 20

            # Move the window
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                new_x,
                new_y,
                width,
                height,
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE,
            )

            # Track when this window was last moved (debounce)
            self._recently_moved[hwnd] = time.time()

            return True

        except Exception as e:
            return False

    def check_and_enforce(self) -> int:
        """
        Check all windows and enforce projector restrictions.

        Returns:
            Number of windows moved.
        """
        if not self.enabled:
            return 0

        # Check if we have projectors to protect
        if not has_projectors():
            return 0

        # Clean up stale entries
        self._cleanup_old_entries()

        # Detect if user is currently dragging
        is_currently_dragging = _is_dragging()

        # Initialize moved counter
        moved_count = 0

        # Detect drag end - apply deferred enforcement
        if self._was_dragging and not is_currently_dragging:
            # Drag just ended - process deferred windows
            deferred = self._deferred_hwnds.copy()
            self._deferred_hwnds.clear()
            for hwnd in deferred:
                if self.is_valid_window(hwnd) and not self._is_recently_moved(hwnd):
                    if self.move_to_primary_monitor(hwnd):
                        moved_count += 1
                        self.stats.total_moves += 1
                        try:
                            title = win32gui.GetWindowText(hwnd)
                            self.stats.last_moved_title = title
                            self.stats.last_moved_process = (
                                self.get_process_name(hwnd) or "Unknown"
                            )
                            if self.on_window_moved:
                                self.on_window_moved(
                                    hwnd, self.get_process_name(hwnd), title
                                )
                        except Exception:
                            pass

        self._was_dragging = is_currently_dragging

        def enum_callback(hwnd, _):
            nonlocal moved_count

            if not self.is_valid_window(hwnd):
                return True

            # Skip recently moved windows (debounce)
            if self._is_recently_moved(hwnd):
                return True

            should_move, process_name = self.should_move_window(hwnd)

            if should_move:
                if is_currently_dragging:
                    # Defer enforcement until drag ends
                    self._deferred_hwnds.add(hwnd)
                else:
                    if self.move_to_primary_monitor(hwnd):
                        moved_count += 1
                        self.stats.total_moves += 1

                        # Try to get window info for stats
                        try:
                            title = win32gui.GetWindowText(hwnd)
                            self.stats.last_moved_title = title
                            self.stats.last_moved_process = process_name or "Unknown"

                            # Call callback if set
                            if self.on_window_moved:
                                self.on_window_moved(hwnd, process_name, title)
                        except Exception:
                            pass

            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            pass

        return moved_count

    def get_stats(self) -> WindowMoveStats:
        """
        Get statistics about moved windows.

        Returns:
            WindowMoveStats object
        """
        return self.stats

    def reset_stats(self):
        """Reset the move statistics."""
        self.stats = WindowMoveStats()


# Global monitor instance
_monitor_instance = None


def get_window_monitor(protected_device_names=None) -> WindowMonitor:
    """
    Get the global window monitor instance.

    Args:
        protected_device_names: Optional device names to protect

    Returns:
        WindowMonitor instance
    """
    global _monitor_instance

    if _monitor_instance is None:
        _monitor_instance = WindowMonitor(protected_device_names)

    return _monitor_instance


def reload_window_monitor():
    """Reload the window monitor configuration."""
    global _monitor_instance
    _monitor_instance = None
