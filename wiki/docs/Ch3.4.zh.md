_善用器者，先審其適。_

---

## 概要 -- `Factory module` (工廠模組)

**Factory module 自動幫你處理每日的開發與建造。樸實無華。**

為了確保提督在開啟它之前確實有做好相關設定，工廠模組**預設是關閉的**。

你可以藉由編輯設定檔（CUI 玩家為 `configs/config_cui.json`）來啟用它：  
將 `factory.enabled` 修改成 `true`。  
**請在編輯前先關閉 CUI 控制面板，否則 CUI 可能不會偵測到你做出的檔案修改。**

```json
    "factory.enabled": true,
```

***啟用工廠模組***

---

## 工廠控制面板

在主頁面按下 `"` 鍵（`shift` + `'`）可以開啟工廠面板。  
玩家能在此設定建造與開發所要使用的配方（Recipe）以及秘書艦。  
再次按下 `"` 鍵即可關閉離開。

<img width="360" height="146" alt="image" src="https://github.com/user-attachments/assets/f0ebc274-7523-4655-97f3-a501cec4b9f5" />

***決定要投入多少資源***

---

## 透過 ID 選擇秘書艦
秘書艦的 ID 可以透過 [plugin-ship-info](https://github.com/poooi/plugin-ship-info) 外掛查詢，  
該 ID 即為艦娘的生產 ID（Production id）。

<img width="398" height="174" alt="image" src="https://github.com/user-attachments/assets/6f8a1e75-54ae-4996-a68a-bb81d2525322" />
 
<img width="206" height="62" alt="image" src="https://github.com/user-attachments/assets/acb251f4-e88e-4171-b1c3-bf0e2401b08f" />

*艦娘資訊中顯示的生產 ID*

以這五月雨為例，她的 ID 是 ```1```。  
現在我們便可著手設定秘書艦。

<img width="439" height="134" alt="image" src="https://github.com/user-attachments/assets/b4ea5779-c20b-4b91-85c4-5610778244e7" />
<img width="439" height="134" alt="image" src="https://github.com/user-attachments/assets/ee91682a-4ed0-49a9-9a07-5f63c5ecabc5" />

***指定特定秘書艦***

---

## 依照艦種選擇秘書艦

除了直接指定 ID 以外，玩家也可以指定由哪一類「艦種」來擔任秘書艦

<img width="440" height="120" alt="image" src="https://github.com/user-attachments/assets/1e90613a-b7be-4f6b-89ff-0b54e917e854" />

---

## 停用秘書艦切換

若秘書艦 ID 設為 `0`，  
`kcauto_custom` 在執行建造或開發前就不會特別去切換秘書艦。

<img width="358" height="146" alt="image" src="https://github.com/user-attachments/assets/49628fd4-e7d7-45d2-9d83-abfaaad1a7fc" />

***不為特定任務切換秘書艦***

再次按下 `"` 鍵即可關閉離開。

---
