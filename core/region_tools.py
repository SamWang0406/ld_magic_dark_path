from __future__ import annotations

from typing import Optional, Tuple
import os
import cv2
import numpy as np
import pytesseract

try:
    import easyocr  # type: ignore
    _HAS_EASYOCR = True
except Exception:
    easyocr = None  # type: ignore
    _HAS_EASYOCR = False

from .image_recognizer import find_image_in_region as _find_image_in_region
from .logger import get_logger

Region = tuple[int, int, int, int]
_logger = get_logger("region_tools")


_easyocr_readers: dict[str, object] = {}


def _map_lang_for_easyocr(lang: str) -> list[str]:
    """Map tesseract style lang code to EasyOCR list.

    - 'chi_tra' -> ['ch_tra']
    - 'chi_sim' -> ['ch_sim']
    otherwise, try to pass-through if EasyOCR likely supports it,
    and always include 'en' as auxiliary unless explicitly Chinese-only.
    """
    lang = (lang or "").strip().lower()
    if lang in ("chi_tra", "zh_tra", "zh_tw", "cht"):
        return ["ch_tra", "en"]
    if lang in ("chi_sim", "zh_sim", "zh_cn", "chs"):
        return ["ch_sim", "en"]
    # Default: include English as helper
    return [lang or "en", "en"]


def _get_easyocr_reader(lang: str):
    langs = _map_lang_for_easyocr(lang)
    key = ",".join(langs)
    reader = _easyocr_readers.get(key)
    if reader is not None:
        return reader
    # GPU toggle via env; default to CPU for portability
    reader = easyocr.Reader(langs, gpu=False)  # type: ignore[name-defined]
    _easyocr_readers[key] = reader
    return reader


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


def _extract_text_with_easyocr(
    screen_path: str,
    region: Region,
    *,
    lang: str = "chi_tra",
) -> str:
    """Use EasyOCR to extract text from a region. Falls back to empty string on errors."""
    try:
        img = cv2.imread(screen_path)
        if img is None:
            return ""
        x, y, w, h = region
        crop = img[y:y + h, x:x + w]
        reader = _get_easyocr_reader(lang)
        # detail=0 returns list[str]; paragraph=False to keep line granularity
        result = reader.readtext(crop, detail=0, paragraph=False)
        # Join and normalize whitespace and newlines similar to tests' normalization
        text = "".join([t for t in result if t]).strip()
        return text
    except Exception as e:
        try:
            _logger.debug(f"EasyOCR failed: {e}")
        except Exception:
            pass
        return ""


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
    """Extract text within a region.

    Engine selection via env `OCR_ENGINE`:
    - 'easyocr' to force EasyOCR
    - 'tesseract' to force Tesseract
    - 'auto' (default): try EasyOCR if available, else Tesseract
    """

    engine = os.getenv("OCR_ENGINE", "auto").strip().lower()

    if engine in ("easy", "easyocr"):
        if _HAS_EASYOCR:
            text = _extract_text_with_easyocr(screen_path, region, lang=lang)
            if text:
                return text
            # If EasyOCR returns empty, fall through to tesseract as safety net
        # EasyOCR not available, fallback
        return _extract_text_from_region(screen_path, region, lang=lang)

    if engine in ("tesseract", "tess"):
        return _extract_text_from_region(screen_path, region, lang=lang)

    # auto
    if _HAS_EASYOCR:
        text = _extract_text_with_easyocr(screen_path, region, lang=lang)
        if text:
            return text
    return _extract_text_from_region(screen_path, region, lang=lang)
    # display = text or "∅"
    # try:
    #     _logger.info(f"[OCR] file='{screen_path}', region={region}, text='{display}'")
    # except Exception:
    #     pass
    
