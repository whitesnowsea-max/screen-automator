"""Main application window using PyQt6."""
import sys
import platform
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QTextEdit, QLineEdit,
    QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.task import Task, TaskType, ActionType, TaskManager, MixGroup, ConditionType
from core.monitor import MonitorEngine
from gui.task_dialog import TaskDialog
from gui.mix_dialog import MixGroupDialog

from core.updater import check_update_async, download_and_apply_async, UpdateInfo

# Import version and config
try:
    from version_info import VERSION, GITHUB_REPO
except ImportError:
    VERSION = "unknown"
    GITHUB_REPO = ""


# Platform-specific settings
_IS_WINDOWS = platform.system() == "Windows"
_MONO_FONT = "Consolas" if _IS_WINDOWS else "Menlo"
_MOD_KEY_LABEL = "Ctrl" if _IS_WINDOWS else "Cmd"

MAIN_STYLE = f"""
    /* ── Base ── */
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0d0d1a, stop:0.5 #131328, stop:1 #0a1628);
    }}
    QWidget {{
        background: transparent;
        color: #e8e8f0;
        font-family: '{_MONO_FONT}', 'Segoe UI', system-ui;
    }}
    QLabel {{
        color: #e8e8f0;
        background: transparent;
    }}

    /* ── Glass panels ── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: rgba(255,255,255,0.03);
        width: 8px;
        border-radius: 4px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255,255,255,0.15);
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(255,255,255,0.25);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ── Text inputs ── */
    QTextEdit {{
        background: rgba(255, 255, 255, 0.04);
        color: #c8c8e0;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px;
        font-family: '{_MONO_FONT}';
        font-size: 12px;
        selection-background-color: rgba(124, 58, 237, 0.4);
    }}
    QLineEdit {{
        background: rgba(255, 255, 255, 0.06);
        color: #e8e8f0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
        selection-background-color: rgba(124, 58, 237, 0.4);
    }}
    QLineEdit:focus {{
        border: 1px solid rgba(124, 58, 237, 0.6);
    }}
"""


