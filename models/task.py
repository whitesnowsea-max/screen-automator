"""Task data model for screen automation."""
import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class TaskType(Enum):
    IMAGE = "image"
    TEXT = "text"


class ActionType(Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"


class ConditionType(Enum):
    AND = "and"   # All tasks in group must match
    OR = "or"     # Any task in group matches


@dataclass
class Task:
    """Represents a single automation task."""
    name: str
    task_type: TaskType
    action: ActionType
    # For image mode: path to template image
    template_path: Optional[str] = None
    # For text mode: text to search for
    search_text: Optional[str] = None
    # Confidence threshold for image matching (0.0 - 1.0)
    confidence: float = 0.8
    # Whether this task is active
    enabled: bool = True
    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    # Cooldown in seconds (avoid clicking the same target repeatedly)
    cooldown: float = 3.0
    # Search region: None = fullscreen, (x1, y1, x2, y2) = specific area
    search_region: Optional[tuple[int, int, int, int]] = None
    # Auto-scroll: scroll down and re-search when target not found
    auto_scroll: bool = False
    # Scroll target region: None = same as search_region, (x1, y1, x2, y2) = separate area
    scroll_region: Optional[tuple[int, int, int, int]] = None
    # Maximum number of scroll attempts (prevents infinite loops)
    max_scrolls: int = 10
    # Type text after click: None = no typing
    type_text: Optional[str] = None
    # Delay between click and typing (seconds)
    type_delay: float = 0.5
    # Press Enter after typing
    press_enter: bool = True

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        d = asdict(self)
        d["task_type"] = self.task_type.value
        d["action"] = self.action.value
        # Convert tuples to lists for JSON serialization
        if d["search_region"] is not None:
            d["search_region"] = list(d["search_region"])
        if d["scroll_region"] is not None:
            d["scroll_region"] = list(d["scroll_region"])
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Deserialize from dictionary."""
        data = data.copy()
        data["task_type"] = TaskType(data["task_type"])
        data["action"] = ActionType(data["action"])
        # Handle backward compatibility: add defaults for missing fields
        data.setdefault("search_region", None)
        data.setdefault("auto_scroll", False)
        data.setdefault("scroll_region", None)
        data.setdefault("max_scrolls", 10)
        data.setdefault("type_text", None)
        data.setdefault("type_delay", 0.5)
        data.setdefault("press_enter", True)
        # Convert lists back to tuples
        if data["search_region"] is not None:
            data["search_region"] = tuple(data["search_region"])
        if data["scroll_region"] is not None:
            data["scroll_region"] = tuple(data["scroll_region"])
        return cls(**data)


@dataclass
class MixGroup:
    """A group of tasks evaluated together with AND/OR condition."""
    name: str
    task_ids: list[str]
    condition: ConditionType
    action: ActionType
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cooldown: float = 3.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["condition"] = self.condition.value
        d["action"] = self.action.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MixGroup":
        data = data.copy()
        data["condition"] = ConditionType(data["condition"])
        data["action"] = ActionType(data["action"])
        return cls(**data)


class TaskManager:
    """Manages a collection of tasks and mix groups with persistence."""

    def __init__(self, config_path: str = "config/tasks.json"):
        self.config_path = config_path
        self.tasks: list[Task] = []
        self.mix_groups: list[MixGroup] = []

    def add_task(self, task: Task):
        self.tasks.append(task)
        self.save()

    def remove_task(self, task_id: str):
        self.tasks = [t for t in self.tasks if t.id != task_id]
        # Also remove from any mix groups
        for g in self.mix_groups:
            g.task_ids = [tid for tid in g.task_ids if tid != task_id]
        self.save()

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_active_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.enabled]

    def toggle_task(self, task_id: str):
        task = self.get_task(task_id)
        if task:
            task.enabled = not task.enabled
            self.save()

    # ── Mix Group Methods ──

    def add_mix_group(self, group: MixGroup):
        self.mix_groups.append(group)
        self.save()

    def remove_mix_group(self, group_id: str):
        self.mix_groups = [g for g in self.mix_groups if g.id != group_id]
        self.save()

    def get_mix_group(self, group_id: str) -> Optional[MixGroup]:
        for g in self.mix_groups:
            if g.id == group_id:
                return g
        return None

    def get_active_mix_groups(self) -> list[MixGroup]:
        return [g for g in self.mix_groups if g.enabled]

    def toggle_mix_group(self, group_id: str):
        group = self.get_mix_group(group_id)
        if group:
            group.enabled = not group.enabled
            self.save()

    def save(self):
        """Save tasks and mix groups to JSON file."""
        import os
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        data = {
            "tasks": [t.to_dict() for t in self.tasks],
            "mix_groups": [g.to_dict() for g in self.mix_groups],
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """Load tasks and mix groups from JSON file."""
        import os
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Support both old format (list) and new format (dict)
            if isinstance(data, list):
                # Old format: just a list of tasks
                self.tasks = [Task.from_dict(d) for d in data]
                self.mix_groups = []
            else:
                self.tasks = [Task.from_dict(d) for d in data.get("tasks", [])]
                self.mix_groups = [MixGroup.from_dict(d) for d in data.get("mix_groups", [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.tasks = []
            self.mix_groups = []
