import os

# Playwright's official PyInstaller guidance uses this value when the browser
# binaries are installed with PLAYWRIGHT_BROWSERS_PATH=0 before packaging.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
