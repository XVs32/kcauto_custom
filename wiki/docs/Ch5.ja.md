_大道至簡。_

---

## 設定フロー (Config setting flow)

`kcauto_custom` は基本的に、設定ファイルのみで動作するプログラムです。

CUI (コマンドラインユーザーインターフェース) は、`kcauto_custom` を使いやすくするための設定ファイルエディタであり、必須ではありません。

メモ帳で設定ファイルを編集し、それを使用して `kcauto_custom` を実行することも可能です。

![image](https://github.com/XVs32/kcauto_custom/assets/16824564/6bd97995-62ba-4692-9c68-7b81315ecfbc)

---

## KCAuto 設定ファイルドキュメント

## 概要

KCAuto は挙動を制御するために JSON 設定ファイルを使用します。設定システムはモジュール式で、自動化の各側面を異なるセクションで制御します。

すべての設定ファイルは有効な JSON 形式である必要があります。

## ファイル形式

設定ファイルはドット表記のキーを持つ JSON オブジェクトです。  
各キーは `<モジュール>.<設定>` というパターンに従います。

### 基本構造の例
```json
{
    "general.interaction_mode": "chrome_driver",
    "general.jst_offset": 0,
    "combat.enabled": true,
    "combat.sortie_map": "1-1",
    "expedition.enabled": false
}
```

## 設定モジュール

### 一般設定 (`general.*`)

基本的なアプリケーションの挙動とブラウザとのインタラクションを制御します。

#### `general.interaction_mode`
- **型**: string
- **有効な値**: `"chrome_driver"`, `"direct_control"`
- **デフォルト**: `"chrome_driver"`
- **説明**: `kcauto` がブラウザとどのようにインタラクションするかを決定します。  
Chrome driver モードは制御信号をブラウザに直接送信し、Direct control モードはマウスを操作してブラウザとインタラクションします。

#### `general.jst_offset`
- **型**: integer
- **有効な範囲**: -20 ～ 20
- **デフォルト**: 0
- **説明**: スケジューリングや時間ベースの操作のための、JST (日本標準時) からの時差（時間単位）。

#### `general.chrome_dev_port`
- **型**: integer
- **有効な範囲**: 0 ～ 65535
- **デフォルト**: 9222
- **説明**: Chrome DevTools Protocol 接続用のポート番号。  
仕組みを理解していない場合は変更しないでください。

#### `general.poi_api_port`
- **型**: integer
- **有効な範囲**: 0 ～ 65535
- **デフォルト**: 9223
- **説明**: POI API フォワーディング用のポート番号。  
仕組みを理解していない場合は変更しないでください。

#### ~~`general.paused`~~ （現在動作しません (2025/07/17)）
- **型**: boolean
- **デフォルト**: false
- **説明**: `kcauto` を一時停止状態で起動するかどうか。
 
##### CUIでは[スペースキー](../Ch2)を押すことでkcautoを一時停止できます

### 戦闘設定 (`combat.*`)

出撃と戦闘の挙動を制御します。

#### `combat.enabled`
- **型**: boolean
- **デフォルト**: false
- **説明**: 戦闘モジュール全体を有効/無効にします。

#### `combat.sortie_map`
- **型**: string
- **有効な形式**: "1-1"、"3-5"、"6-4" などのマップ表記、または "auto"
- **デフォルト**: "1-1"
- **説明**: 出撃するマップを指定します。自動マップ選択には "auto" を使用してください。
- **例**: `"1-1"`, `"3-5"`, `"E-1"`, `"auto"`

#### `combat.fleet_mode`
- **型**: string
- **有効な値**: `"standard"`, `"strike"`, `"tcf"`, `"ctf"`, `"stf"`
- **デフォルト**: `"standard"`
- **説明**: 戦闘用の艦隊編成モードを定義します。
  - `"standard"`: 単艦隊
  - `"strike"`: 打撃部隊（第 3 艦隊を使用）
  - `"tcf"`: 輸送連合艦隊
  - `"ctf"`: 空母機動部隊
  - `"stf"`: 水上打撃部隊

#### `combat.fleet_presets`
- **型**: array of integers or strings
- **有効な値**: 1 ～ 15 または `"auto"`
- **デフォルト**: `[]`
- **説明**: 戦闘に使用する艦隊編成記録番号のリスト。自動選択には `"auto"` を使用してください。
- **例**: `[1, 2, 3]`, `["auto"]`

#### `combat.check_fatigue`
- **型**: boolean
- **デフォルト**: true
- **説明**: 戦闘操作中に艦娘の疲労度を確認するかどうか。

#### `combat.check_lbas_fatigue`
- **型**: boolean
- **デフォルト**: true
- **説明**: 戦闘中に基地航空隊 (LBAS) の疲労度を確認するかどうか。

#### `combat.clear_stop`
- **型**: boolean
- **デフォルト**: false
- **説明**: マップ攻略完了時に戦闘操作を停止するかどうか。

#### `combat.port_check`
- **型**: boolean
- **デフォルト**: false
- **説明**: 出撃前に母港の空き容量を確認するかどうか。

#### `combat.reserve_repair_dock`
- **型**: boolean
- **デフォルト**: true
- **説明**: 緊急修理用に修理ドックのスロットを予約するかどうか。

#### `combat.retreat_limit`
- **型**: integer
- **有効な値**: 0 ～ 4（ダメージ状態レベル）
- **デフォルト**: 4
- **説明**: 撤退するための艦娘のダメージ閾値。値はダメージ状態に対応：
  - 0: 無傷
  - 1: 小破（かすり傷）
  - 2: 小破
  - 3: 中破
  - 4: 大破

#### `combat.repair_limit`
- **型**: integer
- **有効な値**: 0 ～ 4（ダメージ状態レベル）
- **デフォルト**: 3
- **説明**: 自動的に修理する艦娘のダメージ閾値。

#### `combat.repair_bucket_threshold`
- **型**: integer
- **デフォルト**: 500
- **説明**: 修理に使用する前に維持しておくべき高速修復材（バケツ）の最小数。

#### `combat.repair_timelimit_hours`
- **型**: integer
- **デフォルト**: 0
- **説明**: バケツを使用する前に自然修理を待つ最大時間（時間単位）。

#### `combat.repair_timelimit_minutes`
- **型**: integer
- **有効な範囲**: 0 ～ 59
- **デフォルト**: 0
- **説明**: バケツを使用する前に自然修理を待つ最大時間（分単位）。

#### `combat.retreat_points`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: 艦隊が撤退すべきノード名のリスト。
- **例**: `["A", "B", "C"]`

#### `combat.push_nodes` (**!!DANGER!! 大破進撃警告!!**)
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: ダメージに関係なく進撃すべきノード名のリスト。
- **例**: `["D", "Z"]`

#### `combat.node_selects`
- **型**: array of strings
- **形式**: `"source_node>target_node"`
- **デフォルト**: `[]`
- **説明**: 分岐点でのノード進行先の選択を指定します。
- **例**: `["A>B", "C>D"]`

#### `combat.node_formations`
- **型**: array of strings
- **形式**: `"node:formation"`
- **有効な陣形**: `line_ahead`, `double_line`, `diamond`, `echelon`, `line_abreast`, `vanguard`, `combined_fleet_1`, `combined_fleet_2`, `combined_fleet_3`, `combined_fleet_4`
- **デフォルト**: `[]`
- **説明**: 特定のノードで使用する陣形を指定します。
- **例**: `["A:line_ahead", "B:double_line"]`

#### `combat.node_night_battles`
- **型**: array of strings
- **形式**: `"node:True/False"`
- **デフォルト**: `[]`
- **説明**: 特定のノードで夜戦を行うかどうかを指定します。
- **例**: `["X:True", "A:False"]`

#### `combat.node_smoke`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: 煙幕を使用すべきノードのリスト。
- **例**: `["A", "B"]`

#### `combat.lbas_groups`
- **型**: array of integers
- **有効な値**: `1`, `2`, `3`
- **デフォルト**: `[]`
- **説明**: アクティブにする基地航空隊 (LBAS) グループのリスト。
- **例**: `[1, 2]`

#### `combat.lbas_group_1_nodes`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: LBAS グループ 1 のターゲットノード。必ず 0 個または 2 個のノードを指定してください。
- **例**: `["A", "A"]`

#### `combat.lbas_group_2_nodes`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: LBAS グループ 2 のターゲットノード。

#### `combat.lbas_group_3_nodes`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: LBAS グループ 3 のターゲットノード。

#### `combat.override`
- **型**: boolean
- **デフォルト**: false
- **説明**: 実行時の設定上書きを許可するかどうか。

### 遠征設定 (`expedition.*`)

遠征管理とリソース収集を制御します。

#### `expedition.enabled`
- **型**: boolean
- **デフォルト**: true
- **説明**: 遠征モジュールを有効/無効にします。

#### `expedition.fleet_2`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: 第 2 艦隊に割り当てる遠征 ID のリスト。自動選択には `"auto"` を使用してください。
- **例**: `[2, 4, 5]`, `["auto"]`

#### `expedition.fleet_3`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: 第 3 艦隊に割り当てる遠征 ID のリスト。

#### `expedition.fleet_4`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: 第 4 艦隊に割り当てる遠征 ID のリスト。

#### `expedition.fleet_preset`
- **型**: string or null
- **有効な値**: `"auto"` or null
- **デフォルト**: null
- **説明**: 遠征の艦隊プリセットモード。現在は `"auto"` または `null` のみサポート。

#### `expedition.desire_oil`
- **型**: integer
- **有効な範囲**: 0 ～ 350000
- **デフォルト**: 350000
- **説明**: 遠征で維持する目標燃料量。

#### `expedition.desire_ammo`
- **型**: integer
- **有効な範囲**: 0 ～ 350000
- **デフォルト**: 350000
- **説明**: 維持する目標弾薬量。

#### `expedition.desire_steel`
- **型**: integer
- **有効な範囲**: 0 ～ 350000
- **デフォルト**: 350000
- **説明**: 維持する目標鋼材量。

#### `expedition.desire_bauxite`
- **型**: integer
- **有効な範囲**: 0 ～ 350000
- **デフォルト**: 350000
- **説明**: 維持する目標ボーキサイト量。

#### `expedition.desire_bucket`
- **型**: integer
- **有効な範囲**: 0 ～ 3000
- **デフォルト**: 3000
- **説明**: 維持する目標高速修復材（バケツ）数。

### 演習設定 (`pvp.*`)

PvP（演習）の挙動を制御します。

#### `pvp.enabled`
- **型**: boolean
- **デフォルト**: false
- **説明**: PvP を有効/無効にします。戦闘艦隊が連合艦隊モードの場合は有効にできません。

#### `pvp.fleet_preset`
- **型**: integer, string, or null
- **有効な値**: 1 ～ 15, `"auto"`, or null
- **デフォルト**: 0
- **説明**: PvP 戦闘に使用する艦隊プリセット。自動選択には `"auto"` を使用してください。

### 任務設定 (`quest.*`)

デイリー/ウィークリー/マンスリー任務管理を制御します。

#### `quest.enabled`
- **型**: boolean
- **デフォルト**: true
- **説明**: 自動任務管理を有効/無効にします。

#### `quest.quests`
- **型**: array of strings
- **デフォルト**: `[]`
- **説明**: 自動的に受理・完了する任務 ID のリスト。
- **例**: `["Bd1", "Bd2", "Bw1", "C2", "D2"]`

### 工場設定 (`factory.*`)

建造と開発を制御します。

#### `factory.enabled`
- **型**: boolean
- **デフォルト**: false
- **説明**: 工場操作を有効/無効にします。

#### `factory.build_recipe`
- **型**: array of 4 integers
- **デフォルト**: `[30, 30, 30, 30]`
- **説明**: 建造レシピ [燃料, 弾薬, 鋼材, ボーキサイト]。

#### `factory.build_secretary`
- **型**: integer
- **デフォルト**: 1234
- **説明**: 建造で使用する秘書艦の艦娘 ID。

#### `factory.develop_recipe`
- **型**: array of 4 integers
- **デフォルト**: `[10, 10, 10, 10]`
- **説明**: 開発レシピ [燃料, 弾薬, 鋼材, ボーキサイト]。

#### `factory.develop_secretary`
- **型**: integer
- **デフォルト**: 1234
- **説明**: 開発で使用する秘書艦の艦娘 ID。

### スケジューラ設定 (`scheduler.*`)

時間ベースの自動化ルールを制御します。

#### `scheduler.enabled`
- **型**: boolean
- **デフォルト**: true
- **説明**: スケジューラシステムを有効/無効にします。

#### `scheduler.rules`
- **型**: array of strings
- **形式**: `"condition:value:action:module"` or `"condition:value:action:module:extra"`
- **デフォルト**: `[]`
- **説明**: 条件に基づいてアクションをトリガーするスケジューラルールのリスト。
- **例**: 
  ```json
  [
    "time:0230:stop:kcauto",
    "sorties_run:15:stop:combat"
  ]
  ```

### パッシブ修理設定 (`passive_repair.*`)

自動修理ドック管理を制御します。

#### `passive_repair.enabled`
- **型**: boolean
- **デフォルト**: false
- **説明**: パッシブ修理管理を有効/無効にします。

#### `passive_repair.repair_threshold`
- **型**: integer
- **有効な値**: 1 ～ 4（ダメージ状態レベル）
- **デフォルト**: 1
- **説明**: パッシブ修理をトリガーするために必要な最小ダメージレベル。

#### `passive_repair.slots_to_reserve`
- **型**: integer
- **デフォルト**: 2
- **説明**: 緊急修理用に確保しておく修理ドックのスロット数。

### 艦娘スイッチャー設定 (`ship_switcher.*`)

自動艦娘切り替えと管理を制御します。

#### `ship_switcher.enabled`
- **型**: boolean
- **デフォルト**: false
- **説明**: 自動艦娘切り替えを有効/無効にします。

#### `ship_switcher.slots`
- **型**: object
- **デフォルト**: `{}`
- **説明**: 艦隊スロットごとの艦娘切り替えルールの設定。

### イベントリセット設定 (`event_reset.*`)

周回のためのイベントマップリセットの挙動を制御します。

#### `event_reset.enabled`
- **型**: boolean
- **デフォルト**: false
- **説明**: イベントリセット機能を有効/無効にします。

#### `event_reset.farm_difficulty`
- **型**: integer
- **有効な値**: 1 ～ 4（難易度レベル）
- **デフォルト**: 2
- **説明**: 周回に使用する難易度レベル。

#### `event_reset.reset_difficulty`
- **型**: integer
- **有効な値**: 1 ～ 4（難易度レベル）
- **デフォルト**: 3
- **説明**: 周回後にリセットする難易度レベル。

#### `event_reset.frequency`
- **型**: integer
- **デフォルト**: 3
- **説明**: リセットをトリガーするまでの周回数。

---

## ベストプラクティス

1. **シンプルに始める**: 基本的な設定から始めて、徐々に複雑さを加えていきます
2. **段階的にテストする**: 挙動を確認するために、一度に 1 つのモジュールを有効にします
3. **テンプレートを使用する**: 提供されたテンプレートをベースに設定します
4. **設定を検証する**: すべての値が有効な範囲と形式であることを確認します
5. **ログを監視する**: 設定の警告やエラーがないかログを確認します
6. **設定をバックアップする**: 動作している設定のバックアップを保持します

---

## 設定例

### 基本戦闘設定
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

### 連合艦隊戦闘設定
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

### 自動モード設定
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
