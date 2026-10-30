_不勞，無獲_

---

## 概要 -- `Sortie mode: Auto` (自動出擊模式)
簡而言之，`Sortie mode: Auto` 能夠全自動完成定期出擊任務。

這功能帶來的是高度自動化體驗：

1. `kcauto-custom` 會為你挑選一個可執行的任務
2. 它會自動載入你在 `Noro6` 中設定的編制
3. 接著直接出擊至該任務所要求的地圖

![image](https://github.com/user-attachments/assets/3b141ad3-aae7-4c31-9949-f477bc9760a1)
　　　　***請先在 Noro6 中設定好你的戰鬥艦隊***

相對地，這部分的設定稍微複雜一些，你需要在 `Noro6` 和 `kcauto_custom` 中進行幾項設置：

1. 地圖與任務 ID：這份艦隊（編成）設定檔是為了哪張地圖準備的（例如：是給 1-5 用的？還是給季常任務 Bq4 的 6-3 用的？）
2. 艦娘與裝備：要使用哪些艦娘和裝備
3. 任務池：你想執行哪些任務

話不多說，我們開始吧~

---

## 依賴需求 (Dependence)

### Noro6
我們當然需要用到 Noro6 ，廢話？  

[Noro6](https://noro6.github.io/kc-web/#/aircalc) 是一款非常優秀的模擬器，用戶可以匯入自己的艦娘與裝備庫存來建立艦隊編成。  

稍後會再詳細介紹。

---

## 設定檔配置 (Config setup)
設定你的 `Noro6` 設定檔只需要三個步驟，模板檔案位於 `configs/noro6/noro6`：

1. 將你的艦娘與裝備資料匯出至 `Noro6`
2. 建立你的 `Noro6` 配置
3. 將 `Noro6` 配置匯入至 `kcauto_custom`

---

### 匯出資料 (Exporting)

首先，讓我們把艦娘和裝備資料匯出到 `Noro6`。  
這步驟其實滿簡單的：

開啟 `Noro6 Exporter` 外掛

<img width="474" height="172" alt="image" src="https://github.com/user-attachments/assets/94ae6c1b-b111-47c3-9e7a-7a2a691df1ba" />

點擊 [Export to Noro6]

* 再次提醒，這個外掛**不會**匯出到官方版的 Noro6，  
而是會匯出到 [XVs32's edition Noro6](https://xvs32.github.io/kc-web/#/)。  


<img width="339" height="117" alt="image" src="https://github.com/user-attachments/assets/3e465fc7-b8db-4f6b-ada5-6c3e19c7422a" />

![image](https://github.com/user-attachments/assets/ee4eff82-e3bf-448a-be37-1605dc388a6f)
***網頁會自動切換到 Noro6！***

現在點擊 Setting（設定），然後匯入位於 `configs/noro6/noro6_tutorial` 的教學檔案。  
![Screenshot from 2024-10-31 01-44-44](https://github.com/user-attachments/assets/48e0a662-bc35-46bf-b0cb-0b5a475dc0f1)  

<img width="496" height="157" alt="Screenshot_20260203_155850" src="https://github.com/user-attachments/assets/adf20a4a-8feb-4a0e-a7d7-73b14d40294a" />  

<img width="576" height="345" alt="image" src="https://github.com/user-attachments/assets/9aa14bdd-75fb-4a8f-a374-6d10cc030f47" />  

***以上！搞定！***

---

### 建立配置 (Setting up config)

下一步，我們要來編輯艦隊配置。  

讓我們打開 `B-1-1`。  
<img width="406" height="159" alt="image" src="https://github.com/user-attachments/assets/56b0adcc-406f-47bb-b1e8-704c60389a80" />

額……怎麼說？  
總之就是在這裡配好你的艦隊和裝備，然後記得存檔就對了。  
因為之後會有非常多配置要處理，`Noro6` 的剪貼簿 (clipboard) 功能絕對是你的救命稻草。

![image](https://github.com/user-attachments/assets/7093eb12-26ed-41e8-b9ac-070e0c479348)  
　　　　***在 Noro6 中設定艦隊***

![image](https://github.com/user-attachments/assets/21314488-3e17-4ae7-a813-929120b81180)  
　　　　***珍愛生命，善用剪貼簿功能***


---

### 匯入至 `kcauto_custom` (Import to kcauto_custom)

點擊 Setting => Create backup file => 覆蓋掉原先 `configs/noro6/noro6` 模板檔案就完成了。


![Screenshot from 2024-10-31 12-39-55](https://github.com/user-attachments/assets/863037fc-d8d4-4879-b00f-7129d117d936)

---

### `Sortie mode: Auto` 試運行

設定完 `B-1-1` 的配置後，  
你就可以直接在 `kcauto_cui` 中開啟自動艦隊功能了。

<img width="543" height="351" alt="image" src="https://github.com/user-attachments/assets/0b1b5822-1ab8-46ee-95b6-3f829aaab646" />

　　　　***沒錯，就是這麼簡單***

---

### 動手搭配你自己的出擊 Noro6 配置

成功設定 `B-1-1` 是很大進展，但單個配置意義不大。  
現在你需要建立更多的 `Noro6` 配置，  
以下是需要注意的事項：

1. 每個艦隊設定檔的檔名格式必須為 `B<quest_id>-<world>-<stage>-<target_node>`。  
例如：`B-1-1` 是專為 `1-1` 製作的配置；  
`By6-1-2` 是專為任務 `By6` 在 `1-2` 海域出擊時製作的配置；  
`B-7-2-G` 則是專為 `7-2-G` 點製作的配置。
2. 你可以在配置中同時指定艦娘和裝備。
3. 基地航空隊 (LBAS) 的分配功能目前很遺憾**尚未**支援。
4. 如果找不到某個任務的專屬配置（例如 `By6-1-2`），`kcauto_custom` 會自動轉向使用一般配置（例如 `B-1-2`）。
5. 歡迎自由新增你自己的配置（我肯定漏掉了不少跟任務相關的配置）。
6. **如果你太懶不想把所有配置一次搞定，請把那些你沒設定好的檔案給刪掉，否則 `kcauto_custom` 會被干擾。**

---

**在 `configs/noro6/noro6_template` 底下提供了有命名的模板，如果你想一口氣把設定搞定，可以用它來省下命名檔名的時間。  
如果你決定要從這個模板開始，請務必把沒用到的配置檔案刪掉。**

---

<img width="1014" height="891" alt="image" src="https://github.com/user-attachments/assets/43ad5ea6-eba0-40fa-b7c4-80c757413b9f" />  

　　　　***設定檔配置範例***

---

## 在 `kcauto_cui` 中使用 `Sortie mode: Auto`

完成所有需要的配置後，  
你就可以在 `kcauto_cui` 中享用全自動模式啦！

![image](https://user-images.githubusercontent.com/16824564/236405886-2115dcdd-35b7-4d0c-8e09-71c09bc51595.png)

---
