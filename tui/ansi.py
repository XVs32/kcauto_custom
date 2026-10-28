"""kcauto 日誌行的 ANSI 解析。純 Python,不依賴 Rich / Textual。

沿用舊 CUI 的顏色約定(``cui/util.py: print_log``):
    91 → 錯誤、92 → 狀態、93 → 警告、94 → log;其餘一律視為 debug(預設色)。

舊版用 ``chunk.isdigit()`` 判斷,遇到 ``91;1`` 這類複合參數會把它當成文字印出來;
這裡正確拆解參數,並丟棄游標移動、OSC 標題等非顏色序列,避免日誌出現亂碼。
"""
from __future__ import annotations

import re

Segment = tuple[str, str]   # (文字, 樣式);樣式是 Rich 樣式字串,空字串 = 預設

ERROR_STYLE = "#e06c75"
STATUS_STYLE = "#98c379"
WARNING_STYLE = "#e5c07b"
LOG_STYLE = "#56b6c2"

SGR_STYLES = {
    "91": ERROR_STYLE,
    "92": STATUS_STYLE,
    "93": WARNING_STYLE,
    "94": LOG_STYLE,
}

# CSI:ESC [ 參數 中間字元 結尾字元;OSC:ESC ] ... (BEL 或 ESC \)
_CSI = re.compile(r"\x1b\[([0-9;?]*)([ -/]*[@-~])")
_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_STRAY_ESC = re.compile(r"\x1b")


def parse_ansi(text: str) -> list[Segment]:
    """把含 ANSI 序列的一行拆成 (文字, 樣式) 區段;相鄰同樣式區段會合併。"""
    text = _OSC.sub("", text)
    segments: list[Segment] = []
    style = ""
    pos = 0

    def add(chunk: str) -> None:
        chunk = _STRAY_ESC.sub("", chunk)
        if not chunk:
            return
        if segments and segments[-1][1] == style:
            segments[-1] = (segments[-1][0] + chunk, style)
        else:
            segments.append((chunk, style))

    for match in _CSI.finditer(text):
        add(text[pos:match.start()])
        pos = match.end()
        if match.group(2) != "m":
            continue                      # 非顏色序列:丟棄
        params = match.group(1).split(";") if match.group(1) else ["0"]
        for param in params:
            if param in ("", "0"):
                style = ""
            elif param in SGR_STYLES:
                style = SGR_STYLES[param]
            # 其他(粗體、底線、背景色、256 色…)忽略,維持目前樣式
    add(text[pos:])
    return segments


def plain_text(segments: list[Segment]) -> str:
    return "".join(text for text, _ in segments)
