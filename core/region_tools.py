from __future__ import annotations

from typing import Optional, Tuple
import cv2
import numpy as np
import pytesseract

from .image_recognizer import find_image_in_region as _find_image_in_region
from .logger import get_logger

Region = tuple[int, int, int, int]
_logger = get_logger("region_tools")


def _extract_text_from_region(
    screen_path: str,
    region: Region,
    *,
    lang: str = "chi_tra",
) -> str:
    """使用強化預處理的 OCR 文字辨識"""
    img = cv2.imread(screen_path)
    if img is None:
        return ""

    # 擷取指定區域
    x, y, w, h = region
    crop = img[y:y + h, x:x + w]

    # === Step 1: 灰階 + 去雜訊 ===
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 75, 75)

    # === Step 2: 對比強化 ===
    gray = cv2.equalizeHist(gray)

    # === Step 3: Otsu 二值化 + 反白 ===
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = cv2.bitwise_not(bw)

    # === Step 4: 閉運算（補上描邊文字空隙）===
    kernel = np.ones((2, 2), np.uint8)
    closed = cv2.morphologyEx(inv, cv2.MORPH_CLOSE, kernel)

    # === Step 5: OCR ===
    config = "--psm 7 --oem 3"
    try:
        text = pytesseract.image_to_string(closed, lang=lang, config=config).strip()
    except Exception:
        text = ""

    # === Step 6: fallback（若抓不到文字，再反向測一次）===
    if not text:
        try:
            alt = cv2.bitwise_not(closed)
            text = pytesseract.image_to_string(alt, lang=lang, config=config).strip()
        except Exception:
            pass

    return text


def find_image(
    screen_path: str,
    template_path: str,
    region: Region,
    *,
    threshold: float = 0.8,
    debug: bool = False,
    debug_tag: Optional[str] = None,
    debug_dir: str = "debug",
    value_check: bool = True,
    value_mean_min: float = 40.0,
    value_mean_max: float = 240.0,
) -> Tuple[Optional[tuple[int, int]], float]:
    """Find an image within a region on the given screenshot."""
    return _find_image_in_region(
        screen_path,
        template_path,
        region,
        threshold=threshold,
        debug=debug,
        debug_tag=debug_tag,
        debug_dir=debug_dir,
        value_check=value_check,
        value_mean_min=value_mean_min,
        value_mean_max=value_mean_max,
    )


def find_text(
    screen_path: str,
    region: Region,
    *,
    lang: str = "chi_tra",
) -> str:
    """Extract text within a region from the given screenshot (with enhanced preprocessing)."""
    text = _extract_text_from_region(screen_path, region, lang=lang)
    # display = text or "∅"
    # try:
    #     _logger.info(f"[OCR] file='{screen_path}', region={region}, text='{display}'")
    # except Exception:
    #     pass
    return text
