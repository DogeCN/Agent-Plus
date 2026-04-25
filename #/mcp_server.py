from src.utils import describe_control, run_blocking, validate_loc
from src.desktop.service import Desktop
from typing import List, Literal, Optional, Tuple, Dict, Any
from contextlib import asynccontextmanager
from humancursor import SystemCursor
from markdownify import markdownify
from fastmcp import FastMCP
import pyautogui as pg
import pyperclip as pc
import requests
import threading
import fnmatch
import ctypes
import json
import os


def log(message: str):
    print(f"[MCP Server] {message}")


DEFAULT_PAUSE = 1.0
pg.FAILSAFE = False
pg.PAUSE = DEFAULT_PAUSE
ctypes.windll.user32.SetProcessDPIAware()

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")


def _load_memory() -> Dict[str, Any]:
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_memory(data: Dict[str, Any]) -> None:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class WatchCursor:
    """Background thread that monitors cursor position."""

    def __init__(self):
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self.position: Tuple[int, int] = (0, 0)

    def _watch(self) -> None:
        """Watch cursor position in background thread."""
        import time

        ctypes.windll.ole32.CoInitialize(None)
        try:
            while self._running:
                self.position = pg.position()
                time.sleep(0.05)
        finally:
            ctypes.windll.ole32.CoUninitialize()

    def start(self) -> None:
        """Start the cursor watcher."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._watch, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the cursor watcher."""
        self._running = False
        th = self._thread
        if th and th.is_alive():
            th.join(timeout=1)


desktop = Desktop()
cursor = SystemCursor()
watch_cursor = WatchCursor()


def cursor_move_to(loc: Tuple[int, int]) -> None:
    """Unified cursor movement with fallback to pyautogui."""
    try:
        cursor.move_to(loc[0], loc[1])
    except Exception:
        pg.moveTo(loc[0], loc[1])


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    """Manage cursor watcher lifespan."""
    watch_cursor.start()
    try:
        yield
    finally:
        watch_cursor.stop()


mcp = FastMCP(name="windows-mcp", lifespan=lifespan)


@mcp.tool
def launch(name: str) -> str:
    """Launch an application by name.
    Args:
        name: Application name (case-insensitive partial matching supported)
    Returns:
        Success/failure message with application name
    """
    if not name or not name.strip():
        return "Error: Application name cannot be empty."
    try:
        name, status = desktop.launch_app(name.strip())
        if status != 0:
            return f"Failed to launch {name.title()}. Make sure the application exists."
        return f"Launched {name.title()}."
    except Exception as e:
        return f"Error launching {name.title()}: {str(e)}"


@mcp.tool
def state(use_vision: bool = False) -> str:
    """Capture current desktop state including applications and UI elements.
    Args:
        use_vision: If True, run OCR to capture visible text.
    Returns:
        Structured desktop state with focused app, opened apps, interactive elements, and OCR results.
    """
    try:
        result = desktop.get_state(use_vision=use_vision)
        return str(result)
    except Exception as e:
        return f"Error capturing state: {str(e)}"


@mcp.tool
def click(x: int, y: int, button: str = "left") -> str:
    """Click on a UI element at specified coordinates.
    Args:
        x: X coordinate (absolute screen position)
        y: Y coordinate (absolute screen position)
        button: Mouse button to click (left, right, middle)
    Returns:
        Success/failure message
    """
    try:
        cursor_move_to((x, y))
        pg.click(button=button)
        return f"Clicked at ({x}, {y}) with {button} button."
    except Exception as e:
        return f"Error clicking at ({x}, {y}): {str(e)}"


