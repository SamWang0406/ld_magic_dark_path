from __future__ import annotations

import os
from typing import Optional
import time

from core.adb_controller import tap, capture_screen
from core.image_recognizer import find_image_on_screen, find_image_in_region
from core.text_recognizer import show_region
from core.region_tools import find_text, find_image
from core.task import Task, TaskContext, TaskResult
from core.logger import get_logger


def _normalize_text(text: str) -> str:
    t = text.replace(" ", "").replace("\n", "").replace("★", "").replace("闊", "關")
    if t == "命運宇菩":
        t = "命運寶藏"
    if t == "壹系副本" or t == "袍系熏本":
        t = "魂系副本"
    if t == "芋衣副本":
        t = "普通副本"
    if t == "點召琅本" or t == "點髒勳本":
        t = "困難副本"
    if t == "款英琅本":
        t = "精英副本"
    if t == "請橫副本":
        t = "隨機副本"
    if t == "禾盾關" or t == "物牛關" or t == "奶牛闊":
        t = "奶牛關"
    return t


STAR_BY_LABEL = {
    "賜福關": 1,
    "普通副本": 1,
    "精英副本": 2,
    "困難副本": 3,
    "命運寶藏": 4,
    "奶牛關": 4,
    "魂系副本": 4,
    "隨機副本": 4,
}


