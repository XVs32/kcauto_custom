_大道至簡。_

---

## 設定檔運作流程 (Config setting flow)

`kcauto_custom` 本質上是一個透過設定檔執行的獨立程式。

我們所使用的 CUI (命令列使用者介面) 僅僅是一個設定檔編輯器，  
它讓 `kcauto_custom` 的設定更直覺易懂，但並非必要存在。

你完全可以用記事本直接編輯設定檔，並以此來執行 `kcauto_custom`。

![image](https://github.com/XVs32/kcauto_custom/assets/16824564/6bd97995-62ba-4692-9c68-7b81315ecfbc)

---

## KCAuto 設定檔文件說明

## 概覽

KCAuto 使用 JSON 格式的設定檔來控制其行為。設定系統採用模組化設計，  
不同的區段分別控制自動化的不同面向。

所有的設定檔都必須是合法的 JSON 格式。

## 檔案格式

設定檔是包含點表記法 (dot-notation) 鍵值的 JSON 物件。  
每個鍵值都遵循 `<模組>.<設定>` 的模式。

### 基礎結構範例
```json
{
    "general.interaction_mode": "chrome_driver",
    "general.jst_offset": 0,
    "combat.enabled": true,
    "combat.sortie_map": "1-1",
    "expedition.enabled": false
}
```

## 設定模組

### 一般設定 (`general.*`)

控制基本的應用程式行為與瀏覽器互動。

#### `general.interaction_mode`
- **型別**: string
- **有效值**: `"chrome_driver"`, `"direct_control"`
- **預設值**: `"chrome_driver"`
- **說明**: 決定 `kcauto` 與瀏覽器互動的方式。  
Chrome driver 模式直接傳送控制訊號給瀏覽器，  
而 Direct control 模式則是控制滑鼠來與瀏覽器互動。

#### `general.jst_offset`
- **型別**: integer
- **有效範圍**: -20 ～ 20
- **預設值**: 0
- **說明**: 針對排程與時間基礎操作，與 JST (日本標準時) 的時差（以小時為單位）。

#### `general.chrome_dev_port`
- **型別**: integer
- **有效範圍**: 0 ～ 65535
- **預設值**: 9222
- **說明**: Chrome DevTools Protocol 連接用的連接埠號。  
若不清楚其用途，請勿更改。

#### `general.poi_api_port`
- **型別**: integer
- **有效範圍**: 0 ～ 65535
- **預設值**: 9223
- **說明**: POI API 轉送用的連接埠號。  
若不清楚其用途，請勿更改。

#### ~~`general.paused`~~ （待修復 (2025/07/17)）
- **型別**: boolean
- **預設值**: false
- **說明**: 是否以暫停狀態啟動 `kcauto`。

##### CUI使用者可透過[空白鍵](../Ch2)來暫停kcauto_custom

### 戰鬥設定 (`combat.*`)

控制出擊與戰鬥行為。

#### `combat.enabled`
- **型別**: boolean
- **預設值**: false
- **說明**: 啟用或停用戰鬥模組。

#### `combat.sortie_map`
- **型別**: string
- **有效格式**: 像是 "1-1", "3-5", "6-4" 的地圖表記，或 "auto"
- **預設值**: "1-1"
- **說明**: 指定出擊地圖。使用 "auto" 進行地圖自動選擇。
- **範例**: `"1-1"`, `"3-5"`, `"E-1"`, `"auto"`

#### `combat.fleet_mode`
- **型別**: string
- **有效值**: `"standard"`, `"strike"`, `"tcf"`, `"ctf"`, `"stf"`
- **預設值**: `"standard"`
- **說明**: 定義戰鬥的艦隊編制模式。
  - `"standard"`: 單艦隊
  - `"strike"`: 打擊部隊（使用第 3 艦隊）
  - `"tcf"`: 輸送連合艦隊
  - `"ctf"`: 空母機動部隊
  - `"stf"`: 水上打擊部隊

#### `combat.fleet_presets`
- **型別**: array of integers or strings
- **有效值**: 1 ～ 15 或 `"auto"`
- **預設值**: `[]`
- **說明**: 用於戰鬥的艦隊編制記錄編號列表。使用 `"auto"` 進行自動艦隊選擇。
- **範例**: `[1, 2, 3]`, `["auto"]`

#### `combat.check_fatigue`
- **型別**: boolean
- **預設值**: true
- **說明**: 在戰鬥操作期間是否檢查艦娘疲勞度。

#### `combat.check_lbas_fatigue`
- **型別**: boolean
- **預設值**: true
- **說明**: 在戰鬥期間是否檢查基地航空隊 (LBAS) 的疲勞度。

#### `combat.clear_stop`
- **型別**: boolean
- **預設值**: false
- **說明**: 當地圖攻略完成時，是否停止戰鬥操作。

#### `combat.port_check`
- **型別**: boolean
- **預設值**: false
- **說明**: 出擊前是否檢查母港容量。

#### `combat.reserve_repair_dock`
- **型別**: boolean
- **預設值**: true
- **說明**: 是否保留修理船塢槽位以供緊急修理使用。

#### `combat.retreat_limit`
- **型別**: integer
- **有效值**: 0 ～ 4（損傷狀態等級）
- **預設值**: 4
- **說明**: 撤退艦娘的損傷閾值。數值對應損傷狀態：
  - 0: 無傷
  - 1: 擦傷
  - 2: 小破
  - 3: 中破
  - 4: 大破

#### `combat.repair_limit`
- **型別**: integer
- **有效值**: 0 ～ 4（損傷狀態等級）
- **預設值**: 3
- **說明**: 自動修理艦娘的損傷閾值。

#### `combat.repair_bucket_threshold`
- **型別**: integer
- **預設值**: 500
- **說明**: 在將高速修復材（桶）用於修理前，需維持的最小數量。

#### `combat.repair_timelimit_hours`
- **型別**: integer
- **預設值**: 0
- **說明**: 在使用桶之前，等待自然修理的最大時間（以小時為單位）。

#### `combat.repair_timelimit_minutes`
- **型別**: integer
- **有效範圍**: 0 ～ 59
- **預設值**: 0
- **說明**: 在使用桶之前，等待自然修理的最大時間（以分鐘為單位）。

#### `combat.retreat_points`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 艦隊應該撤退的節點名稱列表。
- **範例**: `["A", "B", "C"]`

#### `combat.push_nodes` (**!!DANGER!! 大破進擊警告!!**)
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 無論損傷程度如何，艦隊都應繼續進擊的節點名稱列表。
- **範例**: `["D", "Z"]`

#### `combat.node_selects`
- **型別**: array of strings
- **格式**: `"source_node>target_node"`
- **預設值**: `[]`
- **說明**: 指定分支點處的節點選擇。
- **範例**: `["A>B", "C>D"]`

#### `combat.node_formations`
- **型別**: array of strings
- **格式**: `"node:formation"`
- **有效陣型**: `line_ahead`, `double_line`, `diamond`, `echelon`, `line_abreast`, `vanguard`, `combined_fleet_1`, `combined_fleet_2`, `combined_fleet_3`, `combined_fleet_4`
- **預設值**: `[]`
- **說明**: 指定特定節點使用的陣型。
- **範例**: `["A:line_ahead", "B:double_line"]`

#### `combat.node_night_battles`
- **型別**: array of strings
- **格式**: `"node:True/False"`
- **預設值**: `[]`
- **說明**: 指定是否在特定節點進行夜戰。
- **範例**: `["X:True", "A:False"]`

#### `combat.node_smoke`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 應該使用煙幕的節點列表。
- **範例**: `["A", "B"]`

#### `combat.lbas_groups`
- **型別**: array of integers
- **有效值**: `1`, `2`, `3`
- **預設值**: `[]`
- **說明**: 要啟動的基地航空隊 (LBAS) 組別列表。
- **範例**: `[1, 2]`

#### `combat.lbas_group_1_nodes`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: LBAS 第 1 組的目標節點。必須指定 0 個或 2 個節點。
- **範例**: `["A", "A"]`

#### `combat.lbas_group_2_nodes`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: LBAS 第 2 組的目標節點。必須指定 0 個或 2 個節點。

#### `combat.lbas_group_3_nodes`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: LBAS 第 3 組的目標節點。必須指定 0 個或 2 個節點。

#### `combat.override`
- **型別**: boolean
- **預設值**: false
- **說明**: 是否允許在執行期間覆寫設定。

### 遠征設定 (`expedition.*`)

控制遠征管理與資源收集。

#### `expedition.enabled`
- **型別**: boolean
- **預設值**: true
- **說明**: 啟用或停用遠征模組。

#### `expedition.fleet_2`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 分配給第 2 艦隊的遠征 ID 列表。自動選擇請使用 `"auto"`。
- **範例**: `[2, 4, 5]`, `["auto"]`

#### `expedition.fleet_3`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 分配給第 3 艦隊的遠征 ID 列表。

#### `expedition.fleet_4`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 分配給第 4 艦隊的遠征 ID 列表。

#### `expedition.fleet_preset`
- **型別**: string or null
- **有效值**: `"auto"` or null
- **預設值**: null
- **說明**: 遠征的艦隊預設模式。目前僅支援 `"auto"` 或 `null`。

#### `expedition.desire_oil`
- **型別**: integer
- **有效範圍**: 0 ～ 350000
- **預設值**: 350000
- **說明**: 透過遠征維持的目標燃料量。

#### `expedition.desire_ammo`
- **型別**: integer
- **有效範圍**: 0 ～ 350000
- **預設值**: 350000
- **說明**: 維持的目標彈藥量。

#### `expedition.desire_steel`
- **型別**: integer
- **有效範圍**: 0 ～ 350000
- **預設值**: 350000
- **說明**: 維持的目標鋼材量。

#### `expedition.desire_bauxite`
- **型別**: integer
- **有效範圍**: 0 ～ 350000
- **預設值**: 350000
- **說明**: 維持的目標鋁土量。

#### `expedition.desire_bucket`
- **型別**: integer
- **有效範圍**: 0 ～ 3000
- **預設值**: 3000
- **說明**: 維持的目標高速修復材（桶）數量。

### 演習設定 (`pvp.*`)

控制 PvP (演習) 戰鬥行為。

#### `pvp.enabled`
- **型別**: boolean
- **預設值**: false
- **說明**: 啟用或停用 PvP 戰鬥。若戰鬥艦隊處於連合艦隊模式，則無法啟用。

#### `pvp.fleet_preset`
- **型別**: integer, string, or null
- **有效值**: 1 ～ 15, `"auto"`, or null
- **預設值**: 0
- **說明**: 用於 PvP 戰鬥的艦隊預設。自動選擇請使用 `"auto"`。

### 任務設定 (`quest.*`)

控制任務管理。

#### `quest.enabled`
- **型別**: boolean
- **預設值**: true
- **說明**: 啟用或停用自動任務管理。

#### `quest.quests`
- **型別**: array of strings
- **預設值**: `[]`
- **說明**: 自動受理並完成的任務 ID 列表。
- **範例**: `["Bd1", "Bd2", "Bw1", "C2", "D2"]`

### 工廠設定 (`factory.*`)

控制艦娘建造與裝備開發。

#### `factory.enabled`
- **型別**: boolean
- **預設值**: false
- **說明**: 啟用或停用工廠操作。

#### `factory.build_recipe`
- **型別**: array of 4 integers
- **預設值**: `[30, 30, 30, 30]`
- **說明**: 建造配方 [燃料, 彈藥, 鋼材, 鋁土]。

#### `factory.build_secretary`
- **型別**: integer
- **預設值**: 1234
- **說明**: 用於艦娘建造的秘書艦 ID。

#### `factory.develop_recipe`
- **型別**: array of 4 integers
- **預設值**: `[10, 10, 10, 10]`
- **說明**: 開發配方 [燃料, 弾薬, 鋼材, 鋁土]。

#### `factory.develop_secretary`
- **型別**: integer
- **預設值**: 1234
- **說明**: 用於裝備開發的秘書艦 ID。

### 排程器設定 (`scheduler.*`)

控制時間基礎的自動化規則。

#### `scheduler.enabled`
- **型別**: boolean
- **預設值**: true
- **說明**: 啟用或停用排程系統。

#### `scheduler.rules`
- **型別**: array of strings
- **格式**: `"condition:value:action:module"` or `"condition:value:action:module:extra"`
- **預設值**: `[]`
- **說明**: 基於條件觸發動作的排程規則列表。
- **範例**: 
  ```json
  [
    "time:0230:stop:kcauto",
    "sorties_run:15:stop:combat"
  ]
  ```

### 被動修理設定 (`passive_repair.*`)

控制自動修理船塢管理。

#### `passive_repair.enabled`
- **型別**: boolean
- **預設值**: false
- **說明**: 啟用或停用被動修理管理。

#### `passive_repair.repair_threshold`
- **型別**: integer
- **有效值**: 1 ～ 4（損傷狀態等級）
- **預設值**: 1
- **說明**: 觸發被動修理所需的最小損傷等級。

#### `passive_repair.slots_to_reserve`
- **型別**: integer
- **預設值**: 2
- **說明**: 為緊急修理保留的修理船塢槽位數。

### 艦娘スイッチャー設定 (`ship_switcher.*`)

控制自動艦娘切換與管理。

#### `ship_switcher.enabled`
- **型別**: boolean
- **預設值**: false
- **說明**: 啟用或停用自動艦娘切換。

#### `ship_switcher.slots`
- **型別**: object
- **預設值**: `{}`
- **說明**: 每個艦隊槽位的艦娘切換規則配置。

### 活動重置設定 (`event_reset.*`)

控制活動地圖周回的重置行為。

#### `event_reset.enabled`
- **型別**: boolean
- **預設值**: false
- **說明**: 啟用或停用活動重置功能。

#### `event_reset.farm_difficulty`
- **型別**: integer
- **有效值**: 1 ～ 4（難易度等級）
- **預設值**: 2
- **說明**: 用於周回的難易度等級。

#### `event_reset.reset_difficulty`
- **型別**: integer
- **有效值**: 1 ～ 4（難易度等級）
- **預設值**: 3
- **說明**: 周回後要重置到的難易度等級。

#### `event_reset.frequency`
- **型別**: integer
- **預設值**: 3
- **說明**: 觸發重置前的周回次數。

---

## 最佳實踐 (Best Practices)

1. **簡單開始**: 從基本設定開始，逐步增加複雜度
2. **循序測試**: 一次啟用一個模組來驗證行為
3. **使用模板**: 以提供的模板為基礎進行設定
4. **驗證設定**: 確保所有數值都在有效範圍與格式內
5. **監控日誌**: 查看日誌中的設定警告與錯誤
6. **備份設定檔**: 妥善保留正常運作設定檔的備份

---

## 設定範例

### 基本戰鬥設定
```json
{
    "general.interaction_mode": "chrome_driver",
    "general.jst_offset": 0,
    "combat.enabled": true,
    "combat.sortie_map": "1-1",
    "combat.fleet_mode": "standard",
    "combat.fleet_presets": [1],
    "combat.check_fatigue": true,
    "combat.retreat_limit": 3,
    "expedition.enabled": false,
    "pvp.enabled": false,
    "quest.enabled": false
}
```

### 遠征周回設定
```json
{
    "general.interaction_mode": "chrome_driver",
    "combat.enabled": false,
    "expedition.enabled": true,
    "expedition.fleet_2": ["2", "3"],
    "expedition.fleet_3": ["5", "6"],
    "expedition.fleet_4": ["37", "38"],
    "expedition.desire_oil": 300000,
    "expedition.desire_ammo": 300000,
    "expedition.desire_steel": 300000,
    "expedition.desire_bauxite": 300000,
    "quest.enabled": true,
    "quest.quests": ["Bd1", "Bd2", "Bd3"]
}
```

### 連合艦隊戰鬥設定
```json
{
    "combat.enabled": true,
    "combat.fleet_mode": "ctf",
    "combat.sortie_map": "6-4",
    "combat.fleet_presets": [1],
    "combat.lbas_groups": ["1", "2"],
    "combat.lbas_group_1_nodes": ["A", "A"],
    "combat.lbas_group_2_nodes": ["B", "Z"],
    "combat.node_formations": ["A:line_ahead", "Z:line_ahead"],
    "combat.node_night_battles": ["A:True"],
    "expedition.enabled": false,
    "pvp.enabled": false
}
```

### 自動模式設定
```json
{
    "combat.enabled": true,
    "combat.sortie_map": "auto",
    "combat.fleet_presets": ["auto"],
    "expedition.enabled": true,
    "expedition.fleet_preset": "auto",
    "expedition.fleet_2": ["auto"],
    "expedition.fleet_3": ["auto"],
    "expedition.fleet_4": ["auto"],
    "pvp.enabled": true,
    "pvp.fleet_preset": "auto"
}
```
