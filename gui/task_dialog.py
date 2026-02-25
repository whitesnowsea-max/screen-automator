"""Task creation/editing dialog using PyQt6."""
import os
import uuid

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QPushButton, QSlider, QFrame,
    QMessageBox, QWidget, QCheckBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QGuiApplication
from PIL import Image

from models.task import Task, TaskType, ActionType
from gui.capture_overlay import CaptureOverlay


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
        color: #c8c8e0; font-size: 12px; spacing: 8px;
        background: transparent;
    }
    QRadioButton::indicator {
        width: 16px; height: 16px; border-radius: 8px;
        border: 2px solid rgba(255,255,255,0.2);
        background: transparent;
    }
    QRadioButton::indicator:checked {
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.4,
            stop:0 #7c3aed, stop:1 #6d28d9);
        border: 2px solid rgba(124, 58, 237, 0.6);
    }
    QCheckBox {
        color: #c8c8e0; font-size: 12px; spacing: 8px;
        background: transparent;
    }
    QSlider::groove:horizontal {
        background: rgba(255,255,255,0.08); height: 6px; border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #7c3aed, stop:1 #6d28d9);
        width: 18px; height: 18px; margin: -6px 0; border-radius: 9px;
        border: 2px solid rgba(124, 58, 237, 0.3);
    }
    QFrame[class="panel"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
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
    QPushButton[class="capture"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #7c3aed, stop:1 #6d28d9);
        color: white; border: none; border-radius: 10px;
        padding: 10px 20px; font-size: 13px; font-weight: 500;
    }
    QPushButton[class="capture"]:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #6d28d9, stop:1 #5b21b6);
    }
