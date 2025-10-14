import subprocess
import shlex
from typing import Optional

def _run(cmd: str) -> str:
    # Use shell=False for safety; allow spaces via shlex.split
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nSTDERR: {proc.stderr.strip()}")
    return proc.stdout.strip()

def _prefix(device_id: Optional[str]) -> str:
    return f"-s {device_id} " if device_id else ""

def capture_screen(save_path: str, device_id: Optional[str] = None):
    """
    透過 adb 擷取模擬器畫面到本機。
    """
    prefix = _prefix(device_id)
    _run(f"adb {prefix}shell screencap -p /sdcard/__ld_screen.png")
    _run(f"adb {prefix}pull /sdcard/__ld_screen.png {save_path}")

def tap(x: int, y: int, device_id: Optional[str] = None):
    prefix = _prefix(device_id)
    _run(f"adb {prefix}shell input tap {int(x)} {int(y)}")

def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, device_id: Optional[str] = None):
    prefix = _prefix(device_id)
    _run(f"adb {prefix}shell input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")

def devices() -> list[str]:
    out = _run("adb devices")
    lines = [ln.strip() for ln in out.splitlines()[1:] if ln.strip()]
    devs = []
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 2 and parts[1] == "device":
            devs.append(parts[0])
    return devs
