# ld_magic_dark_path（Ubuntu 常駐版）

針對 **LDPlayer 9** 的背景自動化工具：在不影響滑鼠鍵盤的情況下，
於背景持續執行多個任務（tasks），例如偵測指定圖片並在模擬器內 **點擊**。

---

## ✅ 功能特點

- 透過 **ADB** 對模擬器下指令（非模擬滑鼠），不干擾主機操作
- **OpenCV** 圖片比對（Template Matching）
- 多任務：以簡單 Task 介面擴充與排序
- 常駐模式：持續輪詢、且具 **點擊冷卻時間**
- 可由環境變數調整門檻、間隔、裝置 ID

---

## 📦 安裝與執行（Ubuntu）

### 1) 安裝相依

```bash
sudo apt update
sudo apt install -y python3-pip adb
pip install -r requirements.txt
```

### 2) 連線到 LDPlayer

在 Windows 的 LDPlayer 9 開啟 ADB（或於設定啟用），確認 ADB 埠號（通常為 5555）。  
在 Ubuntu VM 上：

```bash
# 將 <WINDOWS_HOST_IP> 替換為你的 Windows 主機 IP，例如 192.168.0.10
adb connect <WINDOWS_HOST_IP>:5555
adb devices
```

若成功會看到類似：

```
List of devices attached
192.168.0.10:5555    device
```

> 若你已在 Windows 把埠轉送到 127.0.0.1:5555，也可於 VM 連線該 IP/Port。請依你的網路架構調整。

### 3) 放置目標圖片

將要辨識的按鈕或區塊截圖存成：

```
templates/target.png
```

### 4) 設定任務並執行

```bash
# 預設任務為 cow_level（尋找「奶牛關」）
python3 main.py
```

或背景常駐：

```bash
nohup python3 main.py > run.log 2>&1 &
# 檢視即時輸出
tail -f run.log
```

### 5) 停止

```bash
pkill -f ld_magic_dark_path | true
pkill -f main.py | true
```

---

## ⚙️ 可調整參數（環境變數）

| 變數                           | 預設值                  | 說明                                          |
| ------------------------------ | ----------------------- | --------------------------------------------- |
| `TASKS`                        | `cow_level`             | 以逗號分隔的任務清單                          |
| `ADB_DEVICE`                   | 自動取第一個裝置        | 例：`192.168.0.10:5555`                       |
| `SCREENSHOT_PATH`              | `screen.png`            | 本機儲存螢幕截圖路徑                          |
| `TARGET_IMAGE`                 | `templates/target.png`  | 要比對的目標圖片（通用）                      |
| `MATCH_THRESHOLD`              | `0.8`                   | 影像比對通用門檻（0~1）                       |
| `COW_TARGET_THRESHOLD`         | 取自 `MATCH_THRESHOLD`  | 奶牛關目標圖的專用門檻                        |
| `PAUSE_THRESHOLD`              | 取自 `MATCH_THRESHOLD`  | 暫停鍵圖的專用門檻                            |
| `EXIT_THRESHOLD`               | 取自 `MATCH_THRESHOLD`  | 離開鍵圖的專用門檻                            |
| `CONFIRM_THRESHOLD`            | 取自 `MATCH_THRESHOLD`  | 確認鍵圖的專用門檻                            |
| `ENTER_BEFORE_EXIT`            | `1`                     | 未偵測到奶牛關時，先嘗試進入任一關卡再離開    |
| `ANY_LEVEL_IMAGE`              | 空字串                  | 「任一關卡」的模板圖；未提供則不嘗試進入      |
| `ANY_LEVEL_REGION`             | 空（全螢幕）            | 上述模板的搜尋區域 `x,y,w,h`                  |
| `ANY_LEVEL_THRESHOLD`          | 取自 `MATCH_THRESHOLD`  | 任一關卡模板的門檻                            |
| `ENTER_WAIT_SECONDS`           | `1.0`                   | 點進關卡後等待秒數，讓暫停鍵出現              |
| `IN_PROGRESS_IMAGE`            | 預設沿用 `PAUSE_IMAGE`  | 進行中畫面的模板（常用暫停鍵）                |
| `IN_PROGRESS_REGION`           | 預設沿用 `PAUSE_REGION` | 進行中模板搜尋區域                            |
| `IN_PROGRESS_THRESHOLD`        | 取自 `MATCH_THRESHOLD`  | 進行中模板門檻                                |
| `IN_PROGRESS_BRIGHTNESS_CHECK` | 取自 `BRIGHTNESS_CHECK` | 是否啟用光度過濾                              |
| `IN_PROGRESS_VALUE_MEAN_MIN`   | 取自 `VALUE_MEAN_MIN`   | 光度下限                                      |
| `IN_PROGRESS_VALUE_MEAN_MAX`   | 取自 `VALUE_MEAN_MAX`   | 光度上限                                      |
| `AUTO_EXIT_IF_IN_PROGRESS`     | `0`                     | 偵測到進行中時自動執行離開流程                |
| `CHECK_INTERVAL`               | `1.0`                   | 每次檢查的秒數                                |
| `CLICK_COOLDOWN`               | `2.0`                   | 點擊後冷卻秒數，避免狂點                      |
| `TAP_DELAY_SECONDS`            | `1.0`                   | 每次 tap 後額外等待秒數（序列點擊之間的間隔） |

