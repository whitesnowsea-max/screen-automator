"""Screen monitoring engine that runs in a background thread."""
import time
import threading
from datetime import datetime
from typing import Callable, Optional

import pyautogui
from PIL import Image

from core.image_matcher import ImageMatcher
from core.text_recognizer import TextRecognizer
from core.action_executor import ActionExecutor
from models.task import Task, TaskType, TaskManager, MixGroup, ConditionType


class MonitorEngine:
    """
    Continuously monitors the screen for registered targets and
    executes actions when targets are found.
    """

    def __init__(
        self,
        task_manager: TaskManager,
        interval: float = 1.0,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self.task_manager = task_manager
        self.interval = interval
        self.log_callback = log_callback

        self.image_matcher = ImageMatcher()
        self.text_recognizer = TextRecognizer()
        self.action_executor = ActionExecutor()

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Track last action time per task to implement cooldown
        self._last_action: dict[str, float] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def _log(self, message: str):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        if self.log_callback:
            self.log_callback(full_msg)
        print(full_msg)

    def start(self):
        """Start the monitoring loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self._log("🟢 모니터링 시작")

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        self._paused = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._log("🔴 모니터링 중지")

    def pause(self):
        """Pause the monitoring loop."""
        self._paused = True
        self._log("⏸️ 모니터링 일시정지")

    def resume(self):
        """Resume the monitoring loop."""
        self._paused = False
        self._log("▶️ 모니터링 재개")

    def toggle(self):
        """Toggle between start and stop."""
        if self._running:
            self.stop()
        else:
            self.start()

    def set_interval(self, interval: float):
        """Set the monitoring interval in seconds."""
        self.interval = max(0.3, interval)

    def _take_screenshot(self) -> Image.Image:
        """Take a screenshot of the entire screen."""
        return pyautogui.screenshot()

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue

            try:
                screenshot = self._take_screenshot()
                active_tasks = self.task_manager.get_active_tasks()

                for task in active_tasks:
                    if not self._running:
                        break

                    # Check cooldown
                    last_time = self._last_action.get(task.id, 0)
                    if time.time() - last_time < task.cooldown:
                        continue

                    coords = self._find_target(task, screenshot)

                    # Auto-scroll logic: if not found and auto_scroll enabled
                    if coords is None and task.auto_scroll:
                        coords = self._find_with_scroll(task)

                    if coords:
                        x, y = coords
                        self._log(
                            f"✅ '{task.name}' 발견! 위치: ({x}, {y}) → "
                            f"{task.action.value} 실행"
                        )
                        self.action_executor.execute(
                            task.action, x, y,
                            type_text=task.type_text,
                            type_delay=task.type_delay,
                            press_enter=task.press_enter,
                        )
                        self._last_action[task.id] = time.time()

                # Process mix groups
                self._process_mix_groups(screenshot)

            except Exception as e:
                self._log(f"⚠️ 오류: {str(e)}")

            time.sleep(self.interval)

    def _process_mix_groups(self, screenshot: Image.Image):
        """Evaluate active mix groups against the current screenshot."""
        active_groups = self.task_manager.get_active_mix_groups()

        for group in active_groups:
            if not self._running:
                break

            # Check cooldown
            last_time = self._last_action.get(f"mix_{group.id}", 0)
            if time.time() - last_time < group.cooldown:
                continue

            # Resolve child tasks
            child_tasks = []
            for tid in group.task_ids:
                task = self.task_manager.get_task(tid)
                if task:
                    child_tasks.append(task)

            if not child_tasks:
                continue

            # Evaluate condition
            results: list[tuple[Task, Optional[tuple[int, int]]]] = []
            for task in child_tasks:
                coords = self._find_target(task, screenshot)
                results.append((task, coords))

            if group.condition == ConditionType.AND:
                # All must match
                all_found = all(coords is not None for _, coords in results)
                if all_found:
                    # Use first task's coords for the action
                    first_coords = results[0][1]
                    task_names = " + ".join(t.name for t, _ in results)
                    self._log(
                        f"🔀 믹스 AND '{group.name}' 충족! "
                        f"[{task_names}] → {group.action.value}"
                    )
                    self.action_executor.execute(
                        group.action, first_coords[0], first_coords[1],
                    )
                    self._last_action[f"mix_{group.id}"] = time.time()

            elif group.condition == ConditionType.OR:
                # Any match triggers
                for task, coords in results:
                    if coords is not None:
                        self._log(
                            f"🔀 믹스 OR '{group.name}' 충족! "
                            f"'{task.name}' 발견 → {group.action.value}"
                        )
                        self.action_executor.execute(
                            group.action, coords[0], coords[1],
                        )
                        self._last_action[f"mix_{group.id}"] = time.time()
                        break

    def _crop_to_region(
        self, screenshot: Image.Image, region: tuple[int, int, int, int]
    ) -> Image.Image:
        """Crop screenshot to the specified region (x1, y1, x2, y2)."""
        x1, y1, x2, y2 = region
        # Clamp to screenshot bounds
        x1 = max(0, min(x1, screenshot.width))
        y1 = max(0, min(y1, screenshot.height))
        x2 = max(x1, min(x2, screenshot.width))
        y2 = max(y1, min(y2, screenshot.height))
        return screenshot.crop((x1, y1, x2, y2))

    def _find_target(
        self, task: Task, screenshot: Image.Image
    ) -> Optional[tuple[int, int]]:
        """Find the target for a specific task, applying search region if set."""
        # Apply search region crop
        offset_x, offset_y = 0, 0
        search_img = screenshot

        if task.search_region:
            offset_x, offset_y = task.search_region[0], task.search_region[1]
            search_img = self._crop_to_region(screenshot, task.search_region)

        coords = None
        if task.task_type == TaskType.IMAGE:
            if task.template_path:
                coords = self.image_matcher.find_template(
                    search_img, task.template_path, task.confidence
                )
        elif task.task_type == TaskType.TEXT:
            if task.search_text:
                coords = self.text_recognizer.find_text(search_img, task.search_text)

        # Adjust coordinates back to full screen if region was used
        if coords and task.search_region:
            coords = (coords[0] + offset_x, coords[1] + offset_y)

        return coords

    def _find_with_scroll(self, task: Task) -> Optional[tuple[int, int]]:
        """
        Scroll within the target region and re-search after each scroll.
        Returns coordinates if found, None otherwise.
        """
        # Determine scroll target area
        scroll_area = task.scroll_region or task.search_region
        if scroll_area:
            scroll_cx = (scroll_area[0] + scroll_area[2]) // 2
            scroll_cy = (scroll_area[1] + scroll_area[3]) // 2
        else:
            # Default: center of screen
            screen = self._take_screenshot()
            scroll_cx = screen.width // 2
            scroll_cy = screen.height // 2

        self._log(f"🔄 '{task.name}' 자동 스크롤 검색 시작...")

        for i in range(task.max_scrolls):
            if not self._running:
                return None

            # Move mouse to scroll area center and scroll down
            pyautogui.moveTo(scroll_cx, scroll_cy, duration=0.1)
            pyautogui.scroll(-3)  # scroll down
            time.sleep(0.5)  # wait for content to settle

            # Re-capture and search
            new_screenshot = self._take_screenshot()
            coords = self._find_target(task, new_screenshot)
            if coords:
                self._log(f"🔄 스크롤 {i + 1}회 후 발견!")
                return coords

        # Not found after max scrolls — reset scroll to top
        self._log(f"🔄 스크롤 {task.max_scrolls}회 완료, 대상 없음. 맨 위로 리셋.")
        pyautogui.moveTo(scroll_cx, scroll_cy, duration=0.1)
        pyautogui.scroll(task.max_scrolls * 3)  # scroll back up
        return None

