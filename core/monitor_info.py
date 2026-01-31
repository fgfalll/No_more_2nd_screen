"""
Monitor detection and coordinate management module.

This module handles detection of monitors and their coordinates using Windows APIs.
It distinguishes between the primary monitor and projector monitors.
Provides device names (e.g., \\\\\\\\.\\\\DISPLAY1) for reliable monitor identification.
"""

import ctypes
from ctypes import (
    Structure,
    c_wchar,
    byref,
    POINTER,
    windll,
    sizeof,
    create_unicode_buffer,
)
from ctypes.wintypes import (
    DWORD,
    BOOL,
    HMONITOR,
    RECT,
    UINT,
    LPCWSTR,
    LPARAM,
    HDC,
    WORD,
)
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


user32 = windll.user32


QDC_ONLY_ACTIVE_PATHS = 0x00000002
QDC_DATABASE_CURRENT = 0x00000004
DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME = 2
DISPLAYCONFIG_DEVICE_INFO_GET_TARGET_NAME = 3
CDS_SET_PRIMARY = 0x00000010
CDS_UPDATEREGISTRY = 0x00000001
CDS_NORESET = 0x00000004
DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001


class LUID(Structure):
    _fields_ = [
        ("LowPart", DWORD),
        ("HighPart", DWORD),
    ]


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", DWORD),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", DWORD),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", DWORD),
        ("szDevice", ctypes.c_wchar * 32),
    ]


class DISPLAYCONFIG_DEVICE_INFO_HEADER(Structure):
    _fields_ = [
        ("type", DWORD),
        ("size", DWORD),
        ("adapterId", LUID),
        ("id", DWORD),
    ]


class DISPLAYCONFIG_TARGET_DEVICE_NAME(Structure):
    _fields_ = [
        ("header", DISPLAYCONFIG_DEVICE_INFO_HEADER),
        ("flags", DWORD),
        ("outputTechnology", DWORD),
        ("edidManufactureId", WORD),
        ("edidProductCodeId", WORD),
        ("connectorInstance", DWORD),
        ("monitorFriendlyDeviceName", ctypes.c_wchar * 64),
        ("monitorDevicePath", ctypes.c_wchar * 128),
    ]


@dataclass
class MonitorGroup:
    """Group of physically connected monitors that form one logical display."""

    id: str
    name: str
    device_names: List[str]
    is_primary: bool
    is_combined: bool
    is_clone: bool
    clone_of: Optional[str]
    bounds: Tuple[int, int, int, int]
    resolution: Tuple[int, int]

    @property
    def display_name(self) -> str:
        """UI display: 'DISPLAY1 - Dell U2722D'"""
        parts = [self.name]
        if self.is_combined:
            parts.append("→ Combined")
        if self.is_clone:
            parts.append(f"Cloned from {self.clone_of}")
        parts.append(f"({self.resolution[0]}x{self.resolution[1]})")
        return " ".join(parts)

    @property
    def short_name(self) -> str:
        """Short name: 'DISPLAY1'"""
        if self.device_names:
            return self.device_names[0].split("\\")[-1]
        return self.name

    @property
    def icon(self) -> str:
        """Icon for UI: star for primary, chain for combined"""
        if self.is_primary:
            return "*"
        elif self.is_combined:
            return "#"
        elif self.is_clone:
            return "="
        return "-"


class DISPLAYCONFIG_PATH_SOURCE_INFO(Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", DWORD),
        ("modeInfoIdx", UINT),
        ("statusFlags", DWORD),
    ]


class DISPLAYCONFIG_PATH_TARGET_INFO(Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", DWORD),
        ("modeInfoIdx", UINT),
        ("statusFlags", DWORD),
        ("targetAvailable", DWORD),
        ("nameChange", DWORD),
    ]


class DISPLAYCONFIG_PATH_INFO(Structure):
    _fields_ = [
        ("sourceInfo", DISPLAYCONFIG_PATH_SOURCE_INFO),
        ("targetInfo", DISPLAYCONFIG_PATH_TARGET_INFO),
        ("flags", UINT),
    ]


class DISPLAYCONFIG_2DREGION(Structure):
    _fields_ = [
        ("cx", DWORD),
        ("cy", DWORD),
    ]


