"""
Monitor detection and coordinate management module.

This module handles detection of monitors and their coordinates using Windows APIs.
It distinguishes between the primary monitor and projector monitors.
"""

import ctypes
from ctypes import wintypes
from typing import List, Tuple
from dataclasses import dataclass


# Define Windows API structures
class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long)
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_ulong),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', ctypes.c_ulong)
    ]


# Define callback type for EnumDisplayMonitors
MONITORENUMPROC = ctypes.CFUNCTYPE(
    ctypes.c_int,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM
)


@dataclass
class MonitorInfo:
    """Information about a monitor."""
    handle: int
    index: int
    is_primary: bool
    rc_monitor: Tuple[int, int, int, int]
    rc_work: Tuple[int, int, int, int]

    @property
    def left(self) -> int:
        return self.rc_monitor[0]

    @property
    def top(self) -> int:
        return self.rc_monitor[1]

    @property
    def right(self) -> int:
        return self.rc_monitor[2]

    @property
    def bottom(self) -> int:
        return self.rc_monitor[3]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


# Load Windows API
user32 = ctypes.windll.user32

# Define GetMonitorInfo function
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL

# Define EnumDisplayMonitors function
user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(RECT),
    MONITORENUMPROC,
    wintypes.LPARAM
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL


# Monitor enumeration state
class _EnumState:
    """State object for monitor enumeration."""
    def __init__(self):
        self.monitors = []


# Global state for enumeration
_enum_state = _EnumState()


def _monitor_enum_callback(hmonitor, hdc, rect, lparam):
    """Callback function for EnumDisplayMonitors."""
    global _enum_state

    try:
        monitor_info = MONITORINFO()
        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)

        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(monitor_info)):
            # Check if this is the primary monitor
            is_primary = bool(monitor_info.dwFlags & 0x00000001)  # MONITORINFOF_PRIMARY

            monitor = MonitorInfo(
                handle=hmonitor,
                index=len(_enum_state.monitors),
                is_primary=is_primary,
                rc_monitor=(
                    monitor_info.rcMonitor.left,
                    monitor_info.rcMonitor.top,
                    monitor_info.rcMonitor.right,
                    monitor_info.rcMonitor.bottom
                ),
                rc_work=(
                    monitor_info.rcWork.left,
                    monitor_info.rcWork.top,
                    monitor_info.rcWork.right,
                    monitor_info.rcWork.bottom
                )
            )

            _enum_state.monitors.append(monitor)
    except Exception as e:
        print(f"Error in monitor callback: {e}")

    return True


def get_monitors() -> List[MonitorInfo]:
    """
    Get all monitors connected to the system.

    Returns:
        List of MonitorInfo objects for all monitors.
    """
    global _enum_state
    _enum_state = _EnumState()

    try:
        user32.EnumDisplayMonitors(
            None,
            None,
            MONITORENUMPROC(_monitor_enum_callback),
            0
        )
    except Exception as e:
        print(f"Error enumerating monitors: {e}")
        return []

    return _enum_state.monitors


def get_primary_monitor() -> MonitorInfo:
    """
    Get the primary monitor.

    Returns:
        MonitorInfo object for the primary monitor, or None if not found.
    """
    monitors = get_monitors()
    for monitor in monitors:
        if monitor.is_primary:
            return monitor
    return None


def get_projector_monitors() -> List[MonitorInfo]:
    """
    Get all projector monitors (non-primary monitors).

    Returns:
        List of MonitorInfo objects for all non-primary monitors.
    """
    monitors = get_monitors()
    return [m for m in monitors if not m.is_primary]


def get_monitor_by_index(index: int) -> MonitorInfo:
    """
    Get monitor by its 1-based index (1 = primary, 2 = second, etc.).

    Args:
        index: 1-based monitor index

    Returns:
        MonitorInfo object or None if not found.
    """
    monitors = get_monitors()
    if 0 < index <= len(monitors):
        return monitors[index - 1]
    return None


def is_point_in_rect(x: int, y: int, rect: Tuple[int, int, int, int]) -> bool:
    """
    Check if a point is within a rectangle.

    Args:
        x: X coordinate
        y: Y coordinate
        rect: Rectangle as (left, top, right, bottom)

    Returns:
        True if point is within rectangle, False otherwise.
    """
    left, top, right, bottom = rect
    return left <= x <= right and top <= y <= bottom


def is_window_on_monitor(hwnd: int, monitor: MonitorInfo) -> bool:
    """
    Check if a window is primarily on a specific monitor.

    Uses the center point of the window to determine which monitor it's on.

    Args:
        hwnd: Window handle
        monitor: MonitorInfo object to check against

    Returns:
        True if window center is on the monitor, False otherwise.
    """
    import win32gui

    try:
        rect = win32gui.GetWindowRect(hwnd)
        center_x = (rect[0] + rect[2]) // 2
        center_y = (rect[1] + rect[3]) // 2

        return is_point_in_rect(center_x, center_y, monitor.rc_monitor)
    except Exception:
        return False


def is_window_on_projector(hwnd: int) -> bool:
    """
    Check if a window is on any projector (non-primary monitor).

    Args:
        hwnd: Window handle

    Returns:
        True if window is on a projector, False otherwise.
    """
    projectors = get_projector_monitors()
    return any(is_window_on_monitor(hwnd, p) for p in projectors)


def is_window_on_any_projector(hwnd: int, protected_monitor_indices: List[int]) -> bool:
    """
    Check if a window is on any of the specified protected projector monitors.

    Args:
        hwnd: Window handle
        protected_monitor_indices: List of 1-based monitor indices to protect (e.g., [2, 3])

    Returns:
        True if window is on any protected monitor, False otherwise.
    """
    for index in protected_monitor_indices:
        monitor = get_monitor_by_index(index)
        if monitor and is_window_on_monitor(hwnd, monitor):
            return True
    return False


def get_monitor_count() -> int:
    """
    Get the total number of monitors connected.

    Returns:
        Number of monitors.
    """
    return len(get_monitors())


def has_projectors() -> bool:
    """
    Check if there are any projector (non-primary) monitors connected.

    Returns:
        True if there are projectors, False otherwise.
    """
    return len(get_projector_monitors()) > 0
