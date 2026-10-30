_蒔かぬ種は生えぬ_

---

## 概要 -- `Sortie mode: Auto`
要するに、`Sortie mode: Auto` を使えば、デイリー任務、ウィークリー任務、マンスリー任務を完全に自動化できます。

高度な自動化体験になります：

1. `kcauto-custom` が利用可能な任務を自動的に選択します
2. Noro6 で定義したプリセットを読み込みます
3. 任務で要求された海域へ出撃します

![image](https://github.com/user-attachments/assets/3b141ad3-aae7-4c31-9949-f477bc9760a1)
　　　　***Noro6 で艦隊を設定します***

反面、設定は少々複雑。Noro6 と `kcauto_custom` でいくつか準備が必要になります：

1. 海域と任務 ID：この艦隊（編成）ファイルは何のための設定か？（例：1-5 用か？それとも Bq4 の 6-3 用か？）
2. 艦娘と装備：どの艦娘と装備を使用するか
3. 任務プール：どの任務を遂行したいか

それでは、始めましょう〜

---

## 依存関係 (Dependence)

### Noro6
言うまでもありませんが、これが必要です。  

[Noro6](https://noro6.github.io/kc-web/#/aircalc) は素晴らしいシミュレーターで、艦娘や装備のプールをインポートして艦隊を構築できます。  

詳細は後ほど。

---

## 設定ファイル (Config setup)
Noro6 の設定ファイルを準備するには 3 つのステップがあります。テンプレートは `configs/noro6/noro6` にあります：

1. 艦娘と装備を poi からエクスポートする
2. Noro6 で設定ファイルを作成する
3. 作成した Noro6 設定ファイルを `kcauto_custom` にインポートする

---

### エクスポート (Exporting)

まずは、艦娘と装備を Noro6 にインポートしましょう。  
簡単です。

`Noro6 Exporter` を開きます。

<img width="474" height="172" alt="image" src="https://github.com/user-attachments/assets/94ae6c1b-b111-47c3-9e7a-7a2a691df1ba" />

[Export to Noro6] をクリックします。

<img width="339" height="117" alt="image" src="https://github.com/user-attachments/assets/3e465fc7-b8db-4f6b-ada5-6c3e19c7422a" />

![image](https://github.com/user-attachments/assets/ee4eff82-e3bf-448a-be37-1605dc388a6f)
***自動的に Noro6 へ切り替わります！***

次に [Setting] をクリックし、`configs/noro6/noro6_template` にあるチュートリアルをインポートします。  
![Screenshot from 2024-10-31 01-44-44](https://github.com/user-attachments/assets/48e0a662-bc35-46bf-b0cb-0b5a475dc0f1)  


<img width="496" height="157" alt="Screenshot_20260203_155850" src="https://github.com/user-attachments/assets/adf20a4a-8feb-4a0e-a7d7-73b14d40294a" />  


<img width="576" height="345" alt="image" src="https://github.com/user-attachments/assets/9aa14bdd-75fb-4a8f-a374-6d10cc030f47" />  

***以上で完了です！***

---

### 設定ファイルの構築 (Setting up config)

次は、艦隊設定を編集します。

`B-1-1` を開きましょう。  
<img width="406" height="159" alt="image" src="https://github.com/user-attachments/assets/56b0adcc-406f-47bb-b1e8-704c60389a80" />

えーっと…なんて言えばいいかな？  
ここで艦隊と装備を設定して、保存を忘れないでください。  
設定ファイルの数が多くなるので、Noro6 のクリップボード機能は命綱になります。

![image](https://github.com/user-attachments/assets/7093eb12-26ed-41e8-b9ac-070e0c479348)  
　　　　***Noro6 で艦隊を設定***

![image](https://github.com/user-attachments/assets/21314488-3e17-4ae7-a813-929120b81180)  
　　　　***クリップボード機能で作業を効率化しましょう***


---

### `kcauto_custom` へのインポート (Import to kcauto_custom)

[Setting] => [作成] をクリックし、`configs/noro6/noro6` テンプレートに上書き保存すれば完了です。


![Screenshot from 2024-10-31 12-39-55](https://github.com/user-attachments/assets/863037fc-d8d4-4879-b00f-7129d117d936)

---

### `Sortie mode: Auto` のテスト実行

`B-1-1` の設定が完了したら、`kcauto_cui` から自動艦隊機能を使用できます。

<img width="543" height="351" alt="image" src="https://github.com/user-attachments/assets/0b1b5822-1ab8-46ee-95b6-3f829aaab646" />

　　　　***それでは、試してみましょう！***

---

### 自分専用の出撃 Noro6 設定を作成する

`B-1-1` は大きな第一歩ですが、それだけでは十分ではありません。  
これからは必要に応じて Noro6 設定を作成しましょう。  
以下の点に注意してください：

1. すべての艦隊設定のファイル名は `B<任務ID>-<海域>-<ステージ>-<対象ノード>` である必要があります。  
例：`B-1-1` は `1-1` 用のコンフィグ、  
`By6-1-2` は任務 `By6` の `1-2` 用に特別に作られたコンフィグ、  
`B-7-2-G` は `7-2-G` 用のコンフィグです。
2. 艦娘と装備の両方を指定できます。
3. 基地航空隊 (LBAS) の設定は、残念ながら **まだサポートされていません**。
4. 特定の任務用の設定（例：`By6-1-2`）が見つからない場合、`kcauto_custom` は通常の設定（例：`B-1-2`）にフォールバックします。
5. 独自のコンフィグを自由に追加してください。
6. **設定していないものは削除してください。そうしないと `kcauto_custom` が混乱します。**

---

**`configs/noro6/noro6_template` にテンプレートがあります。一気に設定を終わらせたい場合にファイル名の命名の手間を省けます。  
このテンプレートから始める場合は、使わないコンフィグを必ず削除してください。**

---

<img width="1014" height="891" alt="image" src="https://github.com/user-attachments/assets/43ad5ea6-eba0-40fa-b7c4-80c757413b9f" />  

　　　　***設定ファイルの例***

---

## `kcauto_cui` で `Sortie mode: Auto` を使用する

必要なすべての設定が完了したら、`kcauto_cui` で自動モードを使用できます。

![image](https://user-images.githubusercontent.com/16824564/236405886-2115dcdd-35b7-4d0c-8e09-71c09bc51595.png)

---
