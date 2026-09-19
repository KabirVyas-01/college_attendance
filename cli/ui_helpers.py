import os
import sys
import re
from typing import List, Sequence, Any

# Enable ANSI colors on Windows terminal if supported
if os.name == 'nt':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# Regex to strip ANSI escape codes when calculating visual column widths
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def visible_len(s: Any) -> int:
    """Returns the visual length of a string without ANSI color escape codes."""
    return len(ANSI_ESCAPE_RE.sub('', str(s)))

# ANSI Color constants
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def print_header(title: str, subtitle: str = ""):
    """Prints a styled box header banner."""
    width = 76
    print(f"\n{CYAN}{'=' * width}{RESET}")
    print(f"{CYAN}{BOLD}  {title.center(width - 4)}  {RESET}")
    if subtitle:
        print(f"{DIM}  {subtitle.center(width - 4)}  {RESET}")
    print(f"{CYAN}{'=' * width}{RESET}\n")

def print_section(title: str):
    """Prints a subsection title."""
    print(f"\n{BOLD}{YELLOW}--- {title} ---{RESET}")

def print_success(msg: str):
    """Prints a green success message."""
    print(f"{GREEN}[SUCCESS] {msg}{RESET}")

def print_error(msg: str):
    """Prints a red error message."""
    print(f"{RED}[ERROR] {msg}{RESET}")

def print_warning(msg: str):
    """Prints a yellow warning message."""
    print(f"{YELLOW}[WARNING] {msg}{RESET}")

def print_info(msg: str):
    """Prints a cyan info message."""
    print(f"{CYAN}[INFO] {msg}{RESET}")

def render_table(headers: Sequence[str], rows: List[Sequence[Any]]):
    """
    Renders a clean ASCII table with dynamic column sizing, stripping ANSI codes for perfect alignment.
    """
    if not headers:
        return

    # Calculate visible column widths
    col_widths = [visible_len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], visible_len(val))

    # Formatting helper with ANSI-safe padding
    def format_row(values, fill_char=" "):
        parts = []
        for v, w in zip(values, col_widths):
            v_str = str(v)
            pad_size = w - visible_len(v_str)
            parts.append(v_str + (fill_char * max(0, pad_size)))
        return "| " + " | ".join(parts) + " |"

    separator = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"

    print(separator)
    print(f"{BOLD}" + format_row(headers) + f"{RESET}")
    print(separator)
    if not rows:
        total_width = sum(col_widths) + (len(col_widths) - 1) * 3
        empty_msg = "No records found".center(total_width)
        print(f"| {empty_msg} |")
    else:
        for row in rows:
            print(format_row(row))
    print(separator)

def prompt_str(prompt_text: str, default: str = None, allow_empty: bool = False) -> str:
    """Prompts for a string input with optional default value."""
    while True:
        hint = f" [{default}]" if default is not None else ""
        try:
            val = input(f"{BOLD}{prompt_text}{hint}: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return ""
        if not val and default is not None:
            return default
        if not val and not allow_empty:
            print_error("This field cannot be empty. Please try again.")
            continue
        return val

def prompt_int(prompt_text: str, min_val: int = None, max_val: int = None, default: int = None) -> int:
    """Prompts for an integer input with range verification."""
    while True:
        hint = f" [{default}]" if default is not None else ""
        try:
            val_str = input(f"{BOLD}{prompt_text}{hint}: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return None
        if not val_str and default is not None:
            return default
        try:
            val = int(val_str)
            if min_val is not None and val < min_val:
                print_error(f"Value must be at least {min_val}.")
                continue
            if max_val is not None and val > max_val:
                print_error(f"Value must be at most {max_val}.")
                continue
            return val
        except ValueError:
            print_error("Invalid number. Please enter an integer.")

def pause():
    """Prompts the user to press Enter to return."""
    try:
        input(f"\n{DIM}Press Enter to continue...{RESET}")
    except (KeyboardInterrupt, EOFError):
        pass
