"""ANSI parsing for kcauto log lines. Pure Python, no Rich / Textual dependency.

Keeps the colour convention of the old CUI (``cui/util.py: print_log``):
    91 → error, 92 → status, 93 → warning, 94 → log; anything else is debug (default colour).

The old code used ``chunk.isdigit()``, so compound parameters such as ``91;1`` were printed
as text; here the parameters are parsed properly, and non-colour sequences (cursor movement,
OSC titles, ...) are dropped so the log never shows garbage.
"""

from __future__ import annotations

import re

Segment = tuple[
    str, str
]  # (text, style); style is a Rich style string, empty string = default

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

# CSI: ESC [ params intermediates final; OSC: ESC ] ... (BEL or ESC \)
_CSI = re.compile(r"\x1b\[([0-9;?]*)([ -/]*[@-~])")
_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_STRAY_ESC = re.compile(r"\x1b")


def parse_ansi(text: str) -> list[Segment]:
    """Split a line containing ANSI sequences into (text, style) segments; adjacent segments with the same style are merged."""
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
        add(text[pos : match.start()])
        pos = match.end()
        if match.group(2) != "m":
            continue  # Non-colour sequences: dropped
        params = match.group(1).split(";") if match.group(1) else ["0"]
        for param in params:
            if param in ("", "0"):
                style = ""
            elif param in SGR_STYLES:
                style = SGR_STYLES[param]
            # Others (bold, underline, background, 256 colours, ...) are ignored; keep the current style
    add(text[pos:])
    return segments


def plain_text(segments: list[Segment]) -> str:
    return "".join(text for text, _ in segments)