"""


class TaskDialog(QDialog):
    def __init__(self, parent, templates_dir="templates", task=None):
        super().__init__(parent)
        self.setWindowTitle("작업 추가" if task is None else "작업 수정")
        self.setFixedSize(500, 850)
        self.setStyleSheet(STYLE)

        self.templates_dir = templates_dir
        os.makedirs(templates_dir, exist_ok=True)
        self.result_task = None
        self.captured_image = None
        self.editing_task = task
        self._overlay = None
        self._captured_search_region = None  # (x1, y1, x2, y2) in screen coords

        self._build_ui()
        if task:
            self._populate(task)

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
        layout.setContentsMargins(20, 15, 20, 15)

        # Task name
        layout.addWidget(self._title_label("작업 이름"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("예: 확인 버튼 클릭")
        layout.addWidget(self.name_edit)

        # Task type
        layout.addWidget(self._title_label("인식 모드"))
        type_box = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.radio_image = QRadioButton("🖼️ 이미지 인식")
        self.radio_text = QRadioButton("📝 텍스트 인식 (OCR)")
        self.radio_image.setChecked(True)
        self.type_group.addButton(self.radio_image, 0)
        self.type_group.addButton(self.radio_text, 1)
        type_box.addWidget(self.radio_image)
        type_box.addWidget(self.radio_text)
        type_box.addStretch()
        layout.addLayout(type_box)
        self.type_group.idToggled.connect(self._on_type_change)

        # Image panel
        self.image_panel = QFrame()
        self.image_panel.setProperty("class", "panel")
        self.image_panel.setStyleSheet("background-color: #2a2a3d; border-radius: 8px; padding: 10px;")
        ip_layout = QVBoxLayout(self.image_panel)
        capture_btn = QPushButton("📷 화면 영역 캡처")
        capture_btn.setProperty("class", "capture")
        capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        capture_btn.clicked.connect(self._do_capture)
        ip_layout.addWidget(capture_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.preview_label = QLabel("캡처된 이미지가 여기에 표시됩니다")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #8888aa;")
        self.preview_label.setMinimumHeight(60)
        ip_layout.addWidget(self.preview_label)

        # Confidence
        conf_box = QHBoxLayout()
        conf_box.addWidget(QLabel("신뢰도:"))
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(50, 100)
        self.confidence_slider.setValue(80)
        self.confidence_slider.setTickInterval(5)
        conf_box.addWidget(self.confidence_slider)
        self.conf_label = QLabel("0.80")
        conf_box.addWidget(self.conf_label)
        self.confidence_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f"{v/100:.2f}")
        )
        ip_layout.addLayout(conf_box)
        layout.addWidget(self.image_panel)

        # Text panel
        self.text_panel = QFrame()
        self.text_panel.setProperty("class", "panel")
        self.text_panel.setStyleSheet("background-color: #2a2a3d; border-radius: 8px; padding: 10px;")
        tp_layout = QVBoxLayout(self.text_panel)
        tp_layout.addWidget(QLabel("찾을 텍스트:"))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("예: 확인, OK, 계속")
        tp_layout.addWidget(self.text_edit)
        layout.addWidget(self.text_panel)
        self.text_panel.hide()

        # Action
        layout.addWidget(self._title_label("수행할 동작"))
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

        # Cooldown
        layout.addWidget(self._title_label("재클릭 대기 시간"))
        cd_box = QHBoxLayout()
        self.cooldown_slider = QSlider(Qt.Orientation.Horizontal)
        self.cooldown_slider.setRange(5, 100)  # 0.5 to 10.0 (x10)
        self.cooldown_slider.setValue(30)
        cd_box.addWidget(self.cooldown_slider)
        self.cd_label = QLabel("3.0초")
        cd_box.addWidget(self.cd_label)
        self.cooldown_slider.valueChanged.connect(
            lambda v: self.cd_label.setText(f"{v/10:.1f}초")
        )
        layout.addLayout(cd_box)

        # ── Search Region ──
        layout.addWidget(self._title_label("검색 구역"))
        region_box = QHBoxLayout()
        self.region_group = QButtonGroup(self)
        self.radio_fullscreen = QRadioButton("🖥️ 풀스크린")
        self.radio_region = QRadioButton("📐 구역 지정")
        self.radio_fullscreen.setChecked(True)
        self.region_group.addButton(self.radio_fullscreen, 0)
        self.region_group.addButton(self.radio_region, 1)
        region_box.addWidget(self.radio_fullscreen)
        region_box.addWidget(self.radio_region)
        region_box.addStretch()
        layout.addLayout(region_box)

        self.region_panel = QFrame()
        self.region_panel.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 10px;")
        rp_layout = QVBoxLayout(self.region_panel)
        region_capture_btn = QPushButton("📐 검색 구역 선택")
        region_capture_btn.setProperty("class", "capture")
        region_capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        region_capture_btn.clicked.connect(self._do_region_capture)
        rp_layout.addWidget(region_capture_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.region_label = QLabel("선택된 구역 없음")
        self.region_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.region_label.setStyleSheet("color: #8888aa; font-size: 11px;")
        rp_layout.addWidget(self.region_label)
        layout.addWidget(self.region_panel)
        self.region_panel.hide()

        self.region_group.idToggled.connect(self._on_region_change)

        # ── Auto Scroll ──
        layout.addWidget(self._title_label("자동 스크롤"))
        self.scroll_check = QCheckBox("🔄 대상을 못 찾으면 자동 스크롤 후 재검색")
        self.scroll_check.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        layout.addWidget(self.scroll_check)

        self.scroll_panel = QFrame()
        self.scroll_panel.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 10px;")
        sp_layout = QHBoxLayout(self.scroll_panel)
        sp_layout.addWidget(QLabel("최대 스크롤 횟수:"))
        self.scroll_slider = QSlider(Qt.Orientation.Horizontal)
        self.scroll_slider.setRange(1, 30)
        self.scroll_slider.setValue(10)
        sp_layout.addWidget(self.scroll_slider)
        self.scroll_count_label = QLabel("10회")
        sp_layout.addWidget(self.scroll_count_label)
        self.scroll_slider.valueChanged.connect(
            lambda v: self.scroll_count_label.setText(f"{v}회")
        )
        layout.addWidget(self.scroll_panel)
        self.scroll_panel.hide()

        self.scroll_check.toggled.connect(self._on_scroll_toggle)

        # ── Type Text After Click ──
        layout.addWidget(self._title_label("클릭 후 텍스트 입력"))
        self.type_check = QCheckBox("⌨️ 클릭 후 텍스트 자동 입력")
        self.type_check.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        layout.addWidget(self.type_check)

        self.type_panel = QFrame()
        self.type_panel.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 10px;")
        tp2_layout = QVBoxLayout(self.type_panel)

        tp2_layout.addWidget(QLabel("입력할 텍스트:"))
        self.type_text_edit = QLineEdit()
        self.type_text_edit.setPlaceholderText("예: Hello World, 검색어 등")
        tp2_layout.addWidget(self.type_text_edit)

        delay_box = QHBoxLayout()
        delay_box.addWidget(QLabel("입력 대기 시간:"))
        self.type_delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.type_delay_slider.setRange(3, 30)  # 0.3 to 3.0 (x10)
        self.type_delay_slider.setValue(5)
        delay_box.addWidget(self.type_delay_slider)
        self.type_delay_label = QLabel("0.5초")
        delay_box.addWidget(self.type_delay_label)
        self.type_delay_slider.valueChanged.connect(
            lambda v: self.type_delay_label.setText(f"{v/10:.1f}초")
        )
        tp2_layout.addLayout(delay_box)

        self.enter_check = QCheckBox("입력 후 Enter 키 누르기")
        self.enter_check.setChecked(True)
        self.enter_check.setStyleSheet("color: #c8c8e0; font-size: 12px;")
        tp2_layout.addWidget(self.enter_check)

        layout.addWidget(self.type_panel)
        self.type_panel.hide()

        self.type_check.toggled.connect(self._on_type_toggle)

        layout.addStretch()

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        save_btn = QPushButton("저장")
        save_btn.setProperty("class", "primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("취소")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def _on_type_change(self, id, checked):
        if not checked:
            return
        if id == 0:  # image
            self.image_panel.show()
            self.text_panel.hide()
        else:  # text
            self.image_panel.hide()
            self.text_panel.show()

    def _on_region_change(self, id, checked):
        if not checked:
            return
        if id == 1:  # custom region
            self.region_panel.show()
        else:  # fullscreen
            self.region_panel.hide()
            self._captured_search_region = None
            self.region_label.setText("선택된 구역 없음")

    def _on_scroll_toggle(self, checked):
        self.scroll_panel.setVisible(checked)

    def _on_type_toggle(self, checked):
        self.type_panel.setVisible(checked)

    def _do_capture(self):
        self.hide()
        QTimer.singleShot(300, self._start_capture)

    def _start_capture(self):
        self._overlay = CaptureOverlay(callback=self._on_capture_done)
        self._overlay.start()

    def _do_region_capture(self):
        self.hide()
        QTimer.singleShot(300, self._start_region_capture)

    def _start_region_capture(self):
        self._overlay = CaptureOverlay(callback=self._on_region_capture_done)
        self._overlay.start()

    def _on_capture_done(self, image, bbox):
        self.show()
        self.raise_()
        if image is None:
            return
        self.captured_image = image
        # Show preview
        preview = image.copy()
        preview.thumbnail((400, 120))
        qimage = QImage(
            preview.tobytes("raw", "RGBA"), preview.width, preview.height,
            QImage.Format.Format_RGBA8888,
        )
        pixmap = QPixmap.fromImage(qimage)
        self.preview_label.setPixmap(pixmap)

    def _on_region_capture_done(self, image, bbox):
        self.show()
        self.raise_()
        if image is None or bbox is None:
            return
        # bbox is in widget coords, scale to actual screen pixels
        screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            ratio = screen.devicePixelRatio()
            sx = (geom.width() * ratio) / geom.width()  # typically 1.0 or 2.0
            # bbox = (x1_widget, y1_widget, x2_widget, y2_widget)
            self._captured_search_region = (
                int(bbox[0] * sx), int(bbox[1] * sx),
                int(bbox[2] * sx), int(bbox[3] * sx),
            )
        else:
            self._captured_search_region = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
        r = self._captured_search_region
        self.region_label.setText(f"구역: ({r[0]}, {r[1]}) → ({r[2]}, {r[3]})  [{r[2]-r[0]}×{r[3]-r[1]}]")

    def _populate(self, task):
        self.name_edit.setText(task.name)
        if task.task_type == TaskType.TEXT:
            self.radio_text.setChecked(True)
            if task.search_text:
                self.text_edit.setText(task.search_text)
        else:
            self.radio_image.setChecked(True)
        self.confidence_slider.setValue(int(task.confidence * 100))
        self.cooldown_slider.setValue(int(task.cooldown * 10))

        action_map = {ActionType.CLICK: self.radio_click,
                      ActionType.DOUBLE_CLICK: self.radio_dblclick,
                      ActionType.RIGHT_CLICK: self.radio_rclick}
        action_map.get(task.action, self.radio_click).setChecked(True)

        if task.task_type == TaskType.IMAGE and task.template_path:
            try:
                img = Image.open(task.template_path)
                self.captured_image = img
                preview = img.copy()
                preview.thumbnail((400, 120))
                qimage = QImage(
                    preview.tobytes("raw", "RGBA"), preview.width, preview.height,
                    QImage.Format.Format_RGBA8888,
                )
                self.preview_label.setPixmap(QPixmap.fromImage(qimage))
            except Exception:
                pass

        # Search region
        if task.search_region:
            self.radio_region.setChecked(True)
            self._captured_search_region = task.search_region
            r = task.search_region
            self.region_label.setText(f"구역: ({r[0]}, {r[1]}) → ({r[2]}, {r[3]})  [{r[2]-r[0]}×{r[3]-r[1]}]")

        # Auto scroll
        if task.auto_scroll:
            self.scroll_check.setChecked(True)
            self.scroll_slider.setValue(task.max_scrolls)

        # Type text
        if task.type_text:
            self.type_check.setChecked(True)
            self.type_text_edit.setText(task.type_text)
            self.type_delay_slider.setValue(int(task.type_delay * 10))
            self.enter_check.setChecked(task.press_enter)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "경고", "작업 이름을 입력하세요.")
            return

        task_type = TaskType.IMAGE if self.radio_image.isChecked() else TaskType.TEXT
        action_map = {0: ActionType.CLICK, 1: ActionType.DOUBLE_CLICK, 2: ActionType.RIGHT_CLICK}
        action = action_map.get(self.action_group.checkedId(), ActionType.CLICK)

        template_path = None
        search_text = None

        if task_type == TaskType.IMAGE:
            if self.captured_image is None and (
                self.editing_task is None or self.editing_task.task_type != TaskType.IMAGE
            ):
                QMessageBox.warning(self, "경고", "화면 영역을 캡처하세요.")
                return
            if self.captured_image:
                tid = self.editing_task.id if self.editing_task else uuid.uuid4().hex[:8]
                template_path = os.path.join(self.templates_dir, f"{tid}.png")
                self.captured_image.save(template_path)
            elif self.editing_task:
                template_path = self.editing_task.template_path
        else:
            search_text = self.text_edit.text().strip()
            if not search_text:
                QMessageBox.warning(self, "경고", "찾을 텍스트를 입력하세요.")
                return

        # Gather search region
        search_region = None
        if self.radio_region.isChecked() and self._captured_search_region:
            search_region = self._captured_search_region

        # Gather auto-scroll options
        auto_scroll = self.scroll_check.isChecked()
        max_scrolls = self.scroll_slider.value() if auto_scroll else 10

        # Gather type-text options
        type_text = None
        type_delay = 0.5
        press_enter = True
        if self.type_check.isChecked():
            type_text = self.type_text_edit.text()
            if not type_text:
                QMessageBox.warning(self, "경고", "입력할 텍스트를 입력하세요.")
                return
            type_delay = self.type_delay_slider.value() / 10.0
            press_enter = self.enter_check.isChecked()

        self.result_task = Task(
            name=name,
            task_type=task_type,
            action=action,
            template_path=template_path,
            search_text=search_text,
            confidence=self.confidence_slider.value() / 100.0,
            cooldown=self.cooldown_slider.value() / 10.0,
            id=self.editing_task.id if self.editing_task else str(uuid.uuid4())[:8],
            search_region=search_region,
            auto_scroll=auto_scroll,
            max_scrolls=max_scrolls,
            type_text=type_text,
            type_delay=type_delay,
            press_enter=press_enter,
        )
        self.accept()
