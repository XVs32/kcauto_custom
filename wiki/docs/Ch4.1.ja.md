_十人十色。_

---

## 読む前に (Before you read)
設定ファイルの各オプションの解説については、[第 5 章 設定ファイル](Ch5.ja.md) を参照してください。  

---

## 海域指定出撃設定 (`combat.override`)

ほとんどの場合は、`kcauto_custom` は同じロジックで出撃します。

* 対空時は輪形陣
* 対潜時は単横陣
* イベント中は単縦陣より警戒陣優先
* S 勝利のためにボス戦で夜戦に突入
* など

しかし、一部の海域では以下のような対応が必要です：

* ノードの選択（例：5-3 で K から O を選択）
* 基地航空隊の設定（例：6-4、6-5、7-4 など）
* ネルソンタッチの使用を試みる
* 煙幕の使用を試みる
* など

問題はこれらの設定が他の海域では機能しないことであり、そのための「海域指定設定」です。

---

### 不要な場合はどうすればよいですか？
設定ファイルの `combat.override` を `true` に設定してください。  

---

出撃設定には 3 つのレベルがあります：

1. ユーザー設定（通常のコンフィグ。CUI 使用時は `configs/config_cui.json`）
2. デフォルト `data/config/combat/default.json`（一般的な海域のデフォルト出撃設定）
3. 海域指定設定（例：`data/config/combat/B-4-5.json`）（特定の海域のために作成された出撃設定）

優先順位は `ユーザー設定` < `デフォルト` < `海域指定設定` です。  
また、`enabled`、`fleet_presets`、`sortie_map` はユーザー設定 ***のみ*** で定義可能です（以下の画像で STATIC と表示されている部分）。

![image](https://github.com/XVs32/kcauto_custom/assets/16824564/0ee2f28f-7b6a-43cf-90bd-906f016da836)

`data/config/combat` 下のコンフィグは自由に編集・追加してください。  
`combat.override` が `false` に設定されている限り、`kcauto` は自動的に対応する設定を読み込みます。

---

## `Sortie mode: Auto` -- 任務の処理

***読む前に：通常、CUI を使用している場合は自分で設定する必要はありません。  
仕組みを理解していない場合は、ここのファイルの編集はお控えください。***

任務とマップ選択の挙動に影響を与えるファイルが 3 つあります（通常は編集する必要はありません）：

1. 設定ファイル（CUI ユーザーは `config/config_cui.json`）
2. `data/quest/quest.json`
3. `data/quest/quest_priority.json`

まずは設定ファイルを見てみましょう：

```json
	"quest.enabled":	true,       # 任務モジュールを有効化
	"quest.quests":	["Bd1", "Bd2", "Bd3", "Bd4", "Bd5", "Bd6", "Bd7", "Bd8", "Bw1", "Bw2", "Bw3", "Bw4", "Bw5", "Bw7", "Bw8", "Bw9", "Bw10", "Bm2", "Bm3", "Bm4", "Bm5", "Bm6", "Bm8", "Bq1", "Bq3", "Bq4", "Bq8", "Bq9", "Bq10", "Bq11", "Bq12", "C2", "C3", "C4", "C8", "C16", "C29", "D2", "D3", "D4", "D9", "D11", "D22", "D24", "E3", "E4", "F5", "F6", "F7", "F8"]
	# kcauto-custom が処理を試みる任務
```

`kcauto-custom` は `quest.quests` で指定された任務のみを処理します。

次に `data/quest/quest.json` です。このファイルには任務の詳細が含まれています。  
これも通常は編集不要です。

```json

  "Bd1": {                         # 任務名
    "id": 201,                     # 任務 ID
    "type": "daily",               # 任務タイプ
    "intervals": [1, 0, 0],        # 任務が完了しているか kcauto-custom がチェックする間隔（順序：[出撃, 演習, 遠征]）
    "recommended_map": ["1-1"]     # KC3 から情報が集められない場合に kcauto-custom が出撃するマップ
  }

```

最後は `data/quests/sorite_quest_priority.json` です。ユーザーが `Sortie mode: Auto` を使用しているときに、`kcauto-custom` がどの任務を優先するかを定義します。

```json
{

  "time_limited": [
    "2412B5",
    "2509B5"
  ],
  "exact_ship_and_map": [
    "Bm1",
   ...
    "By15"
  ],
  "exact_ship_type_and_map": [
    "Bm3",
...
    "By11"
  ],
  "any_ship_with_exact_map": [
    "Bm8",
...
    "Bq10"
  ],
  "exact_area": [
    "Bw6",
    "Bw7"
  ],
  "exact_enemy_type": [
    "Bw2",
...
    "Bw3"
  ],
  "any_sortie": [
    "Bd1",
...
    "Bw1"
  ],
  "low_priority": [
    "Bd7"
  ]
}
```

優先順位は `デイリー` > `ウィークリー` > `マンスリー` > `クォータリー` > `イヤーリー` > `低優先度` です。
