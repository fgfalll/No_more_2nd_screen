"""
Build script to create the executable using PyInstaller.
"""

import PyInstaller.__main__
import os
import shutil

# Cleanup function to remove build artifacts
def cleanup():
    artifacts = ['__pycache__', 'build', '.ruff_cache', '.idea', 'NoMore2ndScreen.spec']
    for artifact in artifacts:
        if os.path.exists(artifact):
            if os.path.isdir(artifact):
                shutil.rmtree(artifact)
                print(f"Removed: {artifact}/")
            else:
                os.remove(artifact)
                print(f"Removed: {artifact}")

    # Clean __pycache__ in subdirectories
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"Removed: {pycache_path}")

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

# Cleanup build artifacts
print("\nCleaning up build artifacts...")
cleanup()
print("\nCleanup complete! Only dist/ folder remains.")
