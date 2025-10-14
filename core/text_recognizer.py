import cv2
import pytesseract


def extract_text_from_region(
    image_path: str,
    region: tuple[int, int, int, int],
    lang: str = "chi_tra",
) -> str:
    """
    擷取圖片中指定區域的文字
    region = (x, y, w, h)
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片: {image_path}")

    x, y, w, h = region
    crop = img[y:y+h, x:x+w]

    # 灰階 + 二值化可提升辨識率
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # 使用 tesseract 進行 OCR
    text = pytesseract.image_to_string(gray, lang=lang)  # 支援中文
    text = text.strip().replace(" ", "").replace("\n", "")
    return text


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
    cv2.imwrite(file_name, img)
    # cv2.imshow("TEXT_REGION", img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()