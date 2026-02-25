"""Mouse and keyboard action execution using pyautogui."""
import time
import platform
from typing import Optional

import pyautogui
from models.task import ActionType


# Safety settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Small pause between actions

_IS_WINDOWS = platform.system() == "Windows"


class ActionExecutor:
    """Executes mouse/keyboard actions at specified screen coordinates."""

    def __init__(self):
        self.last_action_time = 0.0

    def execute(
        self,
        action: ActionType,
        x: int,
        y: int,
        pre_delay: float = 0.2,
        type_text: Optional[str] = None,
        type_delay: float = 0.5,
        press_enter: bool = True,
    ):
        """
        Execute a mouse action at the given coordinates,
        optionally followed by text input.

        Args:
            action: Type of action (click, double_click, right_click)
            x: Screen X coordinate
            y: Screen Y coordinate
            pre_delay: Delay in seconds before performing the action
            type_text: Text to type after clicking (None = skip)
            type_delay: Delay between click and typing (seconds)
            press_enter: Whether to press Enter after typing
        """
        if pre_delay > 0:
            time.sleep(pre_delay)

        if action == ActionType.CLICK:
            pyautogui.click(x, y)
        elif action == ActionType.DOUBLE_CLICK:
            pyautogui.doubleClick(x, y)
        elif action == ActionType.RIGHT_CLICK:
            pyautogui.rightClick(x, y)

        # Type text after click (if configured)
        if type_text:
            time.sleep(type_delay)
            self._type_text(type_text)
            if press_enter:
                time.sleep(0.1)
                pyautogui.press("enter")

        self.last_action_time = time.time()

    def _type_text(self, text: str):
        """
        Type text using clipboard paste for full Unicode/Korean support.
        Falls back to pyautogui.write() for pure ASCII text.
        """
        # Check if text is pure ASCII
        try:
            text.encode("ascii")
            is_ascii = True
        except UnicodeEncodeError:
            is_ascii = False

        if is_ascii:
            pyautogui.write(text, interval=0.02)
        else:
            # Use clipboard paste for Korean / Unicode text
            import pyperclip
            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass
            pyperclip.copy(text)
            # Ctrl+V on Windows, Cmd+V on Mac
            if _IS_WINDOWS:
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.hotkey("command", "v")
            time.sleep(0.1)
            # Restore original clipboard
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass

    def move_to(self, x: int, y: int, duration: float = 0.2):
        """Move mouse to coordinates smoothly."""
        pyautogui.moveTo(x, y, duration=duration)
