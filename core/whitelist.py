"""
Whitelist management module.

This module handles loading, saving, and checking the whitelist of allowed applications.
"""

import json
import os
from typing import List, Set
from pathlib import Path


# Default whitelist entries
DEFAULT_WHITELIST = [
    "POWERPNT.EXE",
    "OBS64.EXE",
    "OBS32.EXE"
]


class Whitelist:
    """Manages the application whitelist."""

    def __init__(self, config_path: str = None):
        """
        Initialize the whitelist manager.

        Args:
            config_path: Path to the config.json file. If None, uses default location.
        """
        if config_path is None:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent.parent
            config_path = script_dir / "config.json"

        self.config_path = Path(config_path)
        self._whitelist: Set[str] = set()
        self._custom_whitelist: Set[str] = set()
        self.load()

    def load(self):
        """Load whitelist from config file."""
        if not self.config_path.exists():
            # Create default config if it doesn't exist
            self._whitelist = set(DEFAULT_WHITELIST)
            self._custom_whitelist = set()
            self.save()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self._whitelist = set(config.get('whitelist', DEFAULT_WHITELIST))
            self._custom_whitelist = set(config.get('custom_whitelist', []))

            # Ensure default entries are present
            for entry in DEFAULT_WHITELIST:
                self._whitelist.add(entry)

        except Exception as e:
            print(f"Error loading whitelist: {e}")
            self._whitelist = set(DEFAULT_WHITELIST)
            self._custom_whitelist = set()

    def save(self):
        """Save whitelist to config file."""
        try:
            # Read existing config to preserve other settings
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Update whitelist entries
            config['whitelist'] = list(self._whitelist)
            config['custom_whitelist'] = list(self._custom_whitelist)

            # Write back to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)

        except Exception as e:
            print(f"Error saving whitelist: {e}")

    def is_whitelisted(self, process_name: str) -> bool:
        """
        Check if a process is whitelisted.

        Args:
            process_name: Name of the process (e.g., "POWERPNT.EXE")

        Returns:
            True if the process is whitelisted, False otherwise.
        """
        if not process_name:
            return False

        # Convert to uppercase for case-insensitive comparison
        process_name_upper = process_name.upper().strip()

        return process_name_upper in self._whitelist

    def add(self, process_name: str, custom: bool = True):
        """
        Add a process to the whitelist.

        Args:
            process_name: Name of the process to add
            custom: If True, also add to custom whitelist for UI display
        """
        process_name_upper = process_name.upper().strip()
        self._whitelist.add(process_name_upper)

        if custom:
            self._custom_whitelist.add(process_name_upper)

        self.save()

    def remove(self, process_name: str):
        """
        Remove a process from the whitelist.

        Args:
            process_name: Name of the process to remove
        """
        process_name_upper = process_name.upper().strip()

        # Remove from both sets
        self._whitelist.discard(process_name_upper)
        self._custom_whitelist.discard(process_name_upper)

        self.save()

    def get_all(self) -> List[str]:
        """
        Get all whitelisted processes.

        Returns:
            List of whitelisted process names.
        """
        return sorted(list(self._whitelist))

    def get_custom(self) -> List[str]:
        """
        Get custom whitelisted processes (user-added).

        Returns:
            List of custom whitelisted process names.
        """
        return sorted(list(self._custom_whitelist))

    def get_default(self) -> List[str]:
        """
        Get default whitelisted processes.

        Returns:
            List of default whitelisted process names.
        """
        return DEFAULT_WHITELIST.copy()

    def clear_custom(self):
        """Clear all custom whitelist entries."""
        for entry in self._custom_whitelist:
            self._whitelist.discard(entry)
        self._custom_whitelist.clear()
        self.save()

    def is_default(self, process_name: str) -> bool:
        """
        Check if a process is in the default whitelist.

        Args:
            process_name: Name of the process

        Returns:
            True if the process is a default entry, False otherwise.
        """
        return process_name.upper().strip() in DEFAULT_WHITELIST


# Global whitelist instance
_whitelist_instance = None


def get_whitelist(config_path: str = None) -> Whitelist:
    """
    Get the global whitelist instance.

    Args:
        config_path: Optional path to config file

    Returns:
        Whitelist instance
    """
    global _whitelist_instance

    if _whitelist_instance is None:
        _whitelist_instance = Whitelist(config_path)

    return _whitelist_instance


def reload_whitelist():
    """Reload the whitelist from config file."""
    global _whitelist_instance

    if _whitelist_instance is not None:
        _whitelist_instance.load()
