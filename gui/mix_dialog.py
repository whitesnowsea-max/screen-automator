"""Dialog for creating and editing Mix Groups."""
import uuid

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QPushButton, QFrame,
    QMessageBox, QCheckBox, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt

from models.task import Task, TaskType, ActionType, ConditionType, MixGroup


STYLE = """
    QDialog {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0d0d1a, stop:0.5 #131328, stop:1 #0a1628);
    }
    QLabel {
        color: #e8e8f0; font-size: 13px; background: transparent;
    }
    QLineEdit {
        background: rgba(255, 255, 255, 0.06); color: #e8e8f0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px; padding: 10px 14px; font-size: 13px;
    }
    QLineEdit:focus {
        border: 1px solid rgba(124, 58, 237, 0.5);
    }
    QRadioButton {
        color: #c8c8e0; font-size: 12px; spacing: 8px; background: transparent;
    }
    QRadioButton::indicator {
        width: 16px; height: 16px; border-radius: 8px;
        border: 2px solid rgba(255,255,255,0.2); background: transparent;
    }
    QRadioButton::indicator:checked {
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.4,
            stop:0 #7c3aed, stop:1 #6d28d9);
        border: 2px solid rgba(124, 58, 237, 0.6);
    }
    QCheckBox {
        color: #c8c8e0; font-size: 12px; spacing: 8px; background: transparent;
    }
    QPushButton[class="primary"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #22c55e, stop:1 #16a34a);
        color: white; border: none; border-radius: 10px;
        padding: 10px 24px; font-size: 13px; font-weight: 600;
    }
    QPushButton[class="primary"]:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #16a34a, stop:1 #15803d);
    }
    QPushButton[class="secondary"] {
        background: rgba(255,255,255,0.06); color: #a0a0c0;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px; padding: 10px 24px; font-size: 13px;
    }
    QPushButton[class="secondary"]:hover {
        background: rgba(255,255,255,0.1);
    }
"""


class MixGroupDialog(QDialog):
    """Dialog for creating/editing a MixGroup."""

    def __init__(self, parent, tasks: list[Task], group: MixGroup = None):
        super().__init__(parent)
        self.setWindowTitle("믹스 그룹 추가" if group is None else "믹스 그룹 수정")
        self.setFixedSize(480, 560)
        self.setStyleSheet(STYLE)

        self.all_tasks = tasks
        self.editing_group = group
        self.result_group = None

        self._build_ui()
        if group:
            self._populate(group)

    def _title_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("""
            font-size: 13px; font-weight: 600; color: #a0a0c0;
            background: transparent; margin-top: 10px;
        """)
        return lbl

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(24, 20, 24, 20)

        # Group name
        layout.addWidget(self._title_label("그룹 이름"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("예: 팝업 자동 처리")
        layout.addWidget(self.name_edit)

        # Condition type
        layout.addWidget(self._title_label("조건 모드"))
        cond_box = QHBoxLayout()
        self.cond_group = QButtonGroup(self)
        self.radio_and = QRadioButton("🔗 AND — 모두 발견 시")
        self.radio_or = QRadioButton("⚡ OR — 하나라도 발견 시")
        self.radio_or.setChecked(True)
        self.cond_group.addButton(self.radio_and, 0)
        self.cond_group.addButton(self.radio_or, 1)
        cond_box.addWidget(self.radio_and)
        cond_box.addWidget(self.radio_or)
        cond_box.addStretch()
        layout.addLayout(cond_box)

        # Action
        layout.addWidget(self._title_label("실행 액션"))
        action_box = QHBoxLayout()
        self.action_group = QButtonGroup(self)
        self.radio_click = QRadioButton("클릭")
        self.radio_dblclick = QRadioButton("더블클릭")
        self.radio_rclick = QRadioButton("우클릭")
        self.radio_click.setChecked(True)
        self.action_group.addButton(self.radio_click, 0)
        self.action_group.addButton(self.radio_dblclick, 1)
        self.action_group.addButton(self.radio_rclick, 2)
        action_box.addWidget(self.radio_click)
        action_box.addWidget(self.radio_dblclick)
        action_box.addWidget(self.radio_rclick)
        action_box.addStretch()
        layout.addLayout(action_box)

        # Task selection
        layout.addWidget(self._title_label("포함할 작업 선택"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; background: rgba(255,255,255,0.03); }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; }
        """)
        scroll.setFixedHeight(200)

        task_container = QWidget()
        task_container.setStyleSheet("background: transparent;")
        task_layout = QVBoxLayout(task_container)
        task_layout.setContentsMargins(12, 8, 12, 8)
        task_layout.setSpacing(4)

        self.task_checks: list[tuple[QCheckBox, str]] = []
        if not self.all_tasks:
            empty = QLabel("등록된 작업이 없습니다")
            empty.setStyleSheet("color: #5a5a7a; font-size: 12px; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            task_layout.addWidget(empty)
        else:
            for task in self.all_tasks:
                type_emoji = "🖼️" if task.task_type == TaskType.IMAGE else "📝"
                cb = QCheckBox(f"{type_emoji} {task.name}")
                cb.setStyleSheet("background: transparent;")
                self.task_checks.append((cb, task.id))
                task_layout.addWidget(cb)

        task_layout.addStretch()
        scroll.setWidget(task_container)
        layout.addWidget(scroll)

        layout.addStretch()

        # Buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("취소")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("저장")
        save_btn.setProperty("class", "primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(save_btn)
        layout.addLayout(btn_box)

    def _populate(self, group: MixGroup):
        self.name_edit.setText(group.name)
        if group.condition == ConditionType.AND:
            self.radio_and.setChecked(True)
        else:
            self.radio_or.setChecked(True)

        action_map = {
            ActionType.CLICK: self.radio_click,
            ActionType.DOUBLE_CLICK: self.radio_dblclick,
            ActionType.RIGHT_CLICK: self.radio_rclick,
        }
        action_map.get(group.action, self.radio_click).setChecked(True)

        for cb, task_id in self.task_checks:
            if task_id in group.task_ids:
                cb.setChecked(True)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "경고", "그룹 이름을 입력하세요.")
            return

        selected_ids = [tid for cb, tid in self.task_checks if cb.isChecked()]
        if len(selected_ids) < 2:
            QMessageBox.warning(self, "경고", "2개 이상의 작업을 선택하세요.")
            return

        condition = ConditionType.AND if self.radio_and.isChecked() else ConditionType.OR
        action_map = {0: ActionType.CLICK, 1: ActionType.DOUBLE_CLICK, 2: ActionType.RIGHT_CLICK}
        action = action_map.get(self.action_group.checkedId(), ActionType.CLICK)

        self.result_group = MixGroup(
            name=name,
            task_ids=selected_ids,
            condition=condition,
            action=action,
            id=self.editing_group.id if self.editing_group else str(uuid.uuid4())[:8],
        )
        self.accept()
