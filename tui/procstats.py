"""行程資訊的格式化工具(狀態列用)。純 Python。"""
from __future__ import annotations

from typing import Sequence

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: Sequence[float], maximum: float = 100.0, width: int = 8) -> str:
    """最近 ``width`` 筆資料畫成迷你圖;資料不足時左側補空白,長度恆為 width。"""
    if width <= 0:
        return ""
    recent = list(values)[-width:]
    top = len(SPARK_CHARS) - 1
    chars = []
    for value in recent:
        if maximum <= 0:
            fraction = 0.0
        else:
            fraction = min(max(float(value) / maximum, 0.0), 1.0)
        chars.append(SPARK_CHARS[round(fraction * top)])
    return " " * (width - len(chars)) + "".join(chars)


def fmt_duration(seconds: float) -> str:
    """0:03:12 / 12:00:05 / 2d 03:00:00。"""
    total = max(int(seconds), 0)
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    clock = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{days}d {clock}" if days else clock


def fmt_bytes(count: float) -> str:
    """180M / 1.2G / 512K。"""
    value = float(max(count, 0))
    for unit in ("B", "K", "M", "G", "T"):
        if value < 1024 or unit == "T":
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.0f}{unit}" if value >= 100 else f"{value:.1f}{unit}".replace(".0", "")
        value /= 1024
    return f"{value:.0f}T"  # pragma: no cover
