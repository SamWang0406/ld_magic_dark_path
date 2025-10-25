import cv2
import os
import time
import pytesseract
from pytesseract import Output


def extract_text_from_region(
    image_path: str,
    region: tuple[int, int, int, int],
    lang: str = "chi_tra",
) -> str:
    """
    擷取圖片中指定區域的文字（強化版）
    - 自動對比增強與降噪
    - 自動於黑/白字之間選擇最佳二值化
    - OTSU / 自適應門檻自動嘗試
    - 以 Tesseract 置信度挑選最佳結果
    可用環境變數覆寫：OCR_SCALE, OCR_PSM, OCR_METHOD, OCR_DEBUG, OCR_DILATE
    """

    def _bool_env(name: str, default: str = "0") -> bool:
        return os.getenv(name, default).strip() not in ("0", "false", "False", "no", "NO")

    def _float_env(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except Exception:
            return default

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片: {image_path}")

    x, y, w, h = region
    crop = img[y:y + h, x:x + w]

    # 動態縮放（未指定時依區域大小自動放大）
    scale_env = os.getenv("OCR_SCALE", os.getenv("TEXT_OCR_SCALE", "")).strip()
    if scale_env:
        scale = _float_env("OCR_SCALE", _float_env("TEXT_OCR_SCALE", 1.0))
    else:
        scale = 2.0 if h < 40 else (1.5 if h < 80 else 1.2)

    psm = os.getenv("OCR_PSM", "7").strip()  # 預設單行
    method = os.getenv("OCR_METHOD", os.getenv("TEXT_OCR_METHOD", "auto")).lower()
    debug_flag = _bool_env("OCR_DEBUG", "0")
    dilate_iter = int(os.getenv("OCR_DILATE", "1"))  # 預設做輕微連接

    # Step 1: 灰階 + 降噪 + 對比增強
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 75, 75)
    # 使用 CLAHE 做局部對比提升，對細字更友善
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enh = clahe.apply(gray)

    # 產生候選二值化影像
    candidates: list[tuple[str, any]] = []

    def add_candidates_from(img_gray):
        # OTSU（黑字/白字）
        _, b1 = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, b2 = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        candidates.append(("otsu_bin", b1))
        candidates.append(("otsu_inv", b2))
        # Adaptive（較適合低對比）
        block = int(os.getenv("OCR_ADAPTIVE_BLOCK", "31"))
        block = block if block % 2 == 1 else block + 1
        c_val = int(os.getenv("OCR_ADAPTIVE_C", "5"))
        a1 = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, c_val)
        a2 = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, c_val)
        candidates.append(("ada_bin", a1))
        candidates.append(("ada_inv", a2))

    if method == "otsu":
        add_candidates_from(enh)
        candidates = [c for c in candidates if c[0].startswith("otsu")]  # 僅留 OTSU
    elif method == "adaptive":
        add_candidates_from(enh)
        candidates = [c for c in candidates if c[0].startswith("ada")]  # 僅留 Adaptive
    else:
        add_candidates_from(enh)  # auto: 同時嘗試

    # 輕微形態學處理（連接斷裂筆畫）
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    processed = []
    for tag, img_bin in candidates:
        img_proc = cv2.morphologyEx(img_bin, cv2.MORPH_CLOSE, kernel)
        if dilate_iter > 0:
            img_proc = cv2.dilate(img_proc, kernel, iterations=dilate_iter)
        processed.append((tag, img_proc))

    # 放大
    final_candidates = []
    for tag, p in processed:
        if scale and abs(scale - 1.0) > 1e-3:
            p = cv2.resize(p, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        final_candidates.append((tag, p))

    # OCR 與評分：使用 image_to_data 取得平均置信度
    def _ocr_with_conf(img_bin) -> tuple[str, float]:
        cfg = f"--psm {psm} --oem 3"
        try:
            data = pytesseract.image_to_data(img_bin, lang=lang, config=cfg, output_type=Output.DICT)
            texts = [t for t in data.get("text", []) if t and t.strip()]
            confs = [float(c) for c in data.get("conf", []) if c not in ("-1", -1, None)]
            text_join = "".join(texts)
            mean_conf = sum(confs) / len(confs) if confs else 0.0
            return text_join, mean_conf
        except Exception:
            try:
                # 回退：至少要能回傳文字
                t = pytesseract.image_to_string(img_bin, lang=lang, config=f"--psm {psm} --oem 3")
                return t, 0.0
            except Exception:
                return "", 0.0

    best_text = ""
    best_conf = -1.0
    best_tag = ""
    for tag, p in final_candidates:
        t, c = _ocr_with_conf(p)
        t = t.strip().replace(" ", "").replace("\n", "")
        # 以置信度為主，長度作為平手判斷
        if (c > best_conf + 1e-6) or (abs(c - best_conf) <= 1e-6 and len(t) > len(best_text)):
            best_conf = c
            best_text = t
            best_tag = tag

    if debug_flag:
        ts = int(time.time() * 1000)
        out_dir = "debug/ocr"
        os.makedirs(out_dir, exist_ok=True)
        cv2.imwrite(f"{out_dir}/crop_{x}_{y}_{w}_{h}_{ts}.png", crop)
        for tag, p in final_candidates:
            cv2.imwrite(f"{out_dir}/bin_{tag}_{x}_{y}_{w}_{h}_{ts}.png", p)

    return best_text


def find_text_in_region(
    image_path: str,
    region: tuple[int, int, int, int],
    target_text: str,
    *,
    lang: str = "chi_tra",
) -> tuple[bool, str]:
    """辨識區域內文字，並判斷是否包含指定內容。"""

    text = extract_text_from_region(image_path, region, lang=lang)
    return target_text in text, text


def show_region(image_path: str, region: tuple[int, int, int, int], file_name):
    img = cv2.imread(image_path)
    x, y, w, h = region
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    # 若未指定資料夾，預設輸出到 debug/
    out_dir = os.path.dirname(file_name) or "debug"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(file_name)
    cv2.imwrite(os.path.join(out_dir, base), img)
    # cv2.imshow("TEXT_REGION", img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