@mcp.tool
def clipboard(mode: Literal["copy", "paste"], text: Optional[str] = None) -> str:
    """Copy text to clipboard or retrieve current clipboard content.
    Args:
        mode: "copy" to save text, "paste" to retrieve
        text: Text content to copy (required for copy mode)
    Returns:
        Status message or clipboard content
    """
    try:
        if mode == "copy":
            if text:
                pc.copy(text)
                return f'Copied "{text}" to clipboard'
            return "Error: No text provided to copy"
        elif mode == "paste":
            content = pc.paste()
            return f'Clipboard Content: "{content}"'
        return 'Error: Invalid mode. Use "copy" or "paste".'
    except Exception as e:
        return f"Error with clipboard operation: {str(e)}"


@mcp.tool
def type(text: str, clear: bool = False) -> str:
    """Type text into the current focused element.
    Args:
        text: Text to type, ASCII only, no newlines.
        clear: If True, clear existing text first
    Returns:
        Success/failure message
    """
    if not text:
        return "Error: Text cannot be empty."
    if not text.isascii() or "\n" in text:
        return "Error: Text must be ASCII and cannot contain newlines, use clipboard instead."
    try:
        if clear:
            pg.hotkey("ctrl", "a")
        pg.write(text)
        return f"Typed: {text}"
    except Exception as e:
        return f"Error typing text: {str(e)}"


@mcp.tool
def switch(name: str) -> str:
    """Switch to a specific application window.
    Args:
        name: Name of the application to switch to
    Returns:
        Status message indicating success or failure
    """
    if not name or not name.strip():
        return "Error: Application name cannot be empty."
    try:
        _, status = desktop.switch_app(name.strip())
        if status != 0:
            return f"Failed to switch to {name.title()} window. Make sure the application is running."
        return f"Switched to {name.title()} window."
    except Exception as e:
        return f"Error switching to {name.title()}: {str(e)}"


@mcp.tool
def scroll(amount: int = 5) -> str:
    """Scroll the current window.
    Args:
        amount: Number of scroll clicks (positive for forward, negative for backward)
    Returns:
        Success/failure message
    """
    try:
        pg.scroll(amount)
        return f"Scrolled by {amount} clicks."
    except Exception as e:
        return f"Error scrolling: {str(e)}"


@mcp.tool
def listdir(path: str = ".") -> str:
    """List files and directories in a directory.
    Args:
        path: Directory path (default: current directory)
    Returns:
        List of files and directories
    """
    try:
        entries = os.listdir(path)
        result = []
        for entry in entries:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result.append(f"[DIR] {entry}")
            else:
                result.append(f"[FILE] {entry}")
        return f"Contents of {path}:\n" + "\n".join(result[:20])
    except Exception as e:
        return f"Error listing files and directories: {str(e)}"


@mcp.tool
def save_file(path: str, content: str, mode: str = "w") -> str:
    """Save content to a file.
    Args:
        path: File path to save
        content: Content to save
        mode: File mode ("w" for write, "a" for append)
    Returns:
        Success/failure message
    """
    import os

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode, encoding="utf-8") as f:
            if mode == "a":
                f.write("\n")
            f.write(content)
        return f"Saved to: {path}"
    except Exception as e:
        return f"Error saving file: {str(e)}"


@mcp.tool
def read_file(path: str, limit: int = 100, encoding: str = "utf-8") -> str:
    """Read content from a file.
    Args:
        path: File path to read
        limit: Maximum lines to return
        encoding: File encoding
    Returns:
        File content or error message
    """
    import os

    if not os.path.exists(path):
        return f"Error: File '{path}' does not exist."
    if not os.path.isfile(path):
        return f"Error: '{path}' is not a file."
    try:
        with open(path, "r", encoding=encoding) as f:
            content = f.readlines()
        if len(content) > limit:
            content = content[:limit]
        return f"Content of {path}:\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool
def delete_file(path: str) -> str:
    """Delete a file.
    Args:
        path: File path to delete
    Returns:
        Success/failure message
    """
    import os

    if not os.path.exists(path):
        return f"Error: File '{path}' does not exist."
    if not os.path.isfile(path):
        return f"Error: '{path}' is not a file."
    try:
        os.remove(path)
        return f"Deleted file: {path}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