class DISPLAYCONFIG_VIDEO_SIGNAL_INFO(Structure):
    _fields_ = [
        ("activeSize", DISPLAYCONFIG_2DREGION),
        ("totalSize", DISPLAYCONFIG_2DREGION),
        ("pixelRate", DWORD),
        ("hSyncFreq", DWORD),
        ("vSyncFreq", DWORD),
        ("additionalSignalInfo", DWORD),
        ("standardScanLineTiming", DWORD),
        ("scalings", UINT),
        ("scanLineOrdering", UINT),
        ("refreshRate", DWORD),
    ]


class DISPLAYCONFIG_MODE_INFO(Structure):
    _fields_ = [
        ("infoType", UINT),
        ("id", UINT),
        ("adapterId", LUID),
        ("targetMode", DISPLAYCONFIG_VIDEO_SIGNAL_INFO),
    ]


user32.EnumDisplayDevicesW.argtypes = [
    LPCWSTR,
    DWORD,
    POINTER(DISPLAY_DEVICEW),
    DWORD,
]
user32.EnumDisplayDevicesW.restype = BOOL

user32.GetMonitorInfoW.argtypes = [
    HMONITOR,
    POINTER(MONITORINFOEXW),
]
user32.GetMonitorInfoW.restype = BOOL

user32.GetDisplayConfigBufferSizes.argtypes = [
    UINT,
    POINTER(UINT),
    POINTER(UINT),
]
user32.GetDisplayConfigBufferSizes.restype = DWORD

user32.QueryDisplayConfig.argtypes = [
    UINT,
    POINTER(UINT),
    POINTER(DISPLAYCONFIG_PATH_INFO),
    POINTER(UINT),
    POINTER(DISPLAYCONFIG_MODE_INFO),
    POINTER(UINT),
]
user32.QueryDisplayConfig.restype = DWORD

user32.DisplayConfigGetDeviceInfo.argtypes = [
    POINTER(DISPLAYCONFIG_TARGET_DEVICE_NAME),
]
user32.DisplayConfigGetDeviceInfo.restype = DWORD


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


MONITORENUMPROC = ctypes.CFUNCTYPE(
    ctypes.c_int, HMONITOR, HDC, ctypes.POINTER(RECT), LPARAM
)


@dataclass
class MonitorInfo:
    """Information about a monitor."""

    handle: int
    index: int
    is_primary: bool
    rc_monitor: Tuple[int, int, int, int]
    rc_work: Tuple[int, int, int, int]
    device_name: str = ""
    friendly_name: str = ""
    edid_name: str = ""
    width: int = 0
    height: int = 0

    def __post_init__(self):
        if self.width == 0:
            self.width = self.right - self.left
        if self.height == 0:
            self.height = self.bottom - self.top

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
    def display_name(self) -> str:
        """UI display: 'DISPLAY1 - Dell U2722D (1920x1080)'"""
        parts = [self.short_name]
        if self.friendly_name:
            parts.append(f"- {self.friendly_name}")
        parts.append(f"({self.width}x{self.height})")
        return " ".join(parts)

    @property
    def short_name(self) -> str:
        """Short name: 'DISPLAY1'"""
        if self.device_name:
            return self.device_name.split("\\")[-1]
        return f"Monitor {self.index}"


EnumDisplayMonitors = user32.EnumDisplayMonitors
EnumDisplayMonitors.argtypes = [
    HDC,
    ctypes.POINTER(RECT),
    MONITORENUMPROC,
    LPARAM,
]
EnumDisplayMonitors.restype = BOOL


EnumDisplayDevices = user32.EnumDisplayDevicesW
EnumDisplayDevices.argtypes = [LPCWSTR, DWORD, POINTER(DISPLAY_DEVICEW), DWORD]
EnumDisplayDevices.restype = BOOL


GetMonitorInfo = user32.GetMonitorInfoW
GetMonitorInfo.argtypes = [HMONITOR, POINTER(MONITORINFOEXW)]
GetMonitorInfo.restype = BOOL


_monitor_enum_state = {"monitors": []}


