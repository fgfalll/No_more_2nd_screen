"""
Window monitoring and enforcement module.

This module monitors all windows and enforces projector restrictions
by moving non-whitelisted windows back to the primary monitor.
"""

import win32gui
import win32con
import win32process
import psutil
from typing import Optional, Callable, Dict
from dataclasses import dataclass

from .monitor_info import (
    get_primary_monitor,
    is_window_on_any_projector,
    get_monitor_by_index,
    has_projectors
)
from .whitelist import get_whitelist


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

    def __init__(self, protected_monitor_indices=None, whitelist=None):
        """
        Initialize the window monitor.

        Args:
            protected_monitor_indices: List of 1-based monitor indices to protect (default: [2, 3])
            whitelist: Whitelist instance (uses default if None)
        """
        if protected_monitor_indices is None:
            protected_monitor_indices = [2, 3]

        self.protected_monitor_indices = protected_monitor_indices
        self.whitelist = whitelist or get_whitelist()
        self.enabled = True
        self.stats = WindowMoveStats()

        # Callback for when a window is moved
        self.on_window_moved: Optional[Callable] = None

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

    def set_protected_monitors(self, indices):
        """
        Set which monitor indices to protect.

        Args:
            indices: List of 1-based monitor indices (e.g., [2, 3])
        """
        self.protected_monitor_indices = indices

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
        # Must be visible
        if not win32gui.IsWindowVisible(hwnd):
            return False

        # Must have a title (excludes many system windows)
        try:
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return False
        except Exception:
            return False

        # Exclude certain window classes (e.g., shell windows)
        try:
            class_name = win32gui.GetClassName(hwnd)
            # Skip shell windows and some system windows
            if class_name in ['Shell_TrayWnd', 'Progman', 'WorkerW']:
                return False
        except Exception:
            return False

        return True

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

        # Check if window is on a protected projector
        if not is_window_on_any_projector(hwnd, self.protected_monitor_indices):
            return False, None

        # Get the process name
        process_name = self.get_process_name(hwnd)
        if not process_name:
            # Unknown process - move to be safe
            return True, None

        # Check if process is whitelisted
        if self.whitelist.is_whitelisted(process_name):
            return False, process_name

        return True, process_name

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
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )

            return True

        except Exception as e:
            print(f"Error moving window: {e}")
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

        moved_count = 0

        def enum_callback(hwnd, _):
            nonlocal moved_count

            if not self.is_valid_window(hwnd):
                return True

            should_move, process_name = self.should_move_window(hwnd)

            if should_move:
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
            print(f"Error enumerating windows: {e}")

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


def get_window_monitor(protected_monitor_indices=None) -> WindowMonitor:
    """
    Get the global window monitor instance.

    Args:
        protected_monitor_indices: Optional monitor indices to protect

    Returns:
        WindowMonitor instance
    """
    global _monitor_instance

    if _monitor_instance is None:
        _monitor_instance = WindowMonitor(protected_monitor_indices)

    return _monitor_instance


def reload_window_monitor():
    """Reload the window monitor configuration."""
    global _monitor_instance
    _monitor_instance = None