@mcp.tool
def copy_file(src: str, dst: str) -> str:
    """Copy a file from source to destination.
    Args:
        src: Source file path
        dst: Destination file path
    Returns:
        Success/failure message
    """
    import shutil
    import os

    if not os.path.exists(src):
        return f"Error: Source file '{src}' does not exist."
    if not os.path.isfile(src):
        return f"Error: '{src}' is not a file."
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return f"Copied '{src}' to '{dst}'"
    except Exception as e:
        return f"Error copying file: {str(e)}"


@mcp.tool
def move_file(src: str, dst: str) -> str:
    """Move/rename a file from source to destination.
    Args:
        src: Source file path
        dst: Destination file path
    Returns:
        Success/failure message
    """
    import shutil
    import os

    if not os.path.exists(src):
        return f"Error: Source file '{src}' does not exist."
    if not os.path.isfile(src):
        return f"Error: '{src}' is not a file."
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        return f"Moved '{src}' to '{dst}'"
    except Exception as e:
        return f"Error moving file: {str(e)}"


@mcp.tool
def create_dir(path: str) -> str:
    """Create a directory.
    Args:
        path: Directory path to create
    Returns:
        Success/failure message
    """
    import os

    try:
        os.makedirs(path, exist_ok=True)
        return f"Created directory: {path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"


@mcp.tool
def delete_dir(path: str, recursive: bool = False) -> str:
    """Delete a directory.
    Args:
        path: Directory path to delete
        recursive: If True, delete directory and all contents
    Returns:
        Success/failure message
    """
    import os
    import shutil

    if not os.path.exists(path):
        return f"Error: Directory '{path}' does not exist."
    if not os.path.isdir(path):
        return f"Error: '{path}' is not a directory."
    try:
        if recursive:
            shutil.rmtree(path)
            return f"Deleted directory recursively: {path}"
        else:
            os.rmdir(path)
            return f"Deleted empty directory: {path}"
    except OSError as e:
        return f"Error deleting directory: {str(e)}. Directory may not be empty. Use recursive=True to delete with contents."
    except Exception as e:
        return f"Error deleting directory: {str(e)}"


@mcp.tool
def file_exists(path: str) -> str:
    """Check if a file or directory exists.
    Args:
        path: Path to check
    Returns:
        Existence status and type
    """
    import os

    if not os.path.exists(path):
        return f"'{path}' does not exist."
    if os.path.isfile(path):
        return f"'{path}' exists and is a file."
    if os.path.isdir(path):
        return f"'{path}' exists and is a directory."
    return f"'{path}' exists (unknown type)."


@mcp.tool
def get_file_info(path: str) -> str:
    """Get detailed information about a file or directory.
    Args:
        path: Path to query
    Returns:
        File/directory information
    """
    import os
    from datetime import datetime

    if not os.path.exists(path):
        return f"Error: '{path}' does not exist."
    try:
        stat_info = os.stat(path)
        is_file = os.path.isfile(path)
        is_dir = os.path.isdir(path)

        size = stat_info.st_size
        size_str = f"{size} bytes"
        if size > 1024:
            size_str = f"{size / 1024:.2f} KB"
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.2f} MB"

        mtime = datetime.fromtimestamp(stat_info.st_mtime)
        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")

        result = f"Path: {path}\n"
        result += f"Type: {'File' if is_file else 'Directory'}\n"
        result += f"Size: {size_str}\n"
        result += f"Modified: {mtime_str}\n"

        if is_dir:
            try:
                items = os.listdir(path)
                result += f"Items: {len(items)}\n"
            except Exception:
                pass

        return result
    except Exception as e:
        return f"Error getting file info: {str(e)}"


@mcp.tool
def run_command(command: str) -> str:
    """Run a command in terminal.
    Args:
        command: Command to run
    Returns:
        Command output
    """
    import subprocess

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return f"Status: {result.returncode}\nOutput:\n{result.stdout}\nError:\n{result.stderr}"
    except Exception as e:
        return f"Error running command: {str(e)}"


