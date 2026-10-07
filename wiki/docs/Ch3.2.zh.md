_利器在手，心術不正。_

---

## 概要 -- `Expedition mode: Auto` (自動遠征模式)

`Expedition mode: Auto` 是全自動的遠征模式，它能夠：

1. 自動分配艦娘，組成符合特定遠征條件的有效艦隊
2. 挑選效率最高的遠征，平衡玩家的資源庫存
3. 自動處理大發動艇（大發）與運輸筒（桶）的數量需求
4. 如果有提供 `Noro6` 設定檔，則會自動載入其中的艦隊編制（詳見 [Noro6 段落](#noro6)）

<img width="889" height="928" alt="image" src="https://github.com/user-attachments/assets/f46ca530-b1ab-4861-9ee4-680fb6a99070" />

***`Expedition mode: Auto` 的概略運作流程圖***

---

## 艦娘候選池 (Ship pool)
~~與出擊模組相同，遠征用的艦娘池定義在 ```ship_pool.json``` 中。~~  
~~*你必須自己手動進行設定。*~~

沒，已經不需要手動設定船池了。  
任何符合以下**所有**條件的艦娘：

1. **沒有**在任何 `Noro6` 設定檔中被分配使用
2. 已鎖定（Locked）
![image](https://github.com/user-attachments/assets/5198fb72-ab68-4c9d-a692-f6c252069d18)

都會被自動分配到遠征（EXP）船池中。

<img width="817" height="436" alt="image" src="https://github.com/user-attachments/assets/eb899526-2a3a-47ce-9848-66ddfcaf08c0" />

***遠征船池的自動定義方式***

---

## Noro6
對於戰鬥遠征（例如：`A5`、`A6`）或需要用到已被 `Noro6` 佔用的艦娘的遠征，  
你可以為遠征定義專屬的 `Noro6` 配置，如此一來 `kcauto` 仍可順利執行這些遠征。

### 注意：這只有在出擊（Sortie）與演習（PvP）皆關閉的情況下才會生效。  
因為所有 `Noro6` 配置共享同一個艦娘與裝備池。

<img width="922" height="557" alt="image" src="https://github.com/user-attachments/assets/9f85be79-2b73-4f3a-8847-768dffa8797a" />

***遠征用 Noro6 配置設定範例***

### 設定配置 (Setting up config)

<img width="110" height="204" alt="image" src="https://github.com/user-attachments/assets/637e2009-a219-426f-bab0-587fce4b71b8" />

***遠征配置檔案名稱範例***

注意事項：

1. 每個遠征配置的檔案名稱必須為 `D-<Expedition ID>`。  
例如：`D-A3` 是專為遠征 `A3` 製作的配置。
2. 你可以在配置中同時指定艦娘和裝備。
3. `Noro6` 配置的優先權高於 `kcauto_custom` 的自動分配艦隊。
4. **再次強調，引用 Noro6 的遠征只有在出擊與演習皆關閉時才能順利運作，因為所有 Noro6 配置共用同一個艦娘和裝備庫存池。**
5. 歡迎自由加入你自己的配置。

整體設定概念與 [Ch3.1](../Ch3.1#動手搭配你自己的出擊-noro6-配置) 的出擊 `Noro6` 配置相同。

---

## 艦娘分配 (Ship assign)
你可以透過選擇 `auto` 來啟用自動艦娘分配。

![螢幕擷取畫面 2023-07-18 194649](https://github.com/XVs32/kcauto_custom/assets/16824564/bd1a9f45-191d-41b4-9b4e-819417b3534e)

這已經不再是早期版本的 `expedition mode: auto` 了。  
現在的 `expedition mode: auto` 能夠：

1. 自動處理等級（Level）限制需求
2. 自動處理大發動艇（大發）與運輸筒（桶）的額外資源加成需求
3. 支援像 A1、B6 這種較特別的遠征（須透過 Noro6 輔助）
4. 遠征組合會在運行中即時（On the fly）挑選，不再局限於只在啟動時決定
5. 只要有任何艦隊閒置就會進行切換，無需等待所有艦隊全部歸還