class CowLevelTask(Task):
    name = "cow_level"

    def __init__(self) -> None:
        self.logger = get_logger("cow_level")
        self.left_region = self._parse_region(os.getenv("COW_REGION_LEFT", "560,260,370,60"))
        self.right_region = self._parse_region(os.getenv("COW_REGION_RIGHT", "985,260,375,60"))
        self.target_text = os.getenv("COW_TARGET_TEXT", "奶牛關")
        self.target_image = os.getenv("COW_TARGET_IMAGE", os.getenv("TARGET_IMAGE", "templates/cow_level.png"))
        # 每一個辨識可自訂門檻，未提供時回退全域或預設
        _global_threshold = float(os.getenv("MATCH_THRESHOLD", "0.8"))
        self.target_threshold = float(os.getenv("COW_TARGET_THRESHOLD", str(_global_threshold)))
        self.total_stars = 0
        # 統計用計數器
        self.cow_hits = 0  # 累計本程式存活期間遇到奶牛關的次數
        self.stat_cow_once = 0  # 星數達標時，遇到奶牛關次數為 1 的次數
        self.stat_cow_twice = 0  # 星數達標時，遇到奶牛關次數 > 1 的次數
        self.stat_exit_with_final = 0  # 已執行退出流程（有先進入最終關卡）的次數
        self.stat_exit_without_final = 0  # 已執行退出流程（未進入最終關卡）的次數
        self.cow_hits = 0  # 紀錄遇到奶牛關次數
        # 點擊之間的顯示用延遲（實際延遲由 adb_controller.tap 依環境變數 TAP_DELAY_SECONDS 執行）
        try:
            self.tap_delay_seconds = float(os.getenv("TAP_DELAY_SECONDS", "1.0"))
        except Exception:
            self.tap_delay_seconds = 1.0

        # 若未偵測到奶牛關，可先嘗試點任一關卡再離開（可由環境變數啟用/停用）
        self.enter_before_exit = os.getenv("ENTER_BEFORE_EXIT", "1").strip() not in (
            "0",
            "false",
            "False",
            "no",
            "NO",
        )
        self.any_level_image = os.getenv("ANY_LEVEL_IMAGE", "").strip()
        self.any_level_region = self._parse_region_or_none(os.getenv("ANY_LEVEL_REGION", ""))
        self.any_level_threshold = float(os.getenv("ANY_LEVEL_THRESHOLD", str(_global_threshold)))
        self.enter_wait_seconds = float(os.getenv("ENTER_WAIT_SECONDS", "1.0"))

        # 進行中（In-Progress）偵測（預設沿用 pause 的模板與區域）
        self.inprog_region = self._parse_region_or_none(
            os.getenv("IN_PROGRESS_REGION", os.getenv("PAUSE_REGION", "0,0,65,75"))
        )
        self.inprog_image = os.getenv("IN_PROGRESS_IMAGE", os.getenv("PAUSE_IMAGE", "templates/pause.png"))
        self.inprog_threshold = float(os.getenv("IN_PROGRESS_THRESHOLD", str(_global_threshold)))

        self.pause_region = self._parse_region_or_none(os.getenv("PAUSE_REGION", "0,0,65,75"))
        self.pause_image = os.getenv("PAUSE_IMAGE", "templates/pause.png")
        self.pause_threshold = float(os.getenv("PAUSE_THRESHOLD", str(_global_threshold)))
        # 亮度過濾可調整/關閉（全域與各步驟）
        def _bool_env(name: str, default: str) -> bool:
            return os.getenv(name, default).strip() not in ("0", "false", "False", "no", "NO")

        self.value_check_global = _bool_env("BRIGHTNESS_CHECK", "1")
        self.pause_value_check = _bool_env("PAUSE_BRIGHTNESS_CHECK", "1" if self.value_check_global else "0")
        self.inprog_value_check = _bool_env("IN_PROGRESS_BRIGHTNESS_CHECK", "1" if self.value_check_global else "0")
        self.auto_exit_if_in_progress = _bool_env("AUTO_EXIT_IF_IN_PROGRESS", "0")

        self.exit_region = self._parse_region_or_none(os.getenv("EXIT_REGION", "875,610,170,45"))
        self.exit_image = os.getenv("EXIT_IMAGE", "templates/exit.png")
        self.exit_threshold = float(os.getenv("EXIT_THRESHOLD", str(_global_threshold)))
        self.exit_value_check = _bool_env("EXIT_BRIGHTNESS_CHECK", "1" if self.value_check_global else "0")
        # 是否嚴格匹配完整『退出戰鬥』字串；預設放寬為包含『退出』即可
        self.exit_match_strict = os.getenv("EXIT_MATCH_STRICT", "0").strip() not in (
            "0",
            "false",
            "False",
            "no",
            "NO",
        )

        self.confirm_region = self._parse_region_or_none(os.getenv("CONFIRM_REGION", "790,700,85,40"))
        self.confirm_image = os.getenv("CONFIRM_IMAGE", "templates/confirm.png")
        self.confirm_threshold = float(os.getenv("CONFIRM_THRESHOLD", str(_global_threshold)))
        self.confirm_value_check = _bool_env("CONFIRM_BRIGHTNESS_CHECK", "1" if self.value_check_global else "0")

        # 戰鬥失敗後的『確定』再點一次（可由環境變數覆寫位置/圖片/門檻）
        self.fail_confirm_region = self._parse_region_or_none(
            os.getenv("FAIL_CONFIRM_REGION", "1690,1000,110,50")
        )
        self.fail_confirm_image = os.getenv("FAIL_CONFIRM_IMAGE", self.confirm_image)
        self.fail_confirm_threshold = float(os.getenv("FAIL_CONFIRM_THRESHOLD", str(_global_threshold)))

        def _float_env(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, str(default)))
            except Exception:
                return default

        self.value_mean_min = _float_env("VALUE_MEAN_MIN", 40.0)
        self.value_mean_max = _float_env("VALUE_MEAN_MAX", 240.0)
        self.pause_value_mean_min = _float_env("PAUSE_VALUE_MEAN_MIN", self.value_mean_min)
        self.pause_value_mean_max = _float_env("PAUSE_VALUE_MEAN_MAX", self.value_mean_max)
        self.inprog_value_mean_min = _float_env("IN_PROGRESS_VALUE_MEAN_MIN", self.value_mean_min)
        self.inprog_value_mean_max = _float_env("IN_PROGRESS_VALUE_MEAN_MAX", self.value_mean_max)
        self.exit_value_mean_min = _float_env("EXIT_VALUE_MEAN_MIN", self.value_mean_min)
        self.exit_value_mean_max = _float_env("EXIT_VALUE_MEAN_MAX", self.value_mean_max)
        self.confirm_value_mean_min = _float_env("CONFIRM_VALUE_MEAN_MIN", self.value_mean_min)
        self.confirm_value_mean_max = _float_env("CONFIRM_VALUE_MEAN_MAX", self.value_mean_max)

        # 最後關卡（點擊用）可由環境變數覆寫
        self.final_stage_region = self._parse_region_or_none(os.getenv("FINAL_STAGE_REGION", "780,400,370,270"))
        # 也支援以座標方式指定（優先於區域），預設為 950,500
        self.final_stage_point = self._parse_point_or_none(os.getenv("FINAL_STAGE_POINT", "950,500"))

    def _stat_line(self) -> str:
        # 增加 cow_count 顯示，讓日誌可直接看見累計遇到奶牛關次數
        return (
            f"[STAT] cow_count={self.cow_hits} "
            f"cow_once={self.stat_cow_once} "
            f"cow_twice={self.stat_cow_twice} "
            f"exit_with_final={self.stat_exit_with_final} "
            f"exit_without_final={self.stat_exit_without_final}"
        )

    def _parse_region(self, s: str) -> tuple[int, int, int, int]:
        parts = [int(p) for p in s.split(",")]
        if len(parts) != 4:
            raise ValueError("Region must be 'x,y,w,h'")
        return parts[0], parts[1], parts[2], parts[3]

    def _parse_region_or_none(self, s: str) -> Optional[tuple[int, int, int, int]]:
        try:
            x, y, w, h = self._parse_region(s)
            if w <= 0 or h <= 0:
                return None
            return x, y, w, h
        except Exception:
            return None

    def _parse_point_or_none(self, s: str) -> Optional[tuple[int, int]]:
        try:
            parts = [int(p) for p in s.split(",")]
            if len(parts) != 2:
                return None
            return parts[0], parts[1]
        except Exception:
            return None

    def _label_from_text(self, text: str) -> Optional[str]:
        for label in STAR_BY_LABEL.keys():
            if label in text:
                return label
        return None

    def _add_stars(self, label: str) -> None:
        self.total_stars += STAR_BY_LABEL.get(label, 0)

    def _copy_debug_images(self, tag: str) -> None:
        # 已改為在 debug/ 下以 tag 命名，不再需要額外複製
        return


    def _tap_region_center(self, ctx: TaskContext, region: Optional[tuple[int, int, int, int]], tag: str) -> tuple[bool, str]:
        if region is None:
            return False, f"{tag}: 未設定區域"
        x, y, w, h = region
        cx, cy = x + w // 2, y + h // 2
        tap(cx, cy, device_id=ctx.device_id)
        return True, f"點擊{tag}中心({cx},{cy})"

    def _judge_and_tap(self,
                        ctx: TaskContext,
                        *,
                        tag: str,
                        region: Optional[tuple[int, int, int, int]],
                        text_predicate,
                        image_path: Optional[str],
                        image_threshold: float,
                        ) -> list[str]:
        """通用流程：在指定區域以『文字或圖片』任一命中即點擊中心。
        - 同一個流程，僅判斷位置（region）與關鍵字/模板不同
        """
        msgs: list[str] = []
        if region is None:
            msgs.append(f"[{tag}] 未設定區域，略過")
            return msgs

        # 顯示區域快照以便除錯
        try:
            show_region(ctx.screenshot_path, region, f"region_{tag}.png")
        except Exception:
            pass

        # 先做 OCR 判斷
        try:
            txt = find_text(ctx.screenshot_path, region)
        except Exception:
            txt = ""
        # 特殊處理：確認區域常見 OCR 誤辨『雁現』→ 視為『確認』
        orig_txt = txt
        if tag in ("confirm", "fail_confirm") and (txt or ""):
            compact = (txt or "").replace(" ", "")
            if "雁現" in compact:
                txt = (txt or "").replace("雁現", "確認")
                # 若沒有直接替換到（因為空白或換行），直接覆寫為標準詞
                if txt == orig_txt:
                    txt = "確認"
        if txt != orig_txt:
            try:
                msgs.append(f"[{tag.upper()}] 修正OCR: '{orig_txt or '∅'}' → '{txt}'")
            except Exception:
                pass
        ok_txt = False
        try:
            ok_txt = bool(text_predicate(txt))
        except Exception:
            ok_txt = False
        msgs.append(f"[{tag.upper()}] 判斷: text 命中={'是' if ok_txt else '否'} 辨識='{txt or '∅'}'")

        # 再做圖片模板判斷（如有提供模板）
        ok_img = False
        score = 0.0
        if image_path and os.path.exists(image_path):
            try:
                pt, sc = find_image(ctx.screenshot_path, image_path, region, threshold=0.0)
                score = sc
                ok_img = sc >= image_threshold and bool(pt)
            except Exception:
                ok_img = False
            msgs.append(f"[{tag.upper()}] 判斷: img score={score:.2f} (門檻={image_threshold:.2f}) 命中={'是' if ok_img else '否'}")

        # 文字或圖片任一命中即可
        if not (ok_txt or ok_img):
            msgs.append(f"[{tag.upper()}] 判斷未命中（text/img 皆否），停止後續點擊")
            return msgs

        # 命中後點擊中心
        ok_tap, tap_msg = self._tap_region_center(ctx, region, tag)
        msgs.append(f"[{tag.upper()}] 動作: {tap_msg}")
        return msgs

    def _simple_exit_sequence(self, ctx: TaskContext) -> list[str]:
        msgs: list[str] = []
        ok_p, m_p = self._tap_region_center(ctx, self.pause_region, "pause")
        msgs.append(f"[EXIT] 動作: {m_p}")
        time.sleep(self.tap_delay_seconds)

        ok_e, m_e = self._tap_region_center(ctx, self.exit_region, "exit")
        msgs.append(f"[EXIT] 動作: {m_e}")
        time.sleep(self.tap_delay_seconds)

        ok_c, m_c = self._tap_region_center(ctx, self.confirm_region, "confirm")
        msgs.append(f"[EXIT] 動作: {m_c}")
        time.sleep(self.tap_delay_seconds)

        ok_fc, m_fc = self._tap_region_center(ctx, self.fail_confirm_region, "fail_confirm")
        msgs.append(f"[EXIT] 動作: {m_fc}")
        return msgs

    def _find_and_tap(self, ctx: TaskContext, image: str, region: Optional[tuple[int, int, int, int]], tag: str, threshold: float) -> tuple[bool, str]:
        if not image or not os.path.exists(image):
            return False, f"未提供或找不到圖片：{tag}（{image}）"

        if region is not None:
            try:
                show_region(ctx.screenshot_path, region, f"region_{tag}.png")
            except Exception:
                pass

        if region is None:
            pt, score = find_image_on_screen(
                ctx.screenshot_path,
                image,
                threshold=threshold,
                debug=True,
                debug_tag=tag,
                value_check=(
                    self.pause_value_check if tag == "pause" else self.exit_value_check if tag == "exit" else self.confirm_value_check
                ),
                value_mean_min=(
                    self.pause_value_mean_min if tag == "pause" else self.exit_value_mean_min if tag == "exit" else self.confirm_value_mean_min
                ),
                value_mean_max=(
                    self.pause_value_mean_max if tag == "pause" else self.exit_value_mean_max if tag == "exit" else self.confirm_value_mean_max
                ),
            )
        else:
            pt, score = find_image_in_region(
                ctx.screenshot_path,
                image,
                region,
                threshold=threshold,
                debug=True,
                debug_tag=tag,
                value_check=(
                    self.pause_value_check if tag == "pause" else self.exit_value_check if tag == "exit" else self.confirm_value_check
                ),
                value_mean_min=(
                    self.pause_value_mean_min if tag == "pause" else self.exit_value_mean_min if tag == "exit" else self.confirm_value_mean_min
                ),
                value_mean_max=(
                    self.pause_value_mean_max if tag == "pause" else self.exit_value_mean_max if tag == "exit" else self.confirm_value_mean_max
                ),
            )

        self._copy_debug_images(tag)

        if pt:
            tap(pt[0], pt[1], device_id=ctx.device_id)
            return True, f"點擊{tag}({pt[0]},{pt[1]}) score={score:.2f}"
        return False, (
            f"未匹配到{tag}，信心度={score:.2f} (門檻={threshold:.2f})，"
            f"請調整 {tag.upper()}_IMAGE 與 {tag.upper()}_REGION（如有）"
        )

    def _perform_exit_sequence(self, ctx: TaskContext) -> str:
        msgs: list[str] = []

        ok, m = self._find_and_tap(ctx, self.pause_image, self.pause_region, "pause", self.pause_threshold)
        msgs.append(m)
        if ok:
            msgs.append(f"等待{self.tap_delay_seconds:.1f}s")
            # 暫停後重新擷取畫面，後續 OCR/比對才會是最新狀態
            try:
                capture_screen(ctx.screenshot_path, device_id=ctx.device_id)
            except Exception:
                pass

        # 透過文字判斷並點擊「退出戰鬥」
        if self.exit_region is not None:
            # 在成功點到暫停並重新擷取畫面後，才輸出區域預覽與 OCR
            if ok:
                try:
                    show_region(ctx.screenshot_path, self.exit_region, "region_exit_text.png")
                except Exception:
                    pass
            text_exit = find_text(ctx.screenshot_path, self.exit_region)
            if self._is_exit_text(text_exit):
                x, y, w, h = self.exit_region
                cx, cy = x + w // 2, y + h // 2
                tap(cx, cy, device_id=ctx.device_id)
                ok2, m2 = True, f"點擊exit_text({cx},{cy}) 辨識='{text_exit or '∅'}'"
                # 點擊退出後再擷取一次畫面，供 confirm 使用
                try:
                    capture_screen(ctx.screenshot_path, device_id=ctx.device_id)
                except Exception:
                    pass
            else:
                ok2, m2 = False, f"未匹配到exit_text，辨識='{text_exit or '∅'}'，請調整 EXIT_REGION"
        else:
            # 無區域時回退圖片比對以維持相容性
            ok2, m2 = self._find_and_tap(ctx, self.exit_image, None, "exit", self.exit_threshold)
            if ok2:
                try:
                    capture_screen(ctx.screenshot_path, device_id=ctx.device_id)
                except Exception:
                    pass
        msgs.append(m2)
        if ok2:
            msgs.append(f"等待{self.tap_delay_seconds:.1f}s")

        # 僅在成功點到退出後才嘗試 confirm（避免誤點）
        if ok2:
            # TODO: 可改成 OCR 判斷「確定」字樣
            ok3, m3 = self._find_and_tap(ctx, self.confirm_image, self.confirm_region, "confirm", self.confirm_threshold)
            msgs.append(m3)
        else:
            msgs.append("略過 confirm：尚未成功點擊退出")

        return "\n".join(msgs)

    def _is_exit_text(self, text: str) -> bool:
        t = (text or "").replace(" ", "")
        if self.exit_match_strict:
            return any(s in t for s in ("退出戰鬥", "退出战斗", "退出戰鬭"))
        # 寬鬆策略：包含『退出』即可視為命中，容忍字尾誤辨
        return "退出" in t

    def _check_in_progress(self, ctx: TaskContext) -> tuple[bool, str, float]:
        # 簡化流程：不再依此決策是否執行，保留以備未來需要
        return False, "跳過進行中檢查（已簡化流程）", 0.0

    def tick(self, ctx: TaskContext) -> TaskResult:
        try:
            # 外層『當輪』迴圈：每一輪重置星數與當輪奶牛關數量
            while True:
                round_stars = 0
                round_cow_hits = 0

                # 回到清單（與現有起始流程相同）
                time.sleep(2.0)
                for i in range(3):
                    tap(1570, 850, device_id=ctx.device_id)
                    time.sleep(0.1)
                tap(1670, 1015, device_id=ctx.device_id)
                time.sleep(2.0)
                # 重新擷取畫面供 OCR
                try:
                    capture_screen(ctx.screenshot_path, device_id=ctx.device_id)
                except Exception:
                    pass

                # 顯示左右區域框與 OCR
                try:
                    show_region(ctx.screenshot_path, self.left_region, "region_level_left.png")
                    show_region(ctx.screenshot_path, self.right_region, "region_level_right.png")
                except Exception:
                    pass

                left_raw = find_text(ctx.screenshot_path, self.left_region)
                right_raw = find_text(ctx.screenshot_path, self.right_region)
                text_left = _normalize_text(left_raw)
                text_right = _normalize_text(right_raw)
                self.logger.info(f"左區域文字='{text_left}'")
                self.logger.info(f"右區域文字='{text_right}'")

                # 若一開始不是奶牛關，維持既有行為：選關→退出→回傳
                if (self.target_text not in text_left) and (self.target_text not in text_right):
                    chosen = None
                    chosen_tag = ""
                    if "隨機副本" in text_left:
                        chosen = self.left_region
                        chosen_tag = "random_left"
                    elif "隨機副本" in text_right:
                        chosen = self.right_region
                        chosen_tag = "random_right"
                    else:
                        chosen = self.right_region
                        chosen_tag = "right"

                    ok_enter, _ = self._tap_region_center(ctx, chosen, chosen_tag)
                    if ok_enter:
                        self.stat_exit_without_final += 1
                        _ = self._simple_exit_sequence(ctx)
                    return TaskResult(acted=ok_enter, message=self._stat_line())

                # 判定為奶牛關後，啟動『當輪迴圈』
                while True:
                    time.sleep(40)

                    # 如果上一輪點擊的是賜福關，代表有能力要點
                    if (text_right == "賜福關" and chosen_tag  == "right"):
                        self.logger.info(f"賜福關，點擊能力")
                        ok_enter, _ = self._tap_region_center(ctx, chosen, chosen_tag)
                        time.sleep(1.0)

                    try:
                        capture_screen(ctx.screenshot_path, device_id=ctx.device_id)
                    except Exception:
                        pass

                    try:
                        show_region(ctx.screenshot_path, self.left_region, "region_level_left.png")
                        show_region(ctx.screenshot_path, self.right_region, "region_level_right.png")
                    except Exception:
                        pass

                    left_raw = find_text(ctx.screenshot_path, self.left_region)
                    right_raw = find_text(ctx.screenshot_path, self.right_region)
                    text_left = _normalize_text(left_raw)
                    text_right = _normalize_text(right_raw)
                    self.logger.info(f"左區域文字='{text_left}'")
                    self.logger.info(f"右區域文字='{text_right}'")

                    # 有奶牛關就點奶牛關（左優先、右其次）
                    if self.target_text in text_left:
                        ok, msg = self._tap_region_center(ctx, self.left_region, "cow_left")
                        if ok:
                            round_stars += STAR_BY_LABEL.get("奶牛關", 4)
                            round_cow_hits += 1
                            self.cow_hits += 1
                            try:
                                self.logger.info(f"[ACTION] {msg}")
                                self.logger.info(f"[ROUND] stars={round_stars} cows={round_cow_hits}")
                            except Exception:
                                pass
                        # 回到當輪迴圈頂端，持續偵測
                        continue
                    if self.target_text in text_right:
                        ok, msg = self._tap_region_center(ctx, self.right_region, "cow_right")
                        if ok:
                            round_stars += STAR_BY_LABEL.get("奶牛關", 4)
                            round_cow_hits += 1
                            self.cow_hits += 1
                            try:
                                self.logger.info(f"[ACTION] {msg}")
                                self.logger.info(f"[ROUND] stars={round_stars} cows={round_cow_hits}")
                            except Exception:
                                pass
                        # 回到當輪迴圈頂端，持續偵測
                        continue

                    # 沒有奶牛關
                    chosen = None
                    chosen_tag = ""
                    if "隨機副本" in text_left:
                        chosen = self.left_region
                        chosen_tag = "random_left"
                        round_stars += STAR_BY_LABEL.get("隨機副本", 4)
                    elif "隨機副本" in text_right:
                        chosen = self.right_region
                        chosen_tag = "random_right"
                        round_stars += STAR_BY_LABEL.get("隨機副本", 4)
                    else:
                        chosen = self.right_region
                        chosen_tag = "right"
                        round_stars += STAR_BY_LABEL.get(text_right, 4)

                    try:
                        self.logger.info(f"[ROUND] stars={round_stars} cows={round_cow_hits}")
                    except Exception:
                        pass

                    ok_enter, _ = self._tap_region_center(ctx, chosen, chosen_tag)

                    # 星數達標則點最終關卡，據『當輪奶牛關數量』決策
                    if round_stars >= 10:
                        # 點最終關
                        final_region = self.final_stage_region or self.right_region
                        _msgf = self._tap_region_center(ctx, final_region, "final_stage")
                        self.logger.info(f"[ACTION] 動作: {_msgf}")

                        if round_cow_hits <= 1:
                            self.logger.info(f"[EXIT] 動作: 只遇到一次奶牛關，重新開始")
                            # 只遇到一次奶牛關：退出並重新來過（從 421 流程再跑一輪）
                            self.stat_exit_without_final += 1
                            _ = self._simple_exit_sequence(ctx)
                            # 跳出當輪，回到外層重新開始一輪（重置 round_*）
                            break
                        else:
                            # 如果達兩次以上則回到等待1分鐘
                            time.sleep(60)

                            # 點擊確定離開
                            m_fc = self._tap_region_center(ctx, self.fail_confirm_region, "success_confirm")
                            self.logger.info(f"[EXIT] 動作: {m_fc}")
                            self.stat_cow_twice += 1
                            try:
                                self.logger.info(self._stat_line())
                            except Exception:
                                pass
                            break
                    else:
                        # 星數未達：離開關卡後繼續當輪偵測
                        if ok_enter:
                            continue


                # 當輪 break（只遇一次，已退出）→ 回到外層 while True 重新來過
                continue

        except Exception:
            # 只輸出統計，不輸出錯誤堆疊
            return TaskResult(acted=False, message=self._stat_line())
