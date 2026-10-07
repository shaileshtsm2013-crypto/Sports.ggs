"""Sports Analyzer AI - Desktop Launcher Executable Entry Point."""
import os
import sys
import webbrowser
import threading
import time
import uvicorn

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.main import app
from backend.app.core.config import settings

def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{settings.PORT}/app")

def main():
    print("=" * 60)
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} Desktop Engine...")
    print(f"Local Server: http://127.0.0.1:{settings.PORT}")
    print(f"Web Dashboard: http://127.0.0.1:{settings.PORT}/app")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=settings.PORT, log_level="info")

if __name__ == "__main__":
    main()