def _monitor_enum_callback(hmonitor, hdc, rect, lparam):
    """Callback function for EnumDisplayMonitors."""
    global _monitor_enum_state

    try:
        monitor_info = MONITORINFOEXW()
        monitor_info.cbSize = DWORD(sizeof(MONITORINFOEXW))

        if user32.GetMonitorInfoW(hmonitor, byref(monitor_info)):
            is_primary = bool(monitor_info.dwFlags & 0x00000001)

            device_name = monitor_info.szDevice if monitor_info.szDevice else ""

            monitor = MonitorInfo(
                handle=hmonitor,
                index=len(_monitor_enum_state["monitors"]),
                is_primary=is_primary,
                rc_monitor=(
                    monitor_info.rcMonitor.left,
                    monitor_info.rcMonitor.top,
                    monitor_info.rcMonitor.right,
                    monitor_info.rcMonitor.bottom,
                ),
                rc_work=(
                    monitor_info.rcWork.left,
                    monitor_info.rcWork.top,
                    monitor_info.rcWork.right,
                    monitor_info.rcWork.bottom,
                ),
                device_name=device_name,
                width=monitor_info.rcMonitor.right - monitor_info.rcMonitor.left,
                height=monitor_info.rcMonitor.bottom - monitor_info.rcMonitor.top,
            )

            _monitor_enum_state["monitors"].append(monitor)
    except Exception as e:
        pass

    return True


_monitor_cache = {"monitors": None, "timestamp": 0}
CACHE_DURATION = 5.0


def get_monitors() -> List[MonitorInfo]:
    """
    Get all monitors connected to the system.

    Returns:
        List of MonitorInfo objects for all monitors.
    """
    global _monitor_cache, _monitor_enum_state
    import time

    current_time = time.time()

    if _monitor_cache["monitors"] is not None and (
        current_time - _monitor_cache["timestamp"] < CACHE_DURATION
    ):
        return _monitor_cache["monitors"]

    _monitor_enum_state = {"monitors": []}

    # First, enumerate monitors via EnumDisplayMonitors
    try:
        user32.EnumDisplayMonitors(
            None, None, MONITORENUMPROC(_monitor_enum_callback), 0
        )
    except Exception as e:
        pass

    monitors = _monitor_enum_state["monitors"]
    device_names_from_enum = {m.device_name for m in monitors if m.device_name}

    # Then, enumerate all display devices to catch cloned/duplicate displays
    try:
        display_devices = get_all_display_devices()
        for device_name, device in display_devices.items():
            # device_name is now the proper DeviceName from DISPLAY_DEVICEW
            # e.g., "\\.\DISPLAY1" or "\\.\DISPLAY1\Monitor0"

            # Add any display devices that weren't found by EnumDisplayMonitors
            if device_name not in device_names_from_enum:
                # For cloned displays, find a monitor to copy coordinates from
                primary_monitor = None
                reference_monitor = None
                for m in monitors:
                    if m.is_primary:
                        primary_monitor = m
                    reference_monitor = m
                    if primary_monitor:
                        break

                ref_monitor = primary_monitor or reference_monitor

                if ref_monitor:
                    monitor = MonitorInfo(
                        handle=ref_monitor.handle,  # Same handle for cloned displays
                        index=len(monitors),
                        is_primary=False,  # Cloned displays aren't primary (by default)
                        rc_monitor=ref_monitor.rc_monitor,
                        rc_work=ref_monitor.rc_work,
                        device_name=device_name,  # Use the actual device name directly
                        width=ref_monitor.width,
                        height=ref_monitor.height,
                    )
                    monitors.append(monitor)
    except Exception as e:
        pass

    _monitor_cache["monitors"] = monitors
    _monitor_cache["timestamp"] = current_time

    return monitors


def get_friendly_name_for_device(device_name: str) -> Optional[str]:
    """Get monitor friendly name via DisplayConfigGetDeviceInfo."""
    try:
        path_count = UINT()
        mode_count = UINT()

        result = user32.GetDisplayConfigBufferSizes(
            UINT(QDC_ONLY_ACTIVE_PATHS),
            ctypes.byref(path_count),
            ctypes.byref(mode_count),
        )
        if result != 0:
            return None

        path_array = (DISPLAYCONFIG_PATH_INFO * path_count.value)()
        mode_array = (DISPLAYCONFIG_MODE_INFO * mode_count.value)()

        result = user32.QueryDisplayConfig(
            UINT(QDC_ONLY_ACTIVE_PATHS),
            ctypes.byref(path_count),
            path_array,
            ctypes.byref(mode_count),
            mode_array,
            None,
        )
        if result != 0:
            return None

        for i in range(path_count.value):
            path = path_array[i]
            target_name = DISPLAYCONFIG_TARGET_DEVICE_NAME()
            target_name.header.type = DWORD(DISPLAYCONFIG_DEVICE_INFO_GET_TARGET_NAME)
            target_name.header.size = DWORD(sizeof(DISPLAYCONFIG_TARGET_DEVICE_NAME))
            target_name.header.adapterId = path.targetInfo.adapterId.LowPart
            target_name.header.id = path.targetInfo.id

            result = user32.DisplayConfigGetDeviceInfo(ctypes.byref(target_name))
            if result == 0 and target_name.monitorFriendlyDeviceName:
                return target_name.monitorFriendlyDeviceName

        return None
    except Exception as e:
        return None


