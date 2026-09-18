_人無癖不可與交，以其無深情也。_

---

## 閱讀前須知 (Before you read)
在 [Ch5 設定檔 (Configuration File)](../Ch5) 有專屬的設定說明頁面。  
你可以在那裡找到使用者設定檔中各個選項的詳細解釋。  
如果你發現這邊都是一堆看不懂的專有名詞，去看那邊就對了。

---

## 海域專屬出擊設定 (`combat.override`)

在大多數情況下，`kcauto_custom` 都會使用同一套通用的出擊邏輯。  

* 防空時使用輪形陣
* 反潛時使用單橫陣
* 活動期間使用警戒陣而非單縱陣
* 為了 S 勝利，BOSS 戰時突入夜戰
* 諸如此類

但在其他某些地圖中，我們確實需要：

* 選擇節點（例如：在 5-3 中，我們需要選擇從 K 點走到 O 點） 
* 設定基地航空隊 (LBAS)（例如：在 6-4、6-5、7-4 等地圖）
* 嘗試使用 Nelson 摸  
* 嘗試使用煙幕  
* 諸如此類

問題是，這些特殊設定在其他地圖上根本不適用，而「海域專屬設定 (Map specified setting)」就是為了解決這個問題。

---

### 如果我不需要這個功能呢？
請將你設定檔中的 `combat.override` 設為 `true`。  

---

出擊設定共有 3 個層級：

1. 使用者設定檔（你平常在使用的設定檔，如果使用 CUI 的話就是 `configs/config_cui.json`）
2. 預設 `data/config/combat/default.json`（一般地圖的預設出擊設定）
3. 海域專屬設定（例如：`data/config/combat/B-4-5.json`）（專為特定地圖製作的出擊設定）

優先順序為：`使用者設定` < `預設` < `海域專屬設定`  
此外，你**只能**從使用者設定檔中定義 `enabled`、`fleet_presets` 和 `sortie_map`（在下圖中顯示為 STATIC 的部分）。
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/0ee2f28f-7b6a-43cf-90bd-906f016da836)

你可以隨意編輯或在 `data/config/combat` 資料夾下新增配置。  
只要你自己設定檔中的 `combat.override` 設為 `false`，  
`kcauto` 就會自動讀取對應的特殊設定。

---

## `Sortie mode: Auto` -- 任務處理機制

***閱讀前須知：通常如果你使用的是 CUI，你並不需要手動設定這個部分。  
如果你不確定自己在做什麼，請不要編輯這裡的檔案，LOL***

現在我們已經告訴了 `kcauto-custom` 該用哪艘船，但 `kcauto-custom` 是如何主動挑選地圖並幫我完成任務的呢？

有 3 個檔案會影響任務與地圖的挑選行為（通常你不需要編輯它們）：

1. 你的設定檔（CUI 玩家為 `configs/config_cui.json`）
2. `data/quest/quest.json`
3. `data/quest/quest_priority.json`

我們先來看一下設定檔：

```json
	"quest.enabled":	true,       # 啟用任務模組
	"quest.quests":	["Bd1", "Bd2", "Bd3", "Bd4", "Bd5", "Bd6", "Bd7", "Bd8", "Bw1", "Bw2", "Bw3", "Bw4", "Bw5", "Bw7", "Bw8", "Bw9", "Bw10", "Bm2", "Bm3", "Bm4", "Bm5", "Bm6", "Bm8", "Bq1", "Bq3", "Bq4", "Bq8", "Bq9", "Bq10", "Bq11", "Bq12", "C2", "C3", "C4", "C8", "C16", "C29", "D2", "D3", "D4", "D9", "D11", "D22", "D24", "E3", "E4", "F5", "F6", "F7", "F8"]
	# kcauto-custom 將嘗試完成的任務列表
```

`kcauto-custom` 只會處理列在 `quest.quests` 中的任務。  

下一個是 `data/quest/quest.json`，這個檔案包含任務的詳細資訊。同樣地，通常你需要編輯它。

```json

  "Bd1": {                         # 任務代號名稱
    "id": 201,                     # 任務 ID
    "type": "daily",               # 任務類型
    "intervals": [1, 0, 0],        # kcauto-custom 檢查任務是否完成的間隔，順序為 [出擊, 演習, 遠征]
    "recommended_map": ["1-1"]     # 如果無法從 KC3 收集到資訊，kcauto-custom 預設會出擊的地圖
  }

```

最後一個是 `data/quests/sorite_quest_priority.json`，它定義了當玩家處於 `Sortie mode: Auto` 時，`kcauto-custom` 會優先執行哪些任務。
```json
{

  "time_limited": [
    "2412B5",
    "2509B5"
  ],
  "exact_ship_and_map": [
    "Bm1",
   ．．．
    "By15"
  ],
  "exact_ship_type_and_map": [
    "Bm3",
．．．
    "By11"
  ],
  "any_ship_with_exact_map": [
    "Bm8",
．．．
    "Bq10"
  ],
  "exact_area": [
    "Bw6",
    "Bw7"
  ],
  "exact_enemy_type": [
    "Bw2",
．．．
    "Bw3"
  ],
  "any_sortie": [
    "Bd1",
．．．
    "Bw1"
  ],
  "low_priority": [
    "Bd7"
  ]
}
```

這裡的優先順序為：`日常任務 (Daily)` > `週常任務 (Weekly)` > `月常任務 (Monthly)` > `季常任務 (Quarterly)` > `年常任務 (Yearly)` > `低優先度 (Low priority)`

---
