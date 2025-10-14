import os
import time
import logging
from core.adb_controller import capture_screen, tap
from core.image_recognizer import find_image_on_screen
from core.text_recognizer import extract_text_from_region, show_region

# ================== 基本設定 ==================
SCREENSHOT_PATH = "screen.png"
TARGET_IMAGE = "templates/target.png"  # 目標圖片（例如奶牛關傳送門）
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", 0.9))
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL", 1.0))

# 兩個 OCR 區域 (x, y, w, h) -- 根據你的畫面解析度微調
TEXT_REGION_LEFT = (560, 260, 930-560, 320-260)   # 奶牛關
TEXT_REGION_RIGHT = (985, 260, 1360-985, 320-260)  # 菁英副本

# 目標文字：如果其中一框辨識出這個文字，就進行點擊
TARGET_TEXT = "奶牛關"

# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def normalize_text(text: str) -> str:
    """清理 OCR 結果"""
    return text.replace(" ", "").replace("\n", "").replace("★", "")

def main():
    logging.info("啟動 ld_magic_dark_path 常駐監看程序")
    logging.info(f"目標文字: {TARGET_TEXT}")
    logging.info(f"目標圖片: {TARGET_IMAGE}")
    logging.info(f"相似度門檻: {MATCH_THRESHOLD}")
    logging.info(f"檢查間隔: {CHECK_INTERVAL}s")

    while True:
        try:
            # Step 1. 擷取螢幕
            show_region(SCREENSHOT_PATH, TEXT_REGION_LEFT, "region_preview_left.png")
            show_region(SCREENSHOT_PATH, TEXT_REGION_RIGHT, "region_preview_right.png")
            capture_screen(SCREENSHOT_PATH)

            # Step 2. 讀取兩個區塊文字
            text_left = normalize_text(extract_text_from_region(SCREENSHOT_PATH, TEXT_REGION_LEFT))
            text_right = normalize_text(extract_text_from_region(SCREENSHOT_PATH, TEXT_REGION_RIGHT))

            logging.info(f"[OCR] 左邊辨識: {text_left or '(無文字)'}")
            logging.info(f"[OCR] 右邊辨識: {text_right or '(無文字)'}")

            # Step 3. 判斷哪一框包含目標文字
            if TARGET_TEXT in text_left:
                logging.info(f"[INFO] 左側偵測到目標「{TARGET_TEXT}」，進行圖像比對...")
                pt, score = find_image_on_screen(SCREENSHOT_PATH, TARGET_IMAGE, MATCH_THRESHOLD)
                if pt:
                    x, y = pt
                    logging.info(f"[CLICK] 左側找到目標 (信心值: {score:.2f}) → 點擊位置 ({x}, {y})")
                    tap(x, y)
                else:
                    logging.info(f"[INFO] 左側未找到圖片，最大匹配度: {score:.2f}")

            elif TARGET_TEXT in text_right:
                logging.info(f"[INFO] 右側偵測到目標「{TARGET_TEXT}」，進行圖像比對...")
                pt, score = find_image_on_screen(SCREENSHOT_PATH, TARGET_IMAGE, MATCH_THRESHOLD)
                if pt:
                    x, y = pt
                    logging.info(f"[CLICK] 右側找到目標 (信心值: {score:.2f}) → 點擊位置 ({x}, {y})")
                    tap(x, y)
                else:
                    logging.info(f"[INFO] 右側未找到圖片，最大匹配度: {score:.2f}")

            else:
                logging.info(f"[INFO] 未偵測到「{TARGET_TEXT}」，跳過。")

        except Exception as e:
            logging.error(f"[ERROR] {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
