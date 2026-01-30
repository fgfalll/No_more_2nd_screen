"""
Build script to create the executable using PyInstaller.
"""

import PyInstaller.__main__
import os

# Build the executable with all necessary hidden imports
PyInstaller.__main__.run([
    'main.py',
    '--name=NoMore2ndScreen',
    '--onefile',
    '--noconsole',
    '--windowed',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=win32gui',
    '--hidden-import=win32con',
    '--hidden-import=win32process',
    '--hidden-import=win32api',
    '--hidden-import=psutil',
    '--hidden-import=win32timezone',
    '--collect-all=PySide6',
    '--clean',
])

print("\n" + "="*60)
print("Build complete!")
print("="*60)
print("Executable location: dist/NoMore2ndScreen.exe")
print("\nTo run the app:")
print("  dist/NoMore2ndScreen.exe")
print("="*60)
