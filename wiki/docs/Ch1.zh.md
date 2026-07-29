## 前置作業 (Common)
_You need to do this no matter what_

* 在 `debug`（除錯）模式下運行 POI（Brave 也停止支援 Manifest V2，只能88 KC3 了）
  * ***如有需要，請使用工作管理員強制結束所有 POI 相關程序。***   
    為確保 POI 成功啟動，此 `debug` 模式必須是 POI 啟動的*第一個*程序。若已打開其他 POI 視窗，請先全部關閉後，再以啟用 `remote-debugging` 的方式重新啟動。
  * 範例：`poi --remote-debugging-port=9222 --remote-allow-origins=*`  
    （Windows 使用者：若不知道如何帶參數啟動 POI，請參考 [這篇文章](https://stackoverflow.com/a/56457835)）  
    （目前必須加上 `--remote-allow-origins=*` 參數(2023/05/04) [參考來源](https://github.com/XVs32/kcauto_custom/issues/19)）
  * 如何確認 `debug` 模式已成功開啟？
    * :heavy_check_mark: 連線至 `127.0.0.1:9222`，應有下圖所示的空白畫面：  
![Screenshot from 2023-05-04 22-34-30](https://user-images.githubusercontent.com/16824564/236221380-f2b52443-b2f7-4510-899f-c8582f431d12.png)  
    * :x: 若看到以下畫面，請關閉所有 POI 程序並重新嘗試：  
![Screenshot from 2023-05-04 22-28-56](https://user-images.githubusercontent.com/16824564/236221730-c5445cc8-b270-4cb9-b7d2-0ed4f892be56.png)  

* 安裝 `poi-plugin-noro6-exporter` 及 `poi-plugin-forwarder` 擴充外掛

<img width="474" height="707" alt="image" src="https://github.com/user-attachments/assets/570ebbfa-ca5f-4082-a340-ebee58ccd6c2" />

* **Linux (Ubuntu) 使用者須知**：  
  Ubuntu 的 Wayland 顯示協定對 kcauto 相容性不佳（對很多其他軟體也是，LOL）。  
  建議將 Ubuntu 切換回傳統的 X-windows 介面。  
  ![image](https://github.com/user-attachments/assets/696ed225-09da-4254-9a1c-956c4c1f87f9)  

---

## 啟動說明 (Start Up)
請從 **初學者 (Beginner)**、**玩家 (Gamer)** 或 **開發者 (Developer)** 中選擇一種模式：

### 初學者 (Beginner)  
*功能受限，但安裝與後續設定流程最簡單。*

* Windows
    * 連點兩下執行 `kcauto_cui.exe` 
* Linux
    * 執行 `./kcauto_cui`

以上！

### 玩家 (Gamer)  
*需要搭配制空權模擬器 (Noro6) 設置，但可使用完整功能。*

* Windows
    * 建議在 PowerShell 中執行 `.\kcauto_cui.exe` 以獲得最佳使用體驗
    * 或執行 `.\kcauto_custom.exe --cfg <你的設定檔名稱>` 來指定自訂設定檔  
      （注意：此處無需輸入副檔名 `.json`）
* Linux
    * 執行 `./kcauto_cui`
    * 或執行 `./kcauto.bin --cfg <你的設定檔名稱>` 來指定自訂設定檔  
      （注意：此處無需輸入副檔名 `.json`）

### 專家 (Expert)
*從設定檔直接調整各種細部設定。非新手向。*

請時刻保持備份的好習慣。  
如果你不知道自己在做什麼，回頭是岸。

詳細說明請參閱第 4 章。

### 開發人員 (Developer)
*獨立的 Python 環境，自由修改與修復 kcauto_custom。*

* 安裝 Python 3.11 與 pip
* 使用 `pip install pipenv` 安裝 `pipenv`
* 建立 `.venv` 虛擬環境，若忘記建立方式可參考 [快速參考指南](https://gist.github.com/ryumada/c22133988fd1c22a66e4ed1b23eca233)
* 使用 `source .venv/bin/activate` 啟用虛擬環境
* 安裝依賴套件：
  * ```pip install -r requirements.txt```
* 若發現缺少函式庫，請查看 `requirements.txt` 以獲取更詳細的說明

* Windows
    * 執行 `python .\kcauto\kcauto_cui.py`
    * 或執行 `python kcauto --cfg <你的設定檔名稱>` 來指定自訂設定檔  
      （注意：此處無需輸入副檔名 `.json`）
* Linux
    * 執行 `python3 ./kcauto/kcauto_cui.py`
    * 或執行 `python3 kcauto --cfg <你的設定檔名稱>` 來指定自訂設定檔  
      （注意：此處無需輸入副檔名 `.json`）
