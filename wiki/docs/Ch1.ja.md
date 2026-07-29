## 事前準備 (Common)
_You need to do this no matter what_

* `debug`（デバッグ）モードで POI を起動します（Brave も Manifest V2 のサポートを終了したため、KC3 とはお別れです QAQ）
  * ***必要に応じて、タスクマネージャーからすべての POI プロセスを終了してください。***   
    このデバッグ起動の POI は、POI の*最初の*インスタンスである必要があります。他に開いている POI ウィンドウがある場合は、すべて閉じてから `remote-debugging` を有効にして再起動してください。
  * 例：`poi --remote-debugging-port=9222 --remote-allow-origins=*`  
    （Windows ユーザーへ：オプション付きで POI を起動する方法がわからない場合は [こちら](https://stackoverflow.com/a/56457835) を参照）  
    （現時点では `--remote-allow-origins=*` の指定が必要です(2023/05/04) [参照](https://github.com/XVs32/kcauto_custom/issues/19)）
  * `debug` モードが有効になっているかどうかの確認方法：
    * :heavy_check_mark:`127.0.0.1:9222` にアクセスし、以下のような空白の画面が表示されれば成功です：  
![Screenshot from 2023-05-04 22-34-30](https://user-images.githubusercontent.com/16824564/236221380-f2b52443-b2f7-4510-899f-c8582f431d12.png)  
    * :x: 以下のような画面が表示された場合は、すべての POI プロセスを終了してやり直してください：  
![Screenshot from 2023-05-04 22-28-56](https://user-images.githubusercontent.com/16824564/236221730-c5445cc8-b270-4cb9-b7d2-0ed4f892be56.png)  

* プラグイン `poi-plugin-noro6-exporter` と `poi-plugin-forwarder` をインストールします

<img width="474" height="707" alt="image" src="https://github.com/user-attachments/assets/570ebbfa-ca5f-4082-a340-ebee58ccd6c2" />

* **Linux (Ubuntu) ユーザーへ**：  
  Ubuntu の Wayland は kcauto との相性がよくありません  
  X-windows 環境で Ubuntu を実行することをお勧めします。  
  ![image](https://github.com/user-attachments/assets/696ed225-09da-4254-9a1c-956c4c1f87f9)  

---

## 起動手順 (Start Up)
**初心者 (Beginner)**、**ゲーマー (Gamer)**、**開発者 (Developer)** のいずれかから選択してください。

### 初心者 (Beginner)  
*機能は制限されますが、最も簡単なインストールと設定方法です。*

* Windows
    * `kcauto_cui.exe` をダブルクリックします
* Linux
    * `./kcauto_cui` を実行します

以上です！

### ゲーマー (Gamer)  
*制空権シミュレータ (Noro6) の設定が必要ですが、すべての機能にアクセスできます。*

* Windows
    * Powershell で `.\kcauto_cui.exe` を実行することを推奨します
    * または、`.\kcauto_custom.exe --cfg <設定ファイル名>` を実行して自作の設定ファイルを指定します  
      （注：末尾の `.json` は入力不要です）
* Linux
    * `./kcauto_cui` を実行します
    * または、`./kcauto.bin --cfg <設定ファイル名>` を実行して自作の設定ファイルを指定します  
      （注：末尾の `.json` は入力不要です）

### エキスパート (Expert)
*設定ファイルからあらゆる設定を微調整することが可能です。上級者向けです。*

常にバックアップを保持してください。  
仕組みを理解していない場合は使用をお控えください。

詳細は第 4 章を参照してください。

### 開発者 (Developer)
*独自の Python 環境で、ツールの編集や修正を自由に行えます。*

* Python 3.11 と pip をインストールします
* `pip install pipenv` で `pipenv` をインストールします
* `.venv` を作成します（作成方法を忘れた場合は [こちら](https://gist.github.com/ryumada/c22133988fd1c22a66e4ed1b23eca233) を参照）
* `source .venv/bin/activate` で仮想環境を有効化します
* 依存関係をインストールします：
  * ```pip install -r requirements.txt```
* ライブラリが不足している場合は `requirements.txt` の詳細指示を確認してください

* Windows
    * `python .\kcauto\kcauto_cui.py` を実行します
    * または、`python kcauto --cfg <設定ファイル名>` を実行して自作の設定ファイルを指定します  
      （注：末尾の `.json` は入力不要です）
* Linux
    * `python3 ./kcauto/kcauto_cui.py` を実行します
    * または、`python3 kcauto --cfg <設定ファイル名>` を実行して自作の設定ファイルを指定します  
      （注：末尾の `.json` は入力不要です）