def get_all_display_devices() -> Dict[str, DISPLAY_DEVICEW]:
    r"""Get all active display devices via EnumDisplayDevicesW.

    Returns:
        Dict where keys are device names and values are DISPLAY_DEVICEW structures.
    """
    devices = {}

    # Enumerate all display adapters
    for dev_num in range(256):
        device = DISPLAY_DEVICEW()
        device.cb = DWORD(sizeof(DISPLAY_DEVICEW))

        if not user32.EnumDisplayDevicesW(None, dev_num, byref(device), 0):
            break

        # Only include devices that are attached to desktop
        # This filters out virtual/ghost displays
        if device.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            devices[device.DeviceName] = device

    return devices


def get_device_name_for_hmonitor(hmonitor: int) -> Optional[str]:
    """Map HMONITOR handle to device name using MONITORINFOEX."""
    monitor_info = MONITORINFOEXW()
    monitor_info.cbSize = DWORD(sizeof(MONITORINFOEXW))

    if not user32.GetMonitorInfoW(HMONITOR(hmonitor), byref(monitor_info)):
        return None

    return monitor_info.szDevice


def get_monitor_by_device_name(device_name: str) -> Optional[MonitorInfo]:
    """Find monitor by device name."""
    monitors = get_monitors()
    for monitor in monitors:
        if monitor.device_name == device_name:
            return monitor
    return None