@mcp.tool
def powershell(command: str) -> str:
    """Execute PowerShell commands.
    Args:
        command: PowerShell command to execute
    Returns:
        Command output
    """
    if not command or not command.strip():
        return "Error: Command cannot be empty."
    try:

        def _exec():
            return desktop.execute_command(command.strip())

        response, status = run_blocking(_exec)
        return f"Status Code: {status}\nResponse: {response}"
    except Exception as e:
        return f"Error executing PowerShell command: {str(e)}"


@mcp.tool
def drag(from_loc: Tuple[int, int], to_loc: Tuple[int, int]) -> str:
    """Drag from source coordinates and drop at destination.
    Args:
        from_loc: Starting coordinates (x, y)
        to_loc: Ending coordinates (x, y)
    Returns:
        Confirmation message with element description
    """
    ok1, msg1 = validate_loc(from_loc)
    ok2, msg2 = validate_loc(to_loc)
    if not ok1:
        return f"Error for from_loc: {msg1}"
    if not ok2:
        return f"Error for to_loc: {msg2}"
    try:
        control = desktop.get_element_under_cursor()
        x1, y1 = int(from_loc[0]), int(from_loc[1])
        x2, y2 = int(to_loc[0]), int(to_loc[1])
        cursor.drag_and_drop((x1, y1), (x2, y2))
        return (
            f"Dragged the {describe_control(control)} from ({x1},{y1}) to ({x2},{y2})."
        )
    except Exception as e:
        return f"Error dragging from {from_loc} to {to_loc}: {str(e)}"


@mcp.tool
def move(to_loc: Tuple[int, int]) -> str:
    """Move mouse to specified coordinates without clicking.
    Args:
        to_loc: Target coordinates (x, y)
    Returns:
        Confirmation message with new position
    """
    ok, msg = validate_loc(to_loc)
    if not ok:
        return f"Error: {msg}"
    try:
        x, y = int(to_loc[0]), int(to_loc[1])
        cursor_move_to((x, y))
        return f"Moved the mouse pointer to ({x},{y})."
    except Exception as e:
        return f"Error moving to {to_loc}: {str(e)}"


@mcp.tool
def shortcut(shortcut: List[str]) -> str:
    """Execute a keyboard shortcut.
    Args:
        shortcut: List of keys to press in sequence
    Returns:
        Confirmation message with pressed keys
    """
    if not shortcut:
        return "Error: Provide shortcut as a list of keys (e.g., ['ctrl', 'c'])."
    try:
        pg.hotkey(*shortcut)
        return f'Pressed {"+".join(shortcut)}.'
    except Exception as e:
        return f"Error executing shortcut {shortcut}: {str(e)}"


@mcp.tool
def key(key: str = "") -> str:
    """Press a single keyboard key.
    Args:
        key: Name of the key to press
    Returns:
        Confirmation message with pressed key
    """
    if not key or not key.strip():
        return "Error: Key cannot be empty."
    try:
        pg.press(key.strip())
        return f"Pressed the key {key}."
    except Exception as e:
        return f"Error pressing key {key}: {str(e)}"


@mcp.tool
def wait(duration: int) -> str:
    """Wait for a specified duration.
    Args:
        duration: Number of seconds to wait
    Returns:
        Confirmation message with duration
    """
    if duration <= 0:
        return "Error: Duration must be positive."
    try:
        pg.sleep(duration)
        return f"Waited for {duration} seconds."
    except Exception as e:
        return f"Error waiting: {str(e)}"


