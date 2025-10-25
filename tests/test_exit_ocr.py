import os
from typing import Tuple

import pytest

from core.region_tools import find_text


def _parse_region(s: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) != 4:
        raise ValueError(f"EXIT_REGION 格式錯誤: {s}")
    x, y, w, h = map(int, parts)
    return x, y, w, h


def _normalize(t: str) -> str:
    return t.replace(" ", "").replace("\n", "")


def _ensure_ocr_tuning():
    # 提升細字辨識的預設建議（不覆蓋外部已設定值）
    os.environ.setdefault("OCR_PSM", "7")
    os.environ.setdefault("OCR_SCALE", "2.5")
    os.environ.setdefault("OCR_DILATE", "1")
    os.environ.setdefault("OCR_INV", "1")
    # 僅在需要檢視處理影像時再開
    # os.environ.setdefault("OCR_DEBUG", "1")


@pytest.mark.parametrize("image_path", ["debug/region_exit_text.png"])
def test_exit_ocr_text(image_path: str):
    if not os.path.exists(image_path):
        pytest.skip(f"缺少測試影像：{image_path}")

    # 讀取 EXIT_REGION，若未設定則沿用任務中的預設值
    region_str = os.getenv("EXIT_REGION", "800,600,300,100")
    region = _parse_region(region_str)

    _ensure_ocr_tuning()

    text = find_text(image_path, region)
    normalized = _normalize(text)
    print(f"[TEST] EXIT OCR 辨識: '{normalized or '∅'}'")

    # 接受常見變體，以降低中文 OCR 誤差造成的誤判
    candidates = {"退出戰鬥", "退出战斗", "退出戰鬭"}

    assert any(c in normalized for c in candidates), (
        f"未在 OCR 結果中找到預期文字，辨識='{normalized or '∅'}'，"
        f"請檢查 EXIT_REGION 或調整 OCR_* 參數"
    )


if __name__ == "__main__":
    # 允許直接以腳本方式執行以快速查看結果
    path = "debug/region_exit_text.png"
    if not os.path.exists(path):
        raise SystemExit(f"缺少影像：{path}")
    region_str = os.getenv("EXIT_REGION", "800,600,300,100")
    region = _parse_region(region_str)
    _ensure_ocr_tuning()
    text = find_text(path, region)
    print(f"OCR='{text or '∅'}'  region={region}")