def get_monitor_by_handle(handle: int) -> Optional[MonitorInfo]:
    """Find monitor by handle."""
    monitors = get_monitors()
    for monitor in monitors:
        if monitor.handle == handle:
            return monitor
    return None


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
        True if there are projectors (multiple displays), False otherwise.
    """
    # No protection needed if there's only one display
    monitors = get_monitors()
    return len(monitors) > 1


def get_display_topology() -> str:
    """
    Get current display topology using QueryDisplayConfig.

    Returns:
        'extend', 'clone', 'internal', 'external', or 'unknown'
    """
    flags = QDC_DATABASE_CURRENT
    topology_id = UINT()

    result = user32.QueryDisplayConfig(
        UINT(flags),
        ctypes.byref(topology_id),
        None,
        None,
        None,
        ctypes.byref(topology_id),
    )

    if result != 0:
        return "unknown"

    return str(topology_id.value)


def get_monitor_groups() -> List[MonitorGroup]:
    """
    Get monitor groups with relationship detection.

    Returns:
        List of MonitorGroup objects grouped by topology
    """
    groups = []
    monitors = get_monitors()

    for monitor in monitors:
        is_p = monitor.device_name == get_primary_device_name()
        display_num = monitor.device_name.split("\\")[-1] if monitor.device_name else f"Monitor{monitor.index + 1}"

        is_clone, clone_source = is_device_clone(monitor.device_name)

        group = MonitorGroup(
            id=f"monitor_{monitor.index}",
            name=display_num,
            device_names=[monitor.device_name] if monitor.device_name else [],
            is_primary=is_p,
            is_combined=False,
            is_clone=is_clone,
            clone_of=clone_source,
            bounds=(monitor.left, monitor.top, monitor.right, monitor.bottom),
            resolution=(monitor.width, monitor.height),
        )
        groups.append(group)

    return groups


def get_primary_device_name() -> Optional[str]:
    """
    Get the current primary monitor device name.

    Returns:
        Device name (e.g., "\\\\.\\DISPLAY1") or None
    """
    monitors = get_monitors()
    for m in monitors:
        if m.is_primary:
            return m.device_name
    return None


def set_primary_monitor(device_name: str) -> bool:
    """
    Set a monitor as Windows primary using ChangeDisplaySettingsExW.

    Args:
        device_name: Device name to set as primary (e.g., "\\\\.\\DISPLAY2")

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Get the target monitor's info
        target_monitor = get_monitor_by_device_name(device_name)
        if not target_monitor:
            return False

        # Get current primary monitor to set it to the target's position
        primary_monitor = get_primary_monitor()
        if not primary_monitor:
            return False

        # Create DEVMODE structure for the new primary display
        class DEVMODE(ctypes.Structure):
            _fields_ = [
                ("dmSize", DWORD),
                ("dmDriverExtra", DWORD),
                ("dmFields", DWORD),
                ("dmPosition", ctypes.c_long * 2),
                ("dmDisplayOrientation", DWORD),
                ("dmDisplayFixedOutput", DWORD),
                ("dmPelsWidth", DWORD),
                ("dmPelsHeight", DWORD),
                ("dmBitsPerPel", DWORD),
            ]

        devmode = DEVMODE()
        devmode.dmSize = DWORD(ctypes.sizeof(DEVMODE))
        devmode.dmDriverExtra = DWORD(0)
        devmode.dmFields = 0x00000020 | 0x00000008 | 0x00040000 | 0x00080000 | 0x00100000
        devmode.dmPosition = (ctypes.c_long * 2)(0, 0)
        devmode.dmPelsWidth = DWORD(target_monitor.width)
        devmode.dmPelsHeight = DWORD(target_monitor.height)
        devmode.dmBitsPerPel = DWORD(32)

        result = user32.ChangeDisplaySettingsExW(
            LPCWSTR(device_name),
            ctypes.byref(devmode),
            None,
            CDS_SET_PRIMARY | CDS_UPDATEREGISTRY | CDS_NORESET,
            None,
        )

        # Now set all other monitors to extend to the right
        monitors = get_monitors()
        x_offset = target_monitor.width
        for monitor in monitors:
            if monitor.device_name != device_name:
                devmode2 = DEVMODE()
                devmode2.dmSize = DWORD(ctypes.sizeof(DEVMODE))
                devmode2.dmDriverExtra = DWORD(0)
                devmode2.dmFields = 0x00000020 | 0x00000008
                devmode2.dmPosition = (ctypes.c_long * 2)(x_offset, 0)
                devmode2.dmPelsWidth = DWORD(monitor.width)
                devmode2.dmPelsHeight = DWORD(monitor.height)
                devmode2.dmBitsPerPel = DWORD(32)

                user32.ChangeDisplaySettingsExW(
                    LPCWSTR(monitor.device_name),
                    ctypes.byref(devmode2),
                    None,
                    CDS_UPDATEREGISTRY | CDS_NORESET,
                    None,
                )
                x_offset += monitor.width

        # Apply all changes
        user32.ChangeDisplaySettingsExW(None, None, None, 0, None)

        return result == 0  # DISP_CHANGE_SUCCESSFUL

    except Exception as e:
        return False


def is_device_clone(device_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a device is a clone and return original device if so.

    Args:
        device_name: Device name to check (e.g., "\\\\.\\DISPLAY2")

    Returns:
        Tuple of (is_clone, original_device_name) or (True, None)
    """
    try:
        flags = QDC_ONLY_ACTIVE_PATHS
        path_count = UINT()
        mode_count = UINT()

        result = user32.GetDisplayConfigBufferSizes(
            UINT(flags), ctypes.byref(path_count), ctypes.byref(mode_count)
        )

        if result != 0:
            return False, None

        # Safety check for zero counts
        if path_count.value == 0 or mode_count.value == 0:
            return False, None

        path_array = (DISPLAYCONFIG_PATH_INFO * path_count.value)()
        mode_array = (DISPLAYCONFIG_MODE_INFO * mode_count.value)()

        # Use a proper null pointer for the last parameter
        topology_id = UINT()
        result = user32.QueryDisplayConfig(
            UINT(flags),
            ctypes.byref(path_count),
            path_array,
            ctypes.byref(mode_count),
            mode_array,
            ctypes.byref(topology_id),
        )

        if result != 0:
            return False, None

        for i in range(path_count.value):
            path = path_array[i]
            for j in range(path_count.value):
                if i != j:
                    other_path = path_array[j]
                    if (
                        path.sourceInfo.adapterId.LowPart
                        == other_path.sourceInfo.adapterId.LowPart
                        and path.sourceInfo.id == other_path.sourceInfo.id
                    ):
                        # Same source, different targets - this indicates cloning
                        return True, None

        return False, None

    except Exception:
        return False, None
