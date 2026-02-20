---
description: 'Use when building Python desktop GUI applications with PyWebView, creating cross-platform desktop apps, or bundling Python apps for distribution.'
---

# Python GUI Development (PyWebView)

Best practices for Python desktop applications using PyWebView.

## Core Architecture

**This is a desktop app, not a web app.** The Python backend has full system access.

| Layer | Responsibility |
|-------|----------------|
| **Python** | ALL business logic, storage, I/O, network |
| **Frontend** | Presentation and UI state only |

**Rule**: If it touches filesystem, network, or database → Python.

## Project Structure

```
myapp/
├── main.py                 # PyWebView entry point
├── src/
│   ├── api.py              # JavaScript API class
│   ├── config.py           # Settings (TOML)
│   ├── tasks.py            # Background task manager
│   └── services/           # Business logic
├── web/                    # Frontend (Vite + Vue/React)
│   ├── src/
│   │   ├── main.ts
│   │   └── services/api.ts # TypeScript API wrapper
│   └── dist/               # Production build
├── pyproject.toml
├── Makefile
└── entitlements.plist      # macOS permissions
```

## Main Entry Point

```python
import argparse
import logging
import os
import pwd
import sys
from pathlib import Path

import webview

from src.api import Api

# Resolve home WITHOUT HOME env var (Finder launches don't have it)
_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
_app_dir = _home / ".myapp"
_log_file = _app_dir / "app.log"
_app_dir.mkdir(parents=True, exist_ok=True)

# Detect bundled mode
IS_BUNDLED = getattr(sys, "frozen", False)
APP_DIR = Path(sys._MEIPASS) if IS_BUNDLED else Path(__file__).parent
WEB_DIR = APP_DIR / "web"
VITE_DEV_URL = "http://127.0.0.1:5173"

def configure_logging(dev_mode: bool) -> None:
    handlers: list[logging.Handler] = [
        logging.FileHandler(_log_file, mode="a"),
    ]
    if sys.stdout.isatty():
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.DEBUG if dev_mode else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--debug", "-d", action="store_true")
    args = parser.parse_args()

    configure_logging(args.dev)

    url = VITE_DEV_URL if args.dev else str(WEB_DIR / "dist" / "index.html")

    window = webview.create_window(
        title="My App",
        url=url,
        js_api=Api(),
        width=1200,
        height=800,
    )

    webview.start(debug=args.dev or args.debug, http_server=not args.dev)

if __name__ == "__main__":
    main()
```

## API Class Pattern

```python
"""PyWebView JavaScript API."""
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

class ResultDict(TypedDict):
    success: bool
    data: dict | list | None
    error: str | None

class Api:
    """API exposed to frontend via PyWebView js_api."""

    def log_debug(self, message: str) -> None:
        """Log from frontend to Python log file."""
        logger.info("[Frontend] %s", message)

    def get_items(self) -> list[dict]:
        """Get items from database/config."""
        return [{"id": 1, "name": "Item 1"}]

    def perform_action(self, params: dict) -> ResultDict:
        """Perform action with typed result."""
        try:
            result = do_something(params)
            return {"success": True, "data": result, "error": None}
        except Exception as e:
            logger.warning("Action failed: %s", e)
            return {"success": False, "data": None, "error": str(e)}
```

## TypeScript API Wrapper

```typescript
// web/src/services/api.ts

function getApi() {
  if (!window.pywebview?.api) {
    throw new Error("pywebview not initialized");
  }
  return window.pywebview.api;
}

export async function getItems(): Promise<ItemInfo[]> {
  return getApi().get_items();
}

export function waitForPyWebView(): Promise<void> {
  if (window.pywebview?.api) return Promise.resolve();
  return new Promise((resolve) => {
    const checkApi = () => {
      if (window.pywebview?.api) resolve();
      else setTimeout(checkApi, 10);
    };
    window.addEventListener("pywebviewready", checkApi, { once: true });
  });
}
```

## Desktop App Constraints

**App launches from Finder, NOT terminal:**

| Issue | Solution |
|-------|----------|
| No HOME env var | `pwd.getpwuid(os.getuid()).pw_dir` |
| No TTY/stdin | No `input()`, no interactive prompts |
| No stdout visibility | Log to file, use `logger` not `print()` |
| Different PATH | Use absolute paths |

### SSH Commands (No TTY)

```python
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
ssh_cmd = ["ssh", *SSH_OPTS, "-p", str(port), target, command]
```

## Progress Updates (Python → JavaScript)

```python
import json
import webview

def on_progress(step: int, total: int, message: str) -> None:
    windows = webview.windows
    if not windows:
        return
    data = json.dumps({"step": step, "total": total, "message": message})
    windows[0].evaluate_js(f"window.onProgress?.({data})")
```

## Anti-Patterns

| Anti-Pattern | Why | Do Instead |
|--------------|-----|------------|
| `fetch()` to APIs | CORS, no control | Python `httpx` via js_api |
| localStorage | Web limitation | Python file/SQLite |
| `print()` for logging | No terminal | Use `logger` |
| Rely on HOME env var | Not in Finder | Use `pwd.getpwuid()` |

## macOS Entitlements

```xml
<!-- entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>com.apple.security.network.client</key><true/>
    <key>com.apple.security.network.server</key><true/>
</dict>
</plist>
```

## Development Commands

```makefile
dev:
	cd web && npm run dev &
	uv run python main.py --dev

build:
	cd web && npm run build
	pyinstaller --onedir --windowed --name MyApp main.py
	codesign --force --deep --sign - --entitlements entitlements.plist dist/MyApp.app
```

## Debugging

1. **Check logs**: `~/.myapp/app.log`
2. **Test from Finder**: Double-click .app, not terminal
3. **Frontend logging**: Call `api.log_debug(msg)` to write to Python log
