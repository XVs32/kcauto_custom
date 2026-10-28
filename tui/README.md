# kcauto_custom CUI(重寫版)— 階段 4

## 安裝與執行

```
pip install "textual>=0.86" psutil   # Python 3.11
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
| 單擊 / 雙擊·Enter | 聚焦 / 開啟全螢幕編輯器 |
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


## 編輯器(階段 4)

在儀表板按 Enter 或雙擊方框開啟,直接停在該模組。所有修改立即寫入記憶體並同步到儀表板,
按 `w` 才會存檔。編輯期間 kcauto 的日誌仍會累積;若它在等待 Enter,請先 Esc 回儀表板。

| 按鍵 | 作用 |
|---|---|
| ↑ ↓ / PgUp PgDn / Home End | 在欄位間移動 |
| ← | 回到左側模組清單(視窗 < 72 欄時,← → 改為切換模組) |
| `c e p u s f r h v g o` | 跳到該模組(`o` = 未知 key) |
| `[` `]` | 上一個 / 下一個模組 |
| Enter / 單擊 | 編輯(依型別開對應的控制項) |
| Space | 布林切換、enum 循環;其他型別等同 Enter |
| `+` `-` | 整數微調、enum 循環 |
| `d` | 還原為預設值 |
| `z` | 還原為上次存檔的值 |
| `/` | 搜尋全部欄位(key、標籤、說明) |
| `w` | 存檔(有 error 時拒絕) |
| Esc | 離開編輯器 |

欄位列左側:`✖` 錯誤、`⚠` 警告、`!` 高風險;`*` 代表已修改。底部面板顯示 key、說明、型別、預設值、目前值與問題。

### 各型別的控制項

| 欄位 | 控制項 |
|---|---|
| bool | Space 直接切換 |
| enum | 選單(Space 循環);nullable 的有 `null` 選項 |
| int | 輸入框,↑↓ 微調,即時顯示範圍錯誤;範圍小的欄位在列上畫量表 |
| `factory.*_secretary` | 輸入框;純數字存成整數,其他存成字串 |
| `pvp.fleet_preset` | 格子單選:1~15、auto、null、0 |
| `combat.fleet_presets` | 格子複選(記錄點選順序);若既有值有重複項,改用清單編輯器 |
| 字串陣列 | 清單編輯器:輸入框可一次貼多個(逗號/空白分隔);↓ 進清單,Enter 修改該項,Delete/x 移除 |
| `combat.node_selects` / `node_formations` / `node_night_battles` | 兩欄表格(陣型、夜戰用循環選單) |
| `scheduler.rules` | 五欄表格(extra 可省略),只驗結構 |
| `*.build_recipe` / `develop_recipe` | 四個數字欄(Tab 換欄) |
| `quest.quests` | 依前綴分組的勾選清單(需 `data/` 下有檔名含 quest 的 JSON;找不到時退回清單編輯器) |
| `ship_switcher.slots`、未知 key | JSON 編輯器(Ctrl+S 套用),即時檢查語法 |
| `combat.push_nodes` | 新增節點時會跳出二次確認(y / n);移除不需確認 |

對話框通用:輸入框內 Enter = 新增/確認該筆,**空白時 Enter = OK**;Esc = 取消。