範例：

```bash
TASKS=cow_level ADB_DEVICE=192.168.0.10:5555 MATCH_THRESHOLD=0.86 CHECK_INTERVAL=0.8 CLICK_COOLDOWN=2.0 \
python3 main.py
```

---

## 🧪 圖片與測試資產

### Debug 產物位置

- 比對時的標註截圖與熱度圖會輸出至 `debug/` 資料夾，檔名會帶有對應的 `tag`（例如 `pause_matched.png`, `pause_heatmap.png`）。
- 區域預覽亦輸出到 `debug/`（例如 `region_pause.png`）。

### 產生測試圖片

```bash
# 推薦用模組方式執行（可避免匯入路徑問題）
python3 -m tools.generate_test_images --device "$ADB_DEVICE" --out debug --screen screen.png

# 或直接執行腳本（已內建路徑處理）
python3 tools/generate_test_images.py --device "$ADB_DEVICE" --out debug --screen screen.png

# 若已存在 screen.png，可加上 --no-capture
python3 -m tools.generate_test_images --no-capture
```

### 快速取得像素座標

```bash
# GUI 模式（需要可用的顯示環境，否則會報 Qt/xcb 錯誤）
python3 tools/pixel_picker.py debug/screen.png

# 無視窗（headless）模式：直接指定座標並輸出一張標註圖
python3 tools/pixel_picker.py debug/screen.png --x 720 --y 540 --out debug/pick.png
```

若你在伺服器或沒有 X 顯示的環境看到類似「qt.qpa.xcb: could not connect to display」的錯誤，請使用 headless 模式。

### 模板製作建議

- 使用小範圍、對比清楚且 **固定** 的 UI 元素作為模板
- 若 App 有動態陰影或縮放差異，可提供多張模板並延伸 `main.py` 邏輯去輪流比對
- 若解析度差異大，考慮把 `screen.png` 或模板做等比例縮放後再比對（進階可自行擴充）

---

## 🧰 Region 工具（簡化 API）

提供兩個常用的區域辨識工具，簡化呼叫：

- `core/region_tools.py: find_image(screen_path, template_path, region, threshold=0.8, ...) -> (point|None, score)`
- `core/region_tools.py: find_text(screen_path, region, lang='chi_tra') -> str`

使用範例：

```python
from core.region_tools import find_image, find_text

# 區域內找文字
text = find_text('screen.png', (560, 260, 370, 60))

# 區域內找圖片
pt, score = find_image('screen.png', 'templates/exit.png', (720, 540, 280, 90), threshold=0.85, debug=True, debug_tag='exit')
if pt:
    print('center at', pt, 'score', score)
```

說明：

- `find_image` 內部沿用既有 `image_recognizer` 的多尺度比對、光度過濾與 debug 產物輸出。
- `find_text` 內部沿用既有 `text_recognizer` 的 OCR 前處理（灰階 + 二值化）。
- 特殊文字正規化規則保留在各任務內（避免過度耦合）。

---

## 📁 專案結構（多任務）

```
ld_magic_dark_path/
├── core/
│   ├── adb_controller.py
│   ├── image_recognizer.py
│   ├── image_utils.py
│   ├── region_tools.py
│   └── logger.py
├── tools/
│   ├── pixel_picker.py
│   └── generate_test_images.py
├── tasks/
│   ├── __init__.py
│   └── cow_level.py
├── templates/
│   └── target.png
├── main.py
├── requirements.txt
└── README.md
```

---

## TODO:

- [ ] 修復有奶牛關之後，點擊賜福關會需要點擊隨便一個能力
- [ ] 修復沒有辦法固定打同一關，如果贏了的話會跳到下一關
- [ ] 優化點擊隨機副本後，判斷右上角的文字，如果是奶牛關也要算 cow_count+=1

## TODO Future

- [ ] 新增介面
- [ ] 簡化程式碼、優化程式碼
