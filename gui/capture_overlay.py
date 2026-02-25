"""Screen region capture overlay using PyQt6."""
import sys
from PyQt6.QtWidgets import QWidget, QApplication, QLabel
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QGuiApplication
from PIL import Image


class CaptureOverlay(QWidget):
    """
    Full-screen transparent overlay for selecting a screen region.
    """

    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_selecting = False
        self.screenshot_pixmap = None
        self.pil_screenshot = None

    def start(self):
        """Take screenshot and show overlay."""
        # Take screenshot before showing overlay
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.screenshot_pixmap = screen.grabWindow(0)
            # Convert to PIL
            qimg = self.screenshot_pixmap.toImage()
            width = qimg.width()
            height = qimg.height()
            ptr = qimg.bits()
            ptr.setsize(height * width * 4)
            self.pil_screenshot = Image.frombytes("RGBA", (width, height), bytes(ptr), "raw", "BGRA")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.showFullScreen()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw screenshot as background
        if self.screenshot_pixmap:
            painter.drawPixmap(0, 0, self.width(), self.height(), self.screenshot_pixmap)

        # Dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Draw selection rectangle
        if self.is_selecting:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            # Clear the selection area (show original screenshot)
            if self.screenshot_pixmap:
                sx = self.screenshot_pixmap.width() / self.width()
                sy = self.screenshot_pixmap.height() / self.height()
                source_rect = QRect(
                    int(rect.x() * sx), int(rect.y() * sy),
                    int(rect.width() * sx), int(rect.height() * sy)
                )
                painter.drawPixmap(rect, self.screenshot_pixmap, source_rect)

            # Selection border
            pen = QPen(QColor(124, 58, 237), 2)  # Purple border
            painter.setPen(pen)
            painter.drawRect(rect)

        # Instructions
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(painter.font())
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
            "\n\n마우스를 드래그하여 캡처할 영역을 선택하세요 (ESC: 취소)"
        )
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.end_pos = event.pos()
            self.is_selecting = False

            rect = QRect(self.start_pos, self.end_pos).normalized()

            if rect.width() < 10 or rect.height() < 10:
                self.close()
                if self.callback:
                    self.callback(None, None)
                return

            self.close()

            if self.pil_screenshot and self.callback:
                # Scale coordinates to actual screenshot size
                sx = self.pil_screenshot.width / self.width()
                sy = self.pil_screenshot.height / self.height()
                crop_box = (
                    int(rect.x() * sx),
                    int(rect.y() * sy),
                    int(rect.right() * sx),
                    int(rect.bottom() * sy),
                )
                cropped = self.pil_screenshot.crop(crop_box)
                self.callback(cropped, (rect.x(), rect.y(), rect.right(), rect.bottom()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            if self.callback:
                self.callback(None, None)
