
_千里の行も一歩から。_

---

![Panel](https://github.com/XVs32/kcauto_custom/assets/16824564/0d582a36-60fb-4e18-b660-4b4c84a5cb18)

* 移動
    * 矢印キー
* 決定 / 選択
    * Enter キー
* 終了
    * Esc キー
* 一時停止
    * スペースキー

---
### 遠征 (Expedition)

![image](https://github.com/XVs32/kcauto_custom/assets/16824564/2846046b-4800-4e67-8a3b-eb8bea06a706)

遠征のプリセットは `.\data\expedition\expedition_preset.json` に配置されています。  
必要に応じて遠征 ID を変更できます。

```
{
               #2(長距離練習航海)        #3(警備任務)     #6(防空射撃演習)
  "active":         [[2],                 [3],              [6]],
  "passive":      [[5],[21],[38]],
  "overnight":    [[11],[24],[38]],
  "user":  [[],[],[21]]
}
```

初心者ガイドでは自動編成機能は利用できません。ここでは `disable` を選択してください。  
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/d2e35af7-314a-4226-9a1b-ede83bd1926f)

---
### 出撃 (Combat)

![image](https://user-images.githubusercontent.com/16824564/236396966-32b58de4-0aaa-481e-a2fc-f31213592a8d.png)

#### 手動出撃モード (Manual sortie mode)
まず、矢印キーで海域マップを選択します。  
![image](https://user-images.githubusercontent.com/16824564/236397921-9c79af0b-1edb-44b3-a0ee-8609d54b790a.png)  
次に、艦これゲーム内の編成記録を選択します  
（現在の艦隊をそのまま使用する場合は `disable` を選択）。  
![image](https://user-images.githubusercontent.com/16824564/236398074-ffff1651-e646-4331-979f-ca4c4d9873bf.png)  

#### 明石修理 (Akashi repair)
出撃メニューで `disable(akashi mode)` を選択した後、  
明石修理を有効化できます。  
（これを使用するには 明石改 が必要です）  
![image](https://user-images.githubusercontent.com/16824564/236397397-689805f8-bfb5-4034-b5b1-14f11d9ce40c.png)

---

### 演習 (PVP)
演習モジュールを無効化するか、演習用の艦これゲーム内編成記録を選択します。  
![image](https://user-images.githubusercontent.com/16824564/236402275-ee8a1fc6-812c-4208-bbfa-f0f6629a035b.png)

---

### スケジューラー (Scheduler)

![image](https://user-images.githubusercontent.com/16824564/236401065-96636c78-fcc9-476f-89bb-690e27a17657.png)

#### 終了時間 (End time)
`kcauto_custom` を終了する時間（矢印キーで時間を選択）。  
（`kcauto_custom` を 7/24 動かし続けるのはやめましょう）

![image](https://user-images.githubusercontent.com/16824564/236399553-8897a4ec-7d5c-4977-a039-752925a18fe7.png)

#### 出撃回数 (Sortie count)
指定した出撃回数に達すると、`kcauto_custom` は出撃を停止します。  
（矢印キーで出撃回数を選択）  
![image](https://user-images.githubusercontent.com/16824564/236400038-03892b63-9cc9-4442-a490-2ce8ca0396c1.png)

---

### 任務パネル (Quest panel)

<img width="445" height="340" alt="image" src="https://github.com/user-attachments/assets/2fe76be4-ce87-40e1-a4a5-612383a8a72b" />

ホームパネルで `?` キー（`Shift` + `/`）を押すと、  
`kcauto_custom` に実行させる任務を選択できます。  
もう一度 `?` を押すと任務パネルを閉じます。

---

### kcauto_custom の起動 (Start kcauto_custom)

#### 初回起動時は、スプラッシュ画面から kcauto を起動する必要があります

![???](assets/569605507.png)

ログパネルを選択し、設定ファイルを読み込みます。  
![image](https://user-images.githubusercontent.com/16824564/236402505-1eade161-ca58-4ab4-80da-7f9d7ff4bbc1.png)  
![image](https://user-images.githubusercontent.com/16824564/236402785-c0cd0858-cbad-41be-8c83-500a2e99003c.png)  

初回起動時には、このようなエラーが発生する場合があります：
```java
[SUCCESS][2026-02-23 17:35:36] Initializing kcauto.
[DEBUG][2026-02-23 17:35:36] Loading data from 'configs/config_cui.json'.
[DEBUG][2026-02-23 17:35:36] Loading data from 'data/config/config_cui_template.json'.
[DEBUG][2026-02-23 17:35:36] Combat config init called
[DEBUG][2026-02-23 17:35:36] SET _sortie_map_read_only: {MapEnum(value)}
[DEBUG][2026-02-23 17:35:36] _repair_bucket_threshold set 500
[SUCCESS][2026-02-23 17:35:36] Config successfully loaded.
[DEBUG][2026-02-23 17:35:36] Loading data from 'data/temp/reinforce_general_category.json'.
[ERROR][2026-02-23 17:35:36] Reinforce equipment data not found, please start kcauto from splash screen
[ERROR][2026-02-23 17:35:36] [Errno 2] No such file or directory: 'data/temp/reinforce_general_category.json'
[DEBUG][2026-02-23 17:35:36] Loading data from 'data/temp/equipment_list.json'.
[ERROR][2026-02-23 17:35:36] Equipment data not found, please start kcauto from splash screen
[ERROR][2026-02-23 17:35:36] [Errno 2] No such file or directory: 'data/temp/equipment_list.json'
```

これは `kcauto_custom` が艦これから必要なデータをまだ取得していないためです。  
初回起動後に `data/temp` フォルダに以下のファイルが生成されていれば、  
そのまま `kcauto_custom` を再起動してください。

<img width="870" height="256" alt="image" src="https://github.com/user-attachments/assets/0be41038-5a54-4f44-a7e8-60657589a91c" />

*`kcauto_custom` が艦これから取得したすべてのキャッシュファイル*

~~***Windows ゲーマーへ：***~~  
~~Windows 環境において `kcauto_custom` が `chrome_driver` モードで正常に動作しないとの報告があります。~~  
~~マウス操作に問題が発生する場合は、~~  
~~`direct_control` モードへの切り替えを推奨します。~~  

~~**手順：**~~  
~~1. `kcauto_custom` を 1回実行~~  
~~2. `kcauto_custom` を終了~~  
~~3. `configs/config_cui.json` を開く~~  
~~4. `"general.interaction_mode": "chrome_driver",` => `"general.interaction_mode": "direct_control",` に編集~~  
~~5. 保存して閉じる~~  

Windows のマウス問題は最新バージョンで修正済みです (2026/07/28)。  

