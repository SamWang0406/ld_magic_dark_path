#!/usr/bin/env python3
import argparse
import cv2
import os
from pathlib import Path


def _annotate_and_save(img, x: int, y: int, out_path: str) -> None:
    vis = img.copy()
    h, w = vis.shape[:2]
    x = max(0, min(w - 1, int(x)))
    y = max(0, min(h - 1, int(y)))
    cv2.circle(vis, (x, y), 6, (0, 255, 255), 2)
    b, g, r = [int(v) for v in vis[y, x]]
    label = f"({x},{y}) BGR=({b},{g},{r})"
    cv2.putText(vis, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    out_dir = os.path.dirname(out_path) or "debug"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base = os.path.basename(out_path) or "pick.png"
    cv2.imwrite(os.path.join(out_dir, base), vis)


def main():
    parser = argparse.ArgumentParser(description="Pick pixel color from an image. GUI if available; headless with --x --y.")
    parser.add_argument("image", help="Path to image to open (e.g., latest screenshot)")
    parser.add_argument("--x", type=int, help="X coordinate (headless mode)")
    parser.add_argument("--y", type=int, help="Y coordinate (headless mode)")
    parser.add_argument("--out", default="debug/pick.png", help="Output annotated image path (headless mode)")
    args = parser.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片: {args.image}")

    # Headless mode: coordinates provided
    if args.x is not None and args.y is not None:
        h, w = img.shape[:2]
        if not (0 <= args.x < w and 0 <= args.y < h):
            raise ValueError(f"座標超出範圍: ({args.x},{args.y}) for image size ({w}x{h})")
        b, g, r = [int(v) for v in img[args.y, args.x]]
        print(f"(x={args.x}, y={args.y}) BGR=({b},{g},{r})")
        try:
            _annotate_and_save(img, args.x, args.y, args.out)
            print(f"已輸出標註圖片: {args.out}")
        except Exception as e:
            print(f"標註輸出失敗: {e}")
        return

    # GUI mode (requires display)
    try:
        win = "PixelPicker"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 960, 540)

        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                b, g, r = img[y, x]
                print(f"pos=({x},{y}) BGR=({int(b)},{int(g)},{int(r)})")

        cv2.setMouseCallback(win, on_mouse)
        cv2.imshow(win, img)
        print("左鍵點擊圖片即可輸出像素座標與顏色，按任意鍵關閉視窗…")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception as e:
        print("GUI 模式無法啟動（可能沒有顯示環境）。請改用 headless 模式：")
        print("  python3 tools/pixel_picker.py <image> --x <X> --y <Y> [--out debug/pick.png]")
        print(f"詳細錯誤: {e}")


if __name__ == "__main__":
    main()
