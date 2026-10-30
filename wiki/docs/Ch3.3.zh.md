_得魚忘筌，得意忘象。_

---

## 概要 -- `PvP mode: Auto` (自動演習模式)

`PvP mode: Auto` 的運作原理與 `sortie mode: Auto` 及 `expedition mode: Auto` 相同，  
它能夠自動幫你完成演習相關任務：

1. 玩家可在 `Noro6` 中設定好各個艦隊的預設
2. `kcauto_custom` 會自動挑選適合的演習任務
3. `kcauto_custom` 載入對應的艦隊並嘗試完成任務

---

## 演習任務承接機制 (PvP quest handling)

為了避免 `kcauto_custom` 無腦選取所有看得到的演習任務，  
我們加入了判斷當前艦隊是否符合任務需求的能力。

舉例來說，如果你的艦隊配置中沒有包含 1CL + 3DD 或 4DD，  
`kcauto_custom` 就不會主動去選取任務 [`Cq4 (小艦艇群演習強化任務)`](https://wikiwiki.jp/kancolle/%E4%BB%BB%E5%8B%99#id-Cq)。  
若 `kcauto_custom` 被強迫一定要嘗試完成該任務，系統便會發送警告。

<img width="855" height="58" alt="image" src="https://github.com/user-attachments/assets/8beffcae-c763-4223-83c4-8b0b63c39930" />  

***艦隊編制不合要求的警告訊息***

---

## Noro6

注意事項：

1. 每個演習配置的檔案名稱必須為 `C<quest id>-pvp`。  
例如：`Cm2-pvp` 是專為任務 `Cm2` 製作的配置。
2. 你可以在配置中同時指定艦娘與裝備。
3. 歡迎隨意加入你自己的配置。

<img width="138" height="255" alt="image" src="https://github.com/user-attachments/assets/2b95b355-6787-49c9-b9a3-cc1c2fcb8347" />

***演習配置檔案名稱範例***

---

## 在 `kcauto_cui` 中使用 `PvP mode: Auto`

完成所有必要的配置後，  
你就可以在 `kcauto_cui` 中開啟自動演習模式了。

<img width="489" height="260" alt="image" src="https://github.com/user-attachments/assets/6cbe212a-8668-4578-b0a6-e5317e328a37" />
