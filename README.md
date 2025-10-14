# ld_magic_dark_path（Ubuntu 常駐版）

針對 **LDPlayer 9** 的背景自動化工具：在不影響滑鼠鍵盤的情況下，
於背景持續偵測螢幕是否出現指定圖片，若出現則自動在模擬器內 **點擊**。

---

## ✅ 功能特點

- 透過 **ADB** 對模擬器下指令（非模擬滑鼠），不干擾主機操作
- **OpenCV** 圖片比對（Template Matching）
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

### 4) 直接執行

```bash
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

| 變數              | 預設值                 | 說明                     |
| ----------------- | ---------------------- | ------------------------ |
| `ADB_DEVICE`      | 自動取第一個裝置       | 例：`192.168.0.10:5555`  |
| `SCREENSHOT_PATH` | `screen.png`           | 本機儲存螢幕截圖路徑     |
| `TARGET_IMAGE`    | `templates/target.png` | 要比對的目標圖片         |
| `MATCH_THRESHOLD` | `0.8`                  | 圖片相似度門檻（0~1）    |
| `CHECK_INTERVAL`  | `1.0`                  | 每次檢查的秒數           |
| `CLICK_COOLDOWN`  | `2.0`                  | 點擊後冷卻秒數，避免狂點 |

範例：

```bash
ADB_DEVICE=192.168.0.10:5555 MATCH_THRESHOLD=0.86 CHECK_INTERVAL=0.8 python3 main.py
```

---

## 🧪 圖片製作建議

- 使用小範圍、對比清楚且 **固定** 的 UI 元素作為模板
- 若 App 有動態陰影或縮放差異，可提供多張模板並延伸 `main.py` 邏輯去輪流比對
- 若解析度差異大，考慮把 `screen.png` 或模板做等比例縮放後再比對（進階可自行擴充）

---

## 📁 專案結構

```
ld_magic_dark_path/
├── core/
│   ├── adb_controller.py
│   ├── image_recognizer.py
│   └── logger.py
├── templates/
│   └── target.png
├── main.py
├── requirements.txt
└── README.md
```

---

## 🧩 後續可擴充

- 多圖比對與優先序
- 多裝置（多開）管理
- 任務排程 / 狀態機
- 更強健的特徵比對（ORB/SIFT）以提升抗縮放/旋轉能力
