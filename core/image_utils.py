import os
import cv2
from typing import Tuple


def get_pixel_color(image_path: str, x: int, y: int) -> Tuple[int, int, int]:
    """Return BGR color at (x, y) from image.

    Raises FileNotFoundError if image not readable or ValueError if out of bounds.
    """
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片: {image_path}")
    h, w = img.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        raise ValueError(f"座標超出範圍: ({x},{y}) for image size ({w}x{h})")
    b, g, r = img[y, x]
    return int(b), int(g), int(r)

