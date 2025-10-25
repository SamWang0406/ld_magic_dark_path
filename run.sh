#!/usr/bin/env bash
set -euo pipefail

# 可在此覆寫變數：
export ADB_DEVICE="192.168.0.202:5555"
# 通用比對門檻；可被下方專用門檻覆蓋
export MATCH_THRESHOLD="0.9"
# （選用）針對各辨識點個別設定門檻
# export COW_TARGET_THRESHOLD="0.9"
export PAUSE_THRESHOLD="0.8"
# export EXIT_THRESHOLD="0.88"
# export CONFIRM_THRESHOLD="0.9"

# （選用）未偵測到奶牛關時，先進任一關卡再離開
export ENTER_BEFORE_EXIT="1"
# export ANY_LEVEL_IMAGE="templates/any_level.png"
# export ANY_LEVEL_REGION=""   # 預設全螢幕，或填 x,y,w,h
# export ANY_LEVEL_THRESHOLD="0.85"
# export ENTER_WAIT_SECONDS="1.0"

# （選用）進行中畫面偵測與自動離開
# export IN_PROGRESS_IMAGE="templates/pause.png"   # 預設沿用 PAUSE_IMAGE
# export IN_PROGRESS_REGION="0,0,65,75"            # 預設沿用 PAUSE_REGION
# export IN_PROGRESS_THRESHOLD="0.85"
# export IN_PROGRESS_BRIGHTNESS_CHECK="1"
# export IN_PROGRESS_VALUE_MEAN_MIN="40.0"
# export IN_PROGRESS_VALUE_MEAN_MAX="240.0"
export AUTO_EXIT_IF_IN_PROGRESS="1"
export CHECK_INTERVAL="1.0"
export CLICK_COOLDOWN="2.0"
export TAP_DELAY_SECONDS="0.7"

nohup python3 main.py > run.log 2>&1 &
echo "ld_magic_dark_path started. See run.log"
