"""Image template matching using OpenCV."""
import cv2
import numpy as np
from PIL import Image
from typing import Optional


class ImageMatcher:
    """Finds template images on screen using OpenCV template matching."""

    def __init__(self, confidence: float = 0.8):
        self.confidence = confidence

    def find_template(
        self,
        screenshot: Image.Image,
        template_path: str,
        confidence: Optional[float] = None,
    ) -> Optional[tuple[int, int]]:
        """
        Find a template image within a screenshot.

        Args:
            screenshot: PIL Image of the current screen
            template_path: Path to the template image file
            confidence: Override default confidence threshold

        Returns:
            (x, y) center coordinates of the match, or None if not found
        """
        threshold = confidence if confidence is not None else self.confidence

        # Convert screenshot to numpy array (BGR for OpenCV)
        screen_np = np.array(screenshot)
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        # Load template
        template = cv2.imread(template_path)
        if template is None:
            return None

        template_h, template_w = template.shape[:2]

        # Perform template matching
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            # Return center of matched region
            center_x = max_loc[0] + template_w // 2
            center_y = max_loc[1] + template_h // 2
            return (center_x, center_y)

        return None

    def find_all_templates(
        self,
        screenshot: Image.Image,
        template_path: str,
        confidence: Optional[float] = None,
    ) -> list[tuple[int, int]]:
        """
        Find all occurrences of a template image within a screenshot.

        Returns:
            List of (x, y) center coordinates of all matches
        """
        threshold = confidence if confidence is not None else self.confidence

        screen_np = np.array(screenshot)
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        template = cv2.imread(template_path)
        if template is None:
            return []

        template_h, template_w = template.shape[:2]

        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        matches = []
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + template_w // 2
            center_y = pt[1] + template_h // 2
            # Avoid duplicate nearby detections (within 10px)
            is_duplicate = False
            for existing in matches:
                if abs(center_x - existing[0]) < 10 and abs(center_y - existing[1]) < 10:
                    is_duplicate = True
                    break
            if not is_duplicate:
                matches.append((center_x, center_y))

        return matches
