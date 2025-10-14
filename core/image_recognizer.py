import cv2
import numpy as np
from typing import Optional, Tuple


def _load_image(path: str, description: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"讀取{description}失敗: {path}")
    return image


def _find_best_match(
    search_area_bgr: np.ndarray,
    target_bgr: np.ndarray,
    debug: bool,
) -> tuple[Optional[tuple[int, int]], float, float, Optional[np.ndarray], int, int, float]:
    """在指定影像區塊內進行模板比對，回傳最佳匹配資訊。"""

    search_hsv = cv2.cvtColor(search_area_bgr, cv2.COLOR_BGR2HSV)
    target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)

    search_hsv = cv2.GaussianBlur(search_hsv, (3, 3), 0)
    target_hsv = cv2.GaussianBlur(target_hsv, (3, 3), 0)

    h1, s1, v1 = cv2.split(search_hsv)

    best_score = -1.0
    best_loc: Optional[tuple[int, int]] = None
    best_scale = 1.0
    best_result_map: Optional[np.ndarray] = None
    best_h, best_w = target_hsv.shape[:2]
    best_value_mean = 0.0

    for scale in np.linspace(0.8, 1.2, 9):
        resized = cv2.resize(target_hsv, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h2, s2, _ = cv2.split(resized)

        if h1.shape[0] < h2.shape[0] or h1.shape[1] < h2.shape[1]:
            # 模板比搜尋區域還大時跳過
            continue

        res_h = cv2.matchTemplate(h1, h2, cv2.TM_CCOEFF_NORMED)
        res_s = cv2.matchTemplate(s1, s2, cv2.TM_CCOEFF_NORMED)
        res = res_h * 0.7 + res_s * 0.3

        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > best_score:
            best_score = max_val
            best_loc = max_loc
            best_scale = scale
            best_result_map = res
            best_h, best_w = resized.shape[:2]

            patch_v = v1[max_loc[1]:max_loc[1] + best_h, max_loc[0]:max_loc[0] + best_w]
            if patch_v.size > 0:
                best_value_mean = float(np.mean(patch_v))

    return best_loc, float(best_score), float(best_scale), best_result_map, best_h, best_w, float(best_value_mean)


def _handle_match(
    screen_bgr: np.ndarray,
    best_loc: Optional[tuple[int, int]],
    best_score: float,
    best_scale: float,
    best_result_map: Optional[np.ndarray],
    best_h: int,
    best_w: int,
    best_value_mean: float,
    threshold: float,
    debug: bool,
    offset: tuple[int, int] = (0, 0),
) -> Tuple[Optional[tuple[int, int]], float]:
    x_offset, y_offset = offset

    if best_loc and best_score >= threshold:
        if best_value_mean < 40 or best_value_mean > 240:
            print(f"[SKIP] 光度不符 (mean={best_value_mean:.1f})，忽略此結果")
            return None, best_score

        top_left = (best_loc[0] + x_offset, best_loc[1] + y_offset)
        bottom_right = (top_left[0] + best_w, top_left[1] + best_h)
        center = (top_left[0] + best_w // 2, top_left[1] + best_h // 2)

        cv2.rectangle(screen_bgr, top_left, bottom_right, (0, 255, 0), 2)
        cv2.putText(
            screen_bgr,
            f"{best_score:.2f}@{best_scale:.2f}",
            (top_left[0], top_left[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

        cv2.imwrite("matched_screen.png", screen_bgr)

        if debug and best_result_map is not None:
            res_vis = cv2.normalize(best_result_map, None, 0, 255, cv2.NORM_MINMAX)
            cv2.imwrite("heatmap.png", np.uint8(res_vis))

        print(
            f"[MATCH] scale={best_scale:.2f}, score={best_score:.3f}, "
            f"loc={(top_left[0], top_left[1])}, meanV={best_value_mean:.1f}"
        )
        return (int(center[0]), int(center[1])), float(best_score)

    if best_result_map is not None:
        res_vis = cv2.normalize(best_result_map, None, 0, 255, cv2.NORM_MINMAX)
        cv2.imwrite("heatmap.png", np.uint8(res_vis))

    cv2.imwrite("matched_screen.png", screen_bgr)
    print(f"[NO MATCH] best scale={best_scale:.2f}, score={best_score:.3f}, meanV={best_value_mean:.1f}")
    return None, float(best_score)


def find_image_on_screen(
    screen_path: str,
    target_path: str,
    threshold: float = 0.8,
    debug: bool = False,
) -> Tuple[Optional[tuple[int, int]], float]:
    """在整張螢幕截圖中尋找目標圖片。"""

    screen = _load_image(screen_path, "螢幕截圖")
    target = _load_image(target_path, "目標圖片")

    best_loc, best_score, best_scale, best_result_map, best_h, best_w, best_value_mean = _find_best_match(
        screen, target, debug
    )

    return _handle_match(
        screen,
        best_loc,
        best_score,
        best_scale,
        best_result_map,
        best_h,
        best_w,
        best_value_mean,
        threshold,
        debug,
    )


def find_image_in_region(
    screen_path: str,
    target_path: str,
    region: tuple[int, int, int, int],
    threshold: float = 0.8,
    debug: bool = False,
) -> Tuple[Optional[tuple[int, int]], float]:
    """僅在指定區域內搜尋目標圖片。

    region: (x, y, w, h)
    """

    screen = _load_image(screen_path, "螢幕截圖")
    target = _load_image(target_path, "目標圖片")

    x, y, w, h = region
    if w <= 0 or h <= 0:
        raise ValueError("區域寬高需為正數")

    if x < 0 or y < 0 or x + w > screen.shape[1] or y + h > screen.shape[0]:
        raise ValueError("區域超出螢幕截圖範圍")

    search_area = screen[y : y + h, x : x + w].copy()

    (
        best_loc,
        best_score,
        best_scale,
        best_result_map,
        best_h,
        best_w,
        best_value_mean,
    ) = _find_best_match(search_area, target, debug)

    return _handle_match(
        screen,
        best_loc,
        best_score,
        best_scale,
        best_result_map,
        best_h,
        best_w,
        best_value_mean,
        threshold,
        debug,
        offset=(x, y),
    )
