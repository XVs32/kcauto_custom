_自動化は素晴らしいものだ。どこに機械を導入すべきかを正確に把握している限りは。_

---

## 概要 -- `Factory module`

**工廠モジュールは、デイリーの建造と開発を自動的に処理します。単純です。**

`Factory module` を有効にする前に設定が必要であることをユーザーに認識してもらうため、工廠モジュールは **デフォルトで無効** になっています。

設定ファイル（CUI ユーザーの場合は `configs/config_cui.json`）を編集し、`factory.enabled` を `true` に変更することで有効にできます。  
**これを行う前に CUI パネルを閉じてください。そうしないと CUI が更新を認識できない場合があります。**

```json
    "factory.enabled": true,
```

***Factory module を有効にする***

---

## 工場パネル

工場パネルは、ホーム画面で `"` キー（`Shift` + `'`）を押すと開きます。  
ここでは、建造と開発のレシピ、および秘書艦を設定できます。  
もう一度 `"` キーを押すと閉じます。

<img width="360" height="146" alt="image" src="https://github.com/user-attachments/assets/f0ebc274-7523-4655-97f3-a501cec4b9f5" />

***リソースの投入量を決定する***

---

## ID による秘書艦の選択

秘書艦の ID は [plugin-ship-info](https://github.com/poooi/plugin-ship-info) で確認できます。  
これはその艦娘の製造番号です。

<img width="398" height="174" alt="image" src="https://github.com/user-attachments/assets/6f8a1e75-54ae-4996-a68a-bb81d2525322" />
 
<img width="206" height="62" alt="image" src="https://github.com/user-attachments/assets/acb251f4-e88e-4171-b1c3-bf0e2401b08f" />

*艦娘の情報に表示される製造番号*

この例では、五月雨の製造番号は ```1``` です。これで秘書艦を設定できます。

<img width="439" height="134" alt="image" src="https://github.com/user-attachments/assets/b4ea5779-c20b-4b91-85c4-5610778244e7" />
<img width="439" height="134" alt="image" src="https://github.com/user-attachments/assets/ee91682a-4ed0-49a9-9a07-5f63c5ecabc5" />

***秘書艦を指定する***

---

## 艦種による秘書艦の選択

ID を使用する以外に、艦種で秘書艦を割り当てることもできます。

<img width="440" height="120" alt="image" src="https://github.com/user-attachments/assets/1e90613a-b7be-4f6b-89ff-0b54e917e854" />

---

## 秘書艦の指定を無効化する

秘書艦 ID を `0` に設定すると、`kcauto_custom` は建造や開発を実行する前に秘書艦を切り替えません。

<img width="358" height="146" alt="image" src="https://github.com/user-attachments/assets/49628fd4-e7d7-45d2-9d83-abfaaad1a7fc" />

***特定の秘書艦への切り替えを行わない***

もう一度 `"` キーを押すと閉じます。
