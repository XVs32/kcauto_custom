# kcauto_custom CUI(重寫版)— 階段 3

## 安裝與執行

```
pip install textual psutil   # Python 3.11
python -m tui                # 請在專案根目錄執行;預設讀 configs/config_cui.json
python -m tui --config PATH --template PATH --autostart
```

## 測試

```
python -m unittest discover -s tests -t . -v
```

- 純 Python 部分(schema、store、summaries)不需要 Textual。
- `tests/test_app.py` 需要 Textual,沙盒中沒有執行過,請務必在實際環境跑一次。
- 設 `KCAUTO_TEMPLATE=data/config/config_cui_template.json` 可檢查 schema 是否涵蓋實際模板。

## 目前可用

| 操作 | 作用 |
|---|---|
| 方向鍵 | 在方框間移動(焦點在日誌時改為捲動日誌) |
| `c e p u s f r h v g` | 直接跳到該方框 |
| Space / 點右下角 ON·OFF | 切換模組的 `enabled`;**焦點在日誌時改為暫停/繼續 kcauto** |
| 單擊 / 雙擊·Enter | 聚焦 / 開啟編輯器(階段 4,目前只顯示提示) |
| `a` | **套用**:存檔後(重新)啟動 kcauto。有 error 時不啟動 |
| `b` | 暫停/繼續 kcauto(任何位置) |
| `k` | 停止 kcauto(連同子行程) |
| `l` | 聚焦日誌;日誌因版面被隱藏時改為全螢幕日誌 |
| Esc | 離開日誌 / 全螢幕日誌 |
| 日誌上按 Enter | kcauto 輸出 `Press Enter to continue` 時送出 Enter |
| `w` / `q` | 存檔 / 離開(有未儲存修改或 kcauto 仍在執行時會詢問) |

## kcauto 行程控制(和舊版 CUI 的差異)

沿用:啟動指令(`./bin/kcauto_custom/kcauto_custom[.exe]`,找不到才用 Python)、
`--cli --cfg <名稱>`、ANSI 顏色約定(91 錯誤 / 92 狀態 / 93 警告 / 94 log)、
用 suspend/resume 暫停、`Press Enter to continue` 的偵測、重載 = 結束後重新啟動。

不同(皆為修正):
- **不會自動啟動**。舊版也是如此(啟動等同於「Reload config → Yes」),這裡改成明確的 `a`;
  需要自動啟動可加 `--autostart`。
- 結束時**連子行程一起結束**(舊版只 kill 主行程)。離開 CUI 時一定會清掉 kcauto,
  即使用 Ctrl+Q 或當機離開也一樣。
- 子行程設定 `PYTHONUNBUFFERED=1`、`PYTHONIOENCODING=utf-8`:日誌不會被管線緩衝延遲,
  Windows 上也不會因 locale 編碼而亂碼。
- Python 備援模式用 `sys.executable`,不依賴 PATH 上的 `python` / `python3`。
- ANSI 複合參數(例如 `91;1`)能正確解析,不會把控制碼印成文字。
- 日誌保留最近 3000 行;日誌被隱藏時不會無限累積記憶體。

狀態列顯示:執行狀態、執行時間、CPU 迷你圖與百分比、記憶體、等待 Enter 的提示。

## 響應式版面

| 條件 | 版面 |
|---|---|
| 橫向足夠(寬 ≥ 110) | 日誌在右側;方框依寬度自動 2 / 3 / 4 欄(約 110 / 144 / 178 欄起) |
| 橫向不足、直向足夠 | 日誌移到儀表板下方;方框 1~4 欄(每欄至少 34 欄寬) |
| 兩者都不足 | 隱藏日誌,方框佔滿 |

「直向足夠」= 方框區實際高度(依內容估算)+ 狀態列/提示列 + 日誌最小 8 列。
數值定義在 `tui/layout.py`,`theme.tcss` 必須同步,`tests/test_layout.py` 會檢查。

## 打包注意

`tui/theme.tcss` 必須隨程式一起打包。PyInstaller 範例:

```
--add-data "kcauto/tui/theme.tcss:tui"      # Windows 用分號:  ...theme.tcss;tui
```
