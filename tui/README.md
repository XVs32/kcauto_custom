# kcauto_custom CUI(重寫版)— 階段 2

## 安裝與執行

```
pip install textual          # Python 3.11
python -m tui                # 在 repo 根目錄;預設讀 configs/config_cui.json
python -m tui --config PATH --template PATH
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
| 方向鍵 | 在方框間移動 |
| `c e p u s f r h v g` | 直接跳到該方框 |
| Space / 點右下角 ON·OFF | 切換模組的 `enabled` |
| 單擊 | 聚焦 |
| 雙擊 / Enter | 開啟編輯器(階段 4,目前只會顯示提示) |
| `w` | 存檔(有 error 時拒絕) |
| `q` | 離開(有未儲存修改時詢問) |

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
