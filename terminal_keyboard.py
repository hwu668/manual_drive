"""
terminal_keyboard.py — Read single keystrokes from terminal (Linux/macOS).

Supports non-blocking reads via termios + select. Works over SSH.
On unsupported platforms (Windows), raises ImportError.
"""

import logging
import sys

logger = logging.getLogger(__name__)

try:
    import select
    import termios
    import tty

    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False


class TerminalKeyboard:
    """Non-blocking single-character terminal input reader."""

    def __init__(self):
        if not _HAS_TERMIOS:
            raise ImportError(
                "Terminal keyboard not available on this platform. "
                "Use --keyboard-terminal only on Linux/macOS."
            )
        self._fd = sys.stdin.fileno()
        self._old_settings = None
        self._active = False

    def start(self):
        """Switch terminal to raw mode for single-character reads."""
        self._old_settings = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        self._active = True
        logger.info("Terminal keyboard active (raw mode)")

    def read_key(self, timeout: float = 0.0) -> str | None:
        """Read a single character, returning None if no key pressed.

        Args:
            timeout: seconds to wait for input (0 = non-blocking).
        """
        if not self._active:
            return None
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                char = sys.stdin.read(1)
                if char == "\x03":  # Ctrl+C
                    raise KeyboardInterrupt
                return char.lower()
        except (OSError, ValueError):
            pass
        return None

    def stop(self):
        """Restore terminal settings."""
        if self._old_settings is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
            self._old_settings = None
        self._active = False
        logger.info("Terminal keyboard stopped")

    @property
    def available(self) -> bool:
        """Check if terminal keyboard is supported on this platform."""
        return _HAS_TERMIOS
