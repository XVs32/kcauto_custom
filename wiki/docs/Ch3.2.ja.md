_人類は、あらゆる間違った理由のために、あらゆる正しい技術を獲得している。_

---

## 概要 -- `Expedition mode: Auto`

`Expedition mode: Auto` は完全に自動化された遠征モードで、以下の機能を備えています：

1. 特定の遠征に対して有効な艦隊を編成し、艦娘を編成します
2. 最も効率的な遠征を選択し、プレイヤーのリソースバランスを調整します
3. 大発動艇やドラム缶の必要数を自動で処理します
4. Noro6 の設定ファイルが提供されている場合は、その艦隊構成を読み込む（[Noro6 のセクション](#noro6)を参照）

<img width="889" height="928" alt="image" src="https://github.com/user-attachments/assets/f46ca530-b1ab-4861-9ee4-680fb6a99070" />

***`Expedition mode: Auto` の簡易概要***

---

## 艦娘プール (Ship pool)

遠征で使用する艦娘プールは自動的に組み立てられます。以下のすべてに該当する艦娘が自動的に遠征艦娘プールに割り当てられます：

1. Noro6 のどのコンフィグにも使用されていない
2. ロックされている
![image](https://github.com/user-attachments/assets/5198fb72-ab68-4c9d-a692-f6c252069d18)

<img width="817" height="436" alt="image" src="https://github.com/user-attachments/assets/eb899526-2a3a-47ce-9848-66ddfcaf08c0" />

***遠征用艦娘プールの構成***

---

## Noro6

戦闘遠征（例：`A5`、`A6`）や、すでに Noro6 で使用されている艦娘を必要とする遠征の場合、遠征用の Noro6 コンフィグを定義することで、`kcauto` でそれらの遠征を実行できます。

### 注意：これは「出撃」と「演習」の両方が無効化されている時のみ機能します。  
すべての Noro6 コンフィグは同じ艦娘および装備プールを共有しているためです。

<img width="922" height="557" alt="image" src="https://github.com/user-attachments/assets/9f85be79-2b73-4f3a-8847-768dffa8797a" />

***遠征用 Noro6 コンフィグの例***

### コンフィグの設定

<img width="110" height="204" alt="image" src="https://github.com/user-attachments/assets/637e2009-a219-426f-bab0-587fce4b71b8" />

***遠征用コンフィグのファイル名の例***

注意点：

1. すべての遠征コンフィグのファイル名は `D-<遠征ID>` である必要があります。  
例：`D-A3` は `A3` 用のコンフィグ。
2. コンフィグ内で艦娘と装備の両方を指定できます。
3. Noro6 コンフィグは、`kcauto_custom` が自動割り当てする艦隊よりも優先されます。
4. **繰り返しますが、Noro6 を参照する遠征は、「出撃」と「演習」の両方が無効化されている時のみ機能します。**
5. 独自のコンフィグを自由に追加してください。

基本ルールは、[第 3.1 章](../Ch3.1#put-together-your-own-sortie-noro6-config)の「出撃用 Noro6 コンフィグ」と同じです。

---

## 艦娘の割り当て (Ship assign)

`auto` を選択することで、艦娘の割り当てを有効にできます。

![螢幕擷取畫面 2023-07-18 194649](https://github.com/XVs32/kcauto_custom/assets/16824564/bd1a9f45-191d-41b4-9b4e-819417b3534e)

`expedition mode: auto` は、もはや初期バージョンではありません。現在は以下の機能に対応しています：

1. 遠征レベル制限への対応
2. ドラム缶および大発動艇のボーナス条件への対応
3. A1、B6 などの遠征への対応（Noro6 の補助により）
4. 起動時だけでなく、実行中に遠征セットを動的に選択可能
5. 全艦隊の帰投を待つ必要はなく、空いている艦隊から順次切り替え可能
