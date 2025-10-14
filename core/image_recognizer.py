import cv2
import numpy as np
from typing import Optional, Tuple

def find_image_on_screen(
    screen_path: str,
    target_path: str,
    threshold: float = 0.8,
    debug: bool = False
) -> Tuple[Optional[tuple[int, int]], float]:

    screen = cv2.imread(screen_path, cv2.IMREAD_COLOR)
    target = cv2.imread(target_path, cv2.IMREAD_COLOR)

    if screen is None:
        raise FileNotFoundError(f"讀取螢幕截圖失敗: {screen_path}")
    if target is None:
        raise FileNotFoundError(f"讀取目標圖片失敗: {target_path}")

    # 轉換成 HSV 空間
    screen_hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    target_hsv = cv2.cvtColor(target, cv2.COLOR_BGR2HSV)

    # 輕微模糊，增加容錯
    screen_hsv = cv2.GaussianBlur(screen_hsv, (3, 3), 0)
    target_hsv = cv2.GaussianBlur(target_hsv, (3, 3), 0)

    best_score = -1.0
    best_loc = None
    best_scale = 1.0
    best_result_map = None
    best_h, best_w = target_hsv.shape[:2]
    best_value_mean = 0

    # 嘗試多倍率比對 (80%~120%)
    for scale in np.linspace(0.8, 1.2, 9):
        resized = cv2.resize(target_hsv, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h2, s2, v2 = cv2.split(resized)
        h1, s1, v1 = cv2.split(screen_hsv)

        # Hue+Saturation 比對（顏色最具代表性）
        res_h = cv2.matchTemplate(h1, h2, cv2.TM_CCOEFF_NORMED)
        res_s = cv2.matchTemplate(s1, s2, cv2.TM_CCOEFF_NORMED)
        res = (res_h * 0.7 + res_s * 0.3)

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val > best_score:
            best_score = max_val
            best_loc = max_loc
            best_scale = scale
            best_result_map = res
            best_h, best_w = resized.shape[:2]

            # 取該區塊亮度平均值（過亮或過暗排除）
            patch_v = v1[max_loc[1]:max_loc[1]+best_h, max_loc[0]:max_loc[0]+best_w]
            if patch_v.size > 0:
                best_value_mean = float(np.mean(patch_v))

    # 驗證結果
    if best_loc and best_score >= threshold:
        # 濾掉光度極端值
        if best_value_mean < 40 or best_value_mean > 240:
            print(f"[SKIP] 光度不符 (mean={best_value_mean:.1f})，忽略此結果")
            return None, best_score

        cx = best_loc[0] + best_w // 2
        cy = best_loc[1] + best_h // 2

        cv2.rectangle(screen, best_loc, (best_loc[0] + best_w, best_loc[1] + best_h), (0, 255, 0), 2)
        cv2.putText(screen, f"{best_score:.2f}@{best_scale:.2f}", (best_loc[0], best_loc[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imwrite("matched_screen.png", screen)

        if debug and best_result_map is not None:
            res_vis = cv2.normalize(best_result_map, None, 0, 255, cv2.NORM_MINMAX)
            cv2.imwrite("heatmap.png", np.uint8(res_vis))

        print(f"[MATCH] scale={best_scale:.2f}, score={best_score:.3f}, loc={best_loc}, meanV={best_value_mean:.1f}")
        return (int(cx), int(cy)), float(best_score)

    else:
        if best_result_map is not None:
            res_vis = cv2.normalize(best_result_map, None, 0, 255, cv2.NORM_MINMAX)
            cv2.imwrite("heatmap.png", np.uint8(res_vis))
        cv2.imwrite("matched_screen.png", screen)
        print(f"[NO MATCH] best scale={best_scale:.2f}, score={best_score:.3f}, meanV={best_value_mean:.1f}")
        return None, float(best_score)
