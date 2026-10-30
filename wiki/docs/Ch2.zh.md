_千里之行，始於足下。_

---

![Panel](https://github.com/XVs32/kcauto_custom/assets/16824564/0d582a36-60fb-4e18-b660-4b4c84a5cb18)


* 移動選項
    * 方向鍵
* 確認 / 選擇
    * Enter 鍵
* 退出
    * Esc 鍵
* 暫停
    * 空白鍵 (Spacebar)

---
### 遠征 (Expedition)
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/2846046b-4800-4e67-8a3b-eb8bea06a706)

遠征組合位於 `.\data\expedition\expedition_preset.json`  
請根據需求自行修改遠征 ID。
```
{
               #2(長距離練習航海)        #3(警備任務)     #6(防空射撃演習)
  "active":         [[2],                 [3],              [6]],
  "passive":      [[5],[21],[38]],
  "overnight":    [[11],[24],[38]],
  "user":  [[],[],[21]]
}
```

初學者指南中不提供自動分配功能，請選擇 `disable`。  
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/d2e35af7-314a-4226-9a1b-ede83bd1926f)

---
### 出擊 (Combat)

![image](https://user-images.githubusercontent.com/16824564/236396966-32b58de4-0aaa-481e-a2fc-f31213592a8d.png)

#### 手動出擊模式 (Manual sortie mode)
首先，透過方向鍵選擇出擊地圖。  
![image](https://user-images.githubusercontent.com/16824564/236397921-9c79af0b-1edb-44b3-a0ee-8609d54b790a.png)  
選擇你在艦隊Collection 遊戲內的編成記錄（選擇 `disable` 則代表直接使用當前艦隊）。  
![image](https://user-images.githubusercontent.com/16824564/236398074-ffff1651-e646-4331-979f-ca4c4d9873bf.png)  

#### 明石維修 (Akashi repair)
在出擊選單中選擇 `disable(akashi mode)` 後，  
可以選擇開啟明石維修功能。  
（此功能需要明石改才能使用）  
![image](https://user-images.githubusercontent.com/16824564/236397397-689805f8-bfb5-4034-b5b1-14f11d9ce40c.png)

---

### 演習 (PVP)
關閉演習功能，或是選擇遊戲內用於演習的編成記錄  
![image](https://user-images.githubusercontent.com/16824564/236402275-ee8a1fc6-812c-4208-bbfa-f0f6629a035b.png)

---

### 排程器 (Scheduler)

![image](https://user-images.githubusercontent.com/16824564/236401065-96636c78-fcc9-476f-89bb-690e27a17657.png)

#### 結束時間 (End time)
關閉 kcauto_custom 的時間（用方向鍵選擇時間）  
（請絕對不要 24 小時全天候運作 bot，後果自負，LOL）

![image](https://user-images.githubusercontent.com/16824564/236399553-8897a4ec-7d5c-4977-a039-752925a18fe7.png)

#### 出擊次數 (Sortie count)
達到指定的出擊次數後，kcauto_custom 就會停止出擊。  
（用方向鍵選擇出擊次數）  
![image](https://user-images.githubusercontent.com/16824564/236400038-03892b63-9cc9-4442-a490-2ce8ca0396c1.png)

---

### 任務面板 (Quest panel)

<img width="445" height="340" alt="image" src="https://github.com/user-attachments/assets/2fe76be4-ce87-40e1-a4a5-612383a8a72b" />

在主頁面按下 `?` (shift + /) 鍵，  
可以選擇 kcauto_custom 要嘗試完成哪些任務，  
再次按下 `?` 即可離開任務面板。

---

### 啟動 kcauto_custom

#### 第一次執行時，請從啟動畫面開始運行 kcauto

![???](assets/569605507.png)

選擇 Log 面板，並重新載入你的設定檔。  
![image](https://user-images.githubusercontent.com/16824564/236402505-1eade161-ca58-4ab4-80da-7f9d7ff4bbc1.png)  
![image](https://user-images.githubusercontent.com/16824564/236402785-c0cd0858-cbad-41be-8c83-500a2e99003c.png)


你在首次運行時可能會撞到以下錯誤：
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

這是因為 kcauto_custom 還沒從艦隊Collection 那裡取得所需的資料。  
只要在第一次運行後，你的 `data/temp` 資料夾裡有生成以下檔案，  
就可以直接重啟 kcauto_custom。

<img width="870" height="256" alt="image" src="https://github.com/user-attachments/assets/0be41038-5a54-4f44-a7e8-60657589a91c" />

*kcauto_custom 從艦隊Collection 取得的所有暫存檔*

~~***Windows 使用者請注意：***~~  
~~有回報指出 kcauto_custom 在 Windows 上使用 `chrome_driver` 模式時運作得不太順暢。~~   
~~如果你遇到滑鼠控制方面的問題，~~  
~~建議切換至 `direct_control` 模式。~~  

~~**設定方法：**~~  
~~1. 運行 kcauto_custom 一次~~  
~~2. 關閉 kcauto_custom~~  
~~3. 開啟 `configs/config_cui.json`~~  
~~4. 修改 `"general.interaction_mode": "chrome_driver",` => `"general.interaction_mode": "direct_control",`~~  
~~5. 存檔並關閉~~  

Windows 的滑鼠問題應已在最新版本中修復 (2026/07/28)。
