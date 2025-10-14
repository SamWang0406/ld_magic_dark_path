#!/usr/bin/env bash
set -euo pipefail

# 可在此覆寫變數：
export ADB_DEVICE="192.168.0.202:5555"
export MATCH_THRESHOLD="0.9"
export CHECK_INTERVAL="1.0"
export CLICK_COOLDOWN="2.0"

nohup python3 main.py > run.log 2>&1 &
echo "ld_magic_dark_path started. See run.log"