@mcp.tool
def scrape(url: str) -> str:
    """Scrape webpage content and convert to markdown.
    Args:
        url: Complete URL with protocol
    Returns:
        Markdown formatted webpage content
    """
    if not url or not url.strip():
        return "Error: URL cannot be empty."
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return "Error: URL must include protocol (http:// or https://)"
    try:

        def _get():
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.text

        text = run_blocking(_get, timeout=20)
        content = markdownify(html=text)
        # Limit size of returned content to avoid huge payloads
        if len(content) > 20000:
            content = content[:20000] + "\n\n[truncated]"
        return f"Scraped the contents of the webpage:\n{content}"
    except requests.exceptions.Timeout:
        return f"Error: Timeout while accessing {url}"
    except requests.exceptions.RequestException as e:
        return f"Error scraping {url}: {str(e)}"
    except Exception as e:
        return f"Error processing webpage content: {str(e)}"


@mcp.tool
def memory_store(key: str, value: str) -> str:
    """Store a memory (key-value pair).
    Args:
        key: Memory key
        value: Memory value
    Returns:
        Success/failure message
    """
    if not key or not key.strip():
        return "Error: key cannot be empty."
    mem = _load_memory()
    mem[key.strip()] = value.strip()
    _save_memory(mem)
    return f"Stored memory: {key}"


@mcp.tool
def memory_append(key: str, value: str) -> str:
    """Append a new line to an existing memory.
    Args:
        key: Memory key
        value: New line to append
    Returns:
        Success/failure message
    """
    if not key or not key.strip():
        return "Error: key cannot be empty."
    mem = _load_memory()
    existing = mem.get(key.strip(), "")
    if existing:
        mem[key.strip()] = existing + "\n" + value.strip()
    else:
        mem[key.strip()] = value.strip()
    _save_memory(mem)
    return f"Appended to memory: {key}"


@mcp.tool
def memory_retrieve(key: str) -> str:
    """Retrieve a memory by exact key.
    Args:
        key: Memory key to retrieve
    Returns:
        Memory value or error message
    """
    if not key or not key.strip():
        return "Error: key cannot be empty."
    mem = _load_memory()
    value = mem.get(key.strip())
    if value is None:
        return f"No memory found for key '{key}'."
    return f"{key}: {value}"


@mcp.tool
def memory_search(query: str, limit: int = 10) -> str:
    """Search memories by keyword.
    Args:
        query: Search query
        limit: Maximum number of results to return
    Returns:
        Search results or error message
    """
    if not query or not query.strip():
        return "Error: search query cannot be empty."
    mem = _load_memory()
    if not mem:
        return "No memories stored."
    query = query.strip().lower()
    results = []
    for k, v in mem.items():
        if query in k.lower():
            results.append(f"{k}: {v}")
    results.sort(reverse=True)
    results = results[:limit]
    if not results:
        return f"No memories matching '{query}'."
    result_text = "Search results:\n"
    for item in results:
        result_text += f"{item}\n"
    return result_text.strip()


@mcp.tool
def memory_list(limit: int = 20, offset: int = 0) -> str:
    """List all memory keys with pagination.
    Args:
        limit: Maximum number of keys to return
        offset: Starting offset for pagination
    Returns:
        List of memory keys or error message
    """
    mem = _load_memory()
    if not mem:
        return "No memories stored."
    keys = list(mem.keys())
    total = len(keys)
    if offset >= total:
        return f"Offset {offset} exceeds total keys ({total})."
    end = min(offset + limit, total)
    page_keys = keys[offset:end]
    result = f"Memory keys (total {total}, showing {offset+1}-{end}):\n"
    result += ", ".join(page_keys)
    return result


@mcp.tool
def memory_delete(key: str) -> str:
    """Delete a memory by key.
    Args:
        key: Memory key to delete
    Returns:
        Success/failure message
    """
    if not key or not key.strip():
        return "Error: key cannot be empty."
    mem = _load_memory()
    if key.strip() not in mem:
        return f"No memory found for key '{key}'."
    del mem[key.strip()]
    _save_memory(mem)
    return f"Deleted memory: {key}"


if __name__ == "__main__":
    mcp.run()
