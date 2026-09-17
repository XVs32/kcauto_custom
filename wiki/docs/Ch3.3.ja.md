_クリエイターが犯しうる最大の過ちは、テンプレート（型）をマンネリ化させてしまうことだ。_

---

## 概要 -- `PvP mode: Auto`

`PvP mode: Auto` は `sortie mode: Auto` や `expedition mode: Auto` と同様に、PvP 任務を自動的に完了します。

1. ユーザーは Noro6 で艦隊プリセットを設定可能
2. `kcauto_custom` が PvP 任務を選択
3. `kcauto_custom` が対応する艦隊を読み込み、任務の完了を試みる

---

## PvP 任務処理

`kcauto_custom` がすべての利用可能な PvP 任務を選択しないようにするため、`kcauto_custom` は現在の艦隊が任務の要件を満たしているかを判断する能力を備えています。

例えば、艦隊に 1CL+3DD や 4DD が含まれていない場合、`kcauto_custom` は任務 [`Cq4 (小艦艇群演習強化任務)`](https://wikiwiki.jp/kancolle/%E4%BB%BB%E5%8B%99#id-Cq) を選択しません。また、無理にその任務を遂行させようとすると警告が送信されます。

<img width="855" height="58" alt="image" src="https://github.com/user-attachments/assets/8beffcae-c763-4223-83c4-8b0b63c39930" />  

***任務対象外艦隊に対する警告メッセージ***

---

## Noro6

以下の点に注意してください：

1. PvP コンフィグのファイル名は `C<任務ID>-pvp` である必要があります。  
例：`Cm2-pvp` は任務 `Cm2` 用のコンフィグ。
2. コンフィグ内で艦娘と装備の両方を指定できます。
3. 独自のコンフィグを自由に追加してください。

<img width="138" height="255" alt="image" src="https://github.com/user-attachments/assets/2b95b355-6787-49c9-b9a3-cc1c2fcb8347" />

***PvP コンフィグのファイル名の例***

---

## `kcauto_cui` で `PvP mode: Auto` を使用する

必要な設定を完了したら、`kcauto_cui` で自動モードを使用できます。

<img width="489" height="260" alt="image" src="https://github.com/user-attachments/assets/6cbe212a-8668-4578-b0a6-e5317e328a37" />
