"""Text recognition using pytesseract OCR."""
import os
import platform
import pytesseract
from PIL import Image
from typing import Optional

# Auto-detect Tesseract on Windows
if platform.system() == "Windows":
    _win_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_win_tesseract):
        pytesseract.pytesseract.tesseract_cmd = _win_tesseract

_TESSERACT_INSTALL_HINT = (
    "Tesseract를 설치해 주세요: https://github.com/UB-Mannheim/tesseract/wiki"
    if platform.system() == "Windows"
    else "'brew install tesseract'를 실행해 주세요."
)


class TextRecognizer:
    """Finds text on screen using OCR."""

    def __init__(self, lang: str = "eng+kor"):
        """
        Initialize the text recognizer.

        Args:
            lang: Tesseract language string (e.g., 'eng', 'kor', 'eng+kor')
        """
        self.lang = lang
        self._tesseract_available = True  # flag to avoid spamming errors

    def find_text(
        self,
        screenshot: Image.Image,
        search_text: str,
    ) -> Optional[tuple[int, int]]:
        """
        Find text within a screenshot and return its center coordinates.

        Args:
            screenshot: PIL Image of the current screen
            search_text: Text to search for (case-insensitive)

        Returns:
            (x, y) center coordinates of the text, or None if not found
        """
        if not self._tesseract_available:
            return None
        try:
            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(
                screenshot, lang=self.lang, output_type=pytesseract.Output.DICT
            )
        except pytesseract.TesseractNotFoundError:
            print(f"[오류] Tesseract가 설치되지 않았습니다. {_TESSERACT_INSTALL_HINT}")
            self._tesseract_available = False
            return None

        n_boxes = len(data["text"])
        search_lower = search_text.lower()

        # First, try to find the exact text in a single word
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue
            if search_lower in text.lower():
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                return (x + w // 2, y + h // 2)

        # If not found in single words, try consecutive words on the same line
        for i in range(n_boxes):
            text_i = data["text"][i].strip()
            if not text_i:
                continue

            # Build consecutive text on the same line
            line_num = data["line_num"][i]
            block_num = data["block_num"][i]
            combined = text_i
            last_idx = i

            for j in range(i + 1, n_boxes):
                if data["block_num"][j] == block_num and data["line_num"][j] == line_num:
                    next_text = data["text"][j].strip()
                    if next_text:
                        combined += " " + next_text
                        last_idx = j
                        if search_lower in combined.lower():
                            # Found it in combined text, return center of the span
                            x1 = data["left"][i]
                            y1 = data["top"][i]
                            x2 = data["left"][last_idx] + data["width"][last_idx]
                            y2 = max(
                                data["top"][k] + data["height"][k]
                                for k in range(i, last_idx + 1)
                                if data["text"][k].strip()
                            )
                            return ((x1 + x2) // 2, (y1 + y2) // 2)

        return None

    def get_all_text(self, screenshot: Image.Image) -> str:
        """Extract all text from a screenshot."""
        try:
            return pytesseract.image_to_string(screenshot, lang=self.lang)
        except pytesseract.TesseractNotFoundError:
            return ""