class TaskCard(QFrame):
    """Card widget for a single task — glassmorphism style."""

    def __init__(self, task: Task, parent_app):
        super().__init__()
        self.task = task
        self.app = parent_app

        # Glass card with subtle border glow
        border_color = "rgba(100, 220, 140, 0.3)" if self.task.enabled else "rgba(255,255,255,0.06)"
        bg_alpha = "0.08" if self.task.enabled else "0.04"
        self.setStyleSheet(f"""
            TaskCard {{
                background: rgba(255, 255, 255, {bg_alpha});
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        self.setFixedHeight(76)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 14, 10)
        layout.setSpacing(10)

        # Left accent bar
        accent = QFrame()
        accent_color = "#34d399" if self.task.enabled else "#4a4a6a"
        accent.setFixedSize(3, 40)
        accent.setStyleSheet(f"background: {accent_color}; border-radius: 2px;")
        layout.addWidget(accent)

        # Info section
        left = QVBoxLayout()
        left.setSpacing(3)
        type_emoji = "🖼️" if self.task.task_type == TaskType.IMAGE else "📝"
        name_color = "#f0f0ff" if self.task.enabled else "#777790"

        title = QLabel(f"{type_emoji} {self.task.name}")
        title.setStyleSheet(f"""
            font-size: 14px; font-weight: 600; color: {name_color};
            background: transparent;
        """)
        left.addWidget(title)

        if self.task.task_type == TaskType.IMAGE:
            detail = f"이미지 매칭 · 신뢰도 {self.task.confidence:.0%}"
        else:
            detail = f'텍스트: "{self.task.search_text}"'
        action_names = {"click": "클릭", "double_click": "더블클릭", "right_click": "우클릭"}
        detail += f"  →  {action_names.get(self.task.action.value, self.task.action.value)}"
        detail += f"  ·  {self.task.cooldown:.1f}초"
        if self.task.search_region:
            detail += "  · 📐"
        if self.task.auto_scroll:
            detail += "  · 🔄"
        if self.task.type_text:
            detail += "  · ⌨️"

        detail_label = QLabel(detail)
        detail_label.setStyleSheet("font-size: 11px; color: #7a7a9a; background: transparent;")
        left.addWidget(detail_label)
        layout.addLayout(left, stretch=1)

        # Pill buttons
        def make_btn(text, gradient_start, gradient_end, width=52):
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {gradient_start}, stop:1 {gradient_end});
                    color: white; border: none; border-radius: 10px;
                    padding: 5px 0px; font-size: 11px; font-weight: 500;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {gradient_end}, stop:1 {gradient_start});
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(width, 26)
            return btn

        toggle_text = "비활성" if self.task.enabled else "활성"
        if self.task.enabled:
            toggle_btn = make_btn(toggle_text, "#e67e22", "#d35400", 55)
        else:
            toggle_btn = make_btn(toggle_text, "#22c55e", "#16a34a", 55)
        toggle_btn.clicked.connect(lambda: self.app._toggle_task(self.task.id))
        layout.addWidget(toggle_btn)

        edit_btn = make_btn("수정", "#6366f1", "#4f46e5", 48)
        edit_btn.clicked.connect(lambda: self.app._edit_task(self.task))
        layout.addWidget(edit_btn)

        del_btn = make_btn("삭제", "#ef4444", "#dc2626", 48)
        del_btn.clicked.connect(lambda: self.app._delete_task(self.task.id))
        layout.addWidget(del_btn)


class MixGroupCard(QFrame):
    """Card widget for a MixGroup — distinct glass style."""

    def __init__(self, group: MixGroup, parent_app):
        super().__init__()
        self.group = group
        self.app = parent_app

        border_color = "rgba(139, 92, 246, 0.35)" if group.enabled else "rgba(255,255,255,0.06)"
        bg_alpha = "0.08" if group.enabled else "0.04"
        self.setStyleSheet(f"""
            MixGroupCard {{
                background: rgba(139, 92, 246, {bg_alpha});
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        self.setFixedHeight(76)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 14, 10)
        layout.setSpacing(10)

        # Left accent bar (purple for mix)
        accent = QFrame()
        accent_color = "#8b5cf6" if self.group.enabled else "#4a4a6a"
        accent.setFixedSize(3, 40)
        accent.setStyleSheet(f"background: {accent_color}; border-radius: 2px;")
        layout.addWidget(accent)

        # Info section
        left = QVBoxLayout()
        left.setSpacing(3)
        cond_badge = "AND" if self.group.condition == ConditionType.AND else "OR"
        name_color = "#f0f0ff" if self.group.enabled else "#777790"

        title = QLabel(f"🔀 {self.group.name}  [{cond_badge}]")
        title.setStyleSheet(f"""
            font-size: 14px; font-weight: 600; color: {name_color};
            background: transparent;
        """)
        left.addWidget(title)

        # Show included task names
        task_names = []
        for tid in self.group.task_ids:
            t = self.app.task_manager.get_task(tid)
            if t:
                task_names.append(t.name)
        detail = " · ".join(task_names) if task_names else "작업 없음"
        action_names = {"click": "클릭", "double_click": "더블클릭", "right_click": "우클릭"}
        detail += f"  →  {action_names.get(self.group.action.value, self.group.action.value)}"

        detail_label = QLabel(detail)
        detail_label.setStyleSheet("font-size: 11px; color: #8a7ab8; background: transparent;")
        left.addWidget(detail_label)
        layout.addLayout(left, stretch=1)

        # Pill buttons
        def make_btn(text, gs, ge, width=52):
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {gs}, stop:1 {ge});
                    color: white; border: none; border-radius: 10px;
                    padding: 5px 0px; font-size: 11px; font-weight: 500;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {ge}, stop:1 {gs});
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(width, 26)
            return btn

        toggle_text = "비활성" if self.group.enabled else "활성"
        if self.group.enabled:
            toggle_btn = make_btn(toggle_text, "#e67e22", "#d35400", 55)
        else:
            toggle_btn = make_btn(toggle_text, "#22c55e", "#16a34a", 55)
        toggle_btn.clicked.connect(lambda: self.app._toggle_mix_group(self.group.id))
        layout.addWidget(toggle_btn)

        edit_btn = make_btn("수정", "#8b5cf6", "#7c3aed", 48)
        edit_btn.clicked.connect(lambda: self.app._edit_mix_group(self.group))
        layout.addWidget(edit_btn)

        del_btn = make_btn("삭제", "#ef4444", "#dc2626", 48)
        del_btn.clicked.connect(lambda: self.app._delete_mix_group(self.group.id))
        layout.addWidget(del_btn)


class ScreenAutomatorApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"🖱️ Screen Automator v{VERSION} — 화면 자동화")
        self.setMinimumSize(700, 650)
        self.resize(750, 700)
        self.setStyleSheet(MAIN_STYLE)

        # Data
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "tasks.json"
        )
        self.task_manager = TaskManager(config_path=config_path)
        self.task_manager.load()

        self.monitor = MonitorEngine(
            task_manager=self.task_manager,
            interval=1.0,
            log_callback=self._append_log,
        )

        self._pending_update: UpdateInfo | None = None

        self._build_ui()
        self._refresh_task_list()
        self._setup_hotkey()
        self._check_for_updates()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Glass Header ──
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(124, 58, 237, 0.15),
                    stop:0.5 rgba(99, 102, 241, 0.1),
                    stop:1 rgba(59, 130, 246, 0.15));
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("⚡ Screen Automator")
        title.setFont(QFont("Segoe UI" if _IS_WINDOWS else "SF Pro Display", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #f0f0ff; background: transparent;")
        h_layout.addWidget(title)

        ver_label = QLabel(f"v{VERSION}")
        ver_label.setStyleSheet("""
            color: rgba(255,255,255,0.35); font-size: 11px; background: transparent;
            margin-left: 6px; margin-top: 6px;
        """)
        h_layout.addWidget(ver_label)
        h_layout.addStretch()

        # Update button
        self.update_btn = QPushButton("🔄 업데이트 확인")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06); color: #8888aa;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 5px 12px; font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1); color: #b0b0d0;
            }
        """)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(self._on_update_btn_clicked)
        h_layout.addWidget(self.update_btn)

        self.status_label = QLabel("⏹ 정지됨")
        self.status_label.setStyleSheet("""
            color: rgba(255, 107, 107, 0.9); font-size: 13px; font-weight: 500;
            background: rgba(255, 107, 107, 0.08);
            border: 1px solid rgba(255, 107, 107, 0.15);
            border-radius: 12px; padding: 4px 14px;
        """)
        h_layout.addWidget(self.status_label)
        main_layout.addWidget(header)

        # ── Controls ──
        controls = QFrame()
        controls.setStyleSheet("background: transparent;")
        c_layout = QHBoxLayout(controls)
        c_layout.setContentsMargins(20, 14, 20, 8)
        c_layout.setSpacing(10)

        self.start_btn = QPushButton("▶  시작")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #22c55e, stop:1 #16a34a);
                color: white; border: none; border-radius: 12px;
                padding: 11px 24px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
            }
        """)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._toggle_monitor)
        c_layout.addWidget(self.start_btn)

        add_btn = QPushButton("＋  작업 추가")
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:1 #6d28d9);
                color: white; border: none; border-radius: 12px;
                padding: 11px 20px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6d28d9, stop:1 #5b21b6);
            }
        """)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_task)
        c_layout.addWidget(add_btn)

        mix_btn = QPushButton("🔀  믹스 추가")
        mix_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8b5cf6, stop:1 #6366f1);
                color: white; border: none; border-radius: 12px;
                padding: 11px 20px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366f1, stop:1 #4f46e5);
            }
        """)
        mix_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mix_btn.clicked.connect(self._add_mix_group)
        c_layout.addWidget(mix_btn)
        c_layout.addStretch()

        interval_label = QLabel("검사 간격")
        interval_label.setStyleSheet("font-size: 12px; color: #8888aa; background: transparent;")
        c_layout.addWidget(interval_label)
        self.interval_edit = QLineEdit("1.0")
        self.interval_edit.setFixedWidth(50)
        self.interval_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.interval_edit.returnPressed.connect(self._update_interval)
        c_layout.addWidget(self.interval_edit)
        sec_label = QLabel("초")
        sec_label.setStyleSheet("font-size: 12px; color: #8888aa; background: transparent;")
        c_layout.addWidget(sec_label)
        main_layout.addWidget(controls)

        # Shortcut hint
        hint = QLabel(f"⌨  {_MOD_KEY_LABEL}+Shift+S  시작/정지 토글")
        hint.setStyleSheet("""
            color: rgba(255,255,255,0.5); font-size: 12px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px; padding: 5px 12px;
            margin: 0px 20px;
        """)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(hint)

        # ── Section: Task List ──
        task_header = QHBoxLayout()
        task_header.setContentsMargins(24, 12, 24, 4)
        tl = QLabel("등록된 작업")
        tl.setFont(QFont("Segoe UI" if _IS_WINDOWS else "SF Pro Display", 14, QFont.Weight.DemiBold))
        tl.setStyleSheet("color: #c0c0e0; background: transparent;")
        task_header.addWidget(tl)
        self.task_count_label = QLabel("0개")
        self.task_count_label.setStyleSheet("color: #5a5a7a; font-size: 12px; background: transparent;")
        task_header.addWidget(self.task_count_label)
        task_header.addStretch()
        main_layout.addLayout(task_header)

        # Scrollable task list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.task_layout.setContentsMargins(20, 4, 20, 8)
        self.task_layout.setSpacing(6)
        scroll.setWidget(self.task_container)
        main_layout.addWidget(scroll, stretch=1)

        # ── Section: Log ──
        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.06);")
        main_layout.addWidget(sep)

        log_header = QHBoxLayout()
        log_header.setContentsMargins(24, 10, 24, 4)
        ll = QLabel("실행 로그")
        ll.setFont(QFont("Segoe UI" if _IS_WINDOWS else "SF Pro Display", 14, QFont.Weight.DemiBold))
        ll.setStyleSheet("color: #c0c0e0; background: transparent;")
        log_header.addWidget(ll)
        log_header.addStretch()
        clear_btn = QPushButton("지우기")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06); color: #7a7a9a;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 4px 12px; font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #a0a0c0;
            }
        """)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_log)
        log_header.addWidget(clear_btn)
        main_layout.addLayout(log_header)

        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(150)
        main_layout.addWidget(self.log_text)

    def _refresh_task_list(self):
        # Clear existing
        while self.task_layout.count():
            item = self.task_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(self.task_manager.tasks) + len(self.task_manager.mix_groups)
        self.task_count_label.setText(f"{total}개")

        if total == 0:
            empty = QLabel("등록된 작업이 없습니다\n위의 '작업 추가' 또는 '믹스 추가' 버튼을 눌러 시작하세요")
            empty.setStyleSheet("color: #5a5a7a; font-size: 13px; background: transparent; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.task_layout.addWidget(empty)
            return

        # Individual tasks
        for task in self.task_manager.tasks:
            card = TaskCard(task, self)
            self.task_layout.addWidget(card)

        # Mix groups
        for group in self.task_manager.mix_groups:
            card = MixGroupCard(group, self)
            self.task_layout.addWidget(card)

    def _add_task(self):
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        dialog = TaskDialog(self, templates_dir=templates_dir)
        if dialog.exec() and dialog.result_task:
            self.task_manager.add_task(dialog.result_task)
            self._refresh_task_list()
            self._append_log(f"✅ 작업 추가됨: {dialog.result_task.name}")

    def _edit_task(self, task: Task):
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        dialog = TaskDialog(self, templates_dir=templates_dir, task=task)
        if dialog.exec() and dialog.result_task:
            self.task_manager.remove_task(task.id)
            self.task_manager.add_task(dialog.result_task)
            self._refresh_task_list()
            self._append_log(f"✏️ 작업 수정됨: {dialog.result_task.name}")

    def _delete_task(self, task_id: str):
        reply = QMessageBox.question(self, "삭제 확인", "이 작업을 삭제하시겠습니까?")
        if reply == QMessageBox.StandardButton.Yes:
            self.task_manager.remove_task(task_id)
            self._refresh_task_list()
            self._append_log("🗑️ 작업 삭제됨")

    def _toggle_task(self, task_id: str):
        self.task_manager.toggle_task(task_id)
        self._refresh_task_list()

    # ── Mix Group Handlers ──

    def _add_mix_group(self):
        if not self.task_manager.tasks:
            QMessageBox.warning(self, "경고", "먼저 작업을 추가하세요.")
            return
        dialog = MixGroupDialog(self, self.task_manager.tasks)
        if dialog.exec() and dialog.result_group:
            self.task_manager.add_mix_group(dialog.result_group)
            self._refresh_task_list()
            self._append_log(f"🔀 믹스 그룹 추가됨: {dialog.result_group.name}")

    def _edit_mix_group(self, group: MixGroup):
        dialog = MixGroupDialog(self, self.task_manager.tasks, group=group)
        if dialog.exec() and dialog.result_group:
            self.task_manager.remove_mix_group(group.id)
            self.task_manager.add_mix_group(dialog.result_group)
            self._refresh_task_list()
            self._append_log(f"🔀 믹스 그룹 수정됨: {dialog.result_group.name}")

    def _delete_mix_group(self, group_id: str):
        reply = QMessageBox.question(self, "삭제 확인", "이 믹스 그룹을 삭제하시겠습니까?")
        if reply == QMessageBox.StandardButton.Yes:
            self.task_manager.remove_mix_group(group_id)
            self._refresh_task_list()
            self._append_log("🗑️ 믹스 그룹 삭제됨")

    def _toggle_mix_group(self, group_id: str):
        self.task_manager.toggle_mix_group(group_id)
        self._refresh_task_list()

    def _toggle_monitor(self):
        self._update_interval()

        if self.monitor.is_running:
            self.monitor.stop()
            self.start_btn.setText("▶  시작")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #22c55e, stop:1 #16a34a);
                    color: white; border: none; border-radius: 12px;
                    padding: 11px 24px; font-size: 14px; font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #16a34a, stop:1 #15803d);
                }
            """)
            self.status_label.setText("⏹ 정지됨")
            self.status_label.setStyleSheet("""
                color: rgba(255, 107, 107, 0.9); font-size: 13px; font-weight: 500;
                background: rgba(255, 107, 107, 0.08);
                border: 1px solid rgba(255, 107, 107, 0.15);
                border-radius: 12px; padding: 4px 14px;
            """)
        else:
            active = self.task_manager.get_active_tasks()
            if not active:
                QMessageBox.warning(self, "경고", "활성화된 작업이 없습니다.\n작업을 추가하고 활성화하세요.")
                return
            self.monitor.start()
            self.start_btn.setText("⏹  정지")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ef4444, stop:1 #dc2626);
                    color: white; border: none; border-radius: 12px;
                    padding: 11px 24px; font-size: 14px; font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #dc2626, stop:1 #b91c1c);
                }
            """)
            self.status_label.setText("🟢 모니터링 중")
            self.status_label.setStyleSheet("""
                color: rgba(52, 211, 153, 0.95); font-size: 13px; font-weight: 500;
                background: rgba(52, 211, 153, 0.08);
                border: 1px solid rgba(52, 211, 153, 0.2);
                border-radius: 12px; padding: 4px 14px;
            """)

    def _update_interval(self):
        try:
            val = float(self.interval_edit.text())
            self.monitor.set_interval(val)
        except ValueError:
            pass

    def _append_log(self, message: str):
        QTimer.singleShot(0, lambda: self.log_text.append(message))

    def _clear_log(self):
        self.log_text.clear()

    def _setup_hotkey(self):
        try:
            from pynput import keyboard

            def on_activate():
                QTimer.singleShot(0, self._toggle_monitor)

            hotkey_combo = "<ctrl>+<shift>+s" if _IS_WINDOWS else "<cmd>+<shift>+s"
            self._hotkey_listener = keyboard.GlobalHotKeys({
                hotkey_combo: on_activate,
            })
            self._hotkey_listener.start()
        except Exception as e:
            print(f"단축키 등록 실패: {e}")

    # ── Update Methods ──

    def _check_for_updates(self):
        """Check for updates in background on startup."""
        if not GITHUB_REPO or GITHUB_REPO.startswith("OWNER"):
            return
        check_update_async(VERSION, GITHUB_REPO, self._on_update_check_done)

    def _on_update_check_done(self, update_info):
        """Called from background thread when update check completes."""
        if update_info:
            self._pending_update = update_info
            QTimer.singleShot(0, lambda: self._show_update_available(update_info))

    def _show_update_available(self, info: UpdateInfo):
        """Update the button style to indicate new version."""
        self.update_btn.setText(f"🆕 v{info.version} 업데이트")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f59e0b, stop:1 #d97706);
                color: white; border: none; border-radius: 10px;
                padding: 5px 12px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d97706, stop:1 #b45309);
            }
        """)
        self._append_log(f"🆕 새 버전 v{info.version}이 있습니다! 업데이트 버튼을 클릭하세요.")

    def _on_update_btn_clicked(self):
        """Handle update button click."""
        if self._pending_update:
            reply = QMessageBox.question(
                self, "업데이트",
                f"v{self._pending_update.version}으로 업데이트하시겠습니까?\n"
                f"(config, templates 폴더는 유지됩니다)",
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._do_download_update()
        else:
            # Manual check
            if not GITHUB_REPO or GITHUB_REPO.startswith("OWNER"):
                QMessageBox.information(
                    self, "알림",
                    "GitHub 저장소가 설정되지 않았습니다.\n"
                    "main.py의 GITHUB_REPO 값을 설정하세요.",
                )
                return
            self.update_btn.setText("🔄 확인 중...")
            self.update_btn.setEnabled(False)
            check_update_async(VERSION, GITHUB_REPO, self._on_manual_check_done)

    def _on_manual_check_done(self, update_info):
        """Called from background thread after manual check."""
        def _update_ui():
            self.update_btn.setEnabled(True)
            if update_info:
                self._pending_update = update_info
                self._show_update_available(update_info)
            else:
                self.update_btn.setText("✅ 최신 버전")
                self._append_log("✅ 현재 최신 버전입니다.")
                # Reset button after 3 seconds
                QTimer.singleShot(3000, lambda: self.update_btn.setText("🔄 업데이트 확인"))
        QTimer.singleShot(0, _update_ui)

    def _do_download_update(self):
        """Download and apply the pending update."""
        self.update_btn.setText("📥 다운로드 중...")
        self.update_btn.setEnabled(False)

        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self._append_log(msg))

        def on_done(success, message):
            def _update_ui():
                self.update_btn.setEnabled(True)
                if success:
                    self.update_btn.setText("✅ 업데이트 완료")
                    QMessageBox.information(self, "업데이트 완료", message)
                else:
                    self.update_btn.setText("❌ 업데이트 실패")
                    QMessageBox.warning(self, "업데이트 실패", message)
                    QTimer.singleShot(3000, lambda: self.update_btn.setText("🔄 업데이트 확인"))
            QTimer.singleShot(0, _update_ui)

        download_and_apply_async(
            self._pending_update, app_dir,
            callback=on_done,
            progress_callback=on_progress,
        )

    def closeEvent(self, event):
        if self.monitor.is_running:
            self.monitor.stop()
        try:
            if hasattr(self, "_hotkey_listener"):
                self._hotkey_listener.stop()
        except Exception:
            pass
        event.accept()


def run():
    app = QApplication(sys.argv)
    window = ScreenAutomatorApp()
    window.show()
    sys.exit(app.exec())
