_型があっての型破り。_

---

## 工場レシピプリセット (`Factory recipe preset`)

レシピを変更するたびに wiki を確認する手間を省くため、  
`kcauto_custom` は JSON 形式のレシピプリセットを読み込むことができます。

対象ファイルは `data/factory/construct_recipe_preset.json` と `data/factory/develop_recipe_preset.json` です。フォーマットは以下の通りです：

```json
    <プリセット名>: {
        "factory.build_recipe": [
            <燃料>,
            <弾薬>,
            <鋼材>,
            <ボーキサイト>
        ],
        "factory.build_secretary": <艦娘ID>
    }
```

```json
    <プリセット名>: {
        "factory.develop_recipe": [
            <燃料>,
            <弾薬>,
            <鋼材>,
            <ボーキサイト>
        ],
        "factory.develop_secretary": <艦娘ID>
    }
```

***建造・開発レシピプリセットのフォーマット***

---

```json
{
    "Daily": {
        "factory.build_recipe": [
            30,
            30,
            30,
            30
        ],
        "factory.build_secretary": 0
    },
    "まるゆ": {
        "factory.build_recipe": [
            1500,
            1500,
            2000,
            1000
        ],
        "factory.build_secretary": 0
    }
}
```

```json
{
    "radar": {
        "factory.develop_recipe": [
            10,
            10,
            250,
            250
        ],
        "factory.develop_secretary": 456
    },
    "91-AP": {
        "factory.develop_recipe": [
            10,
            30,
            90,
            10
        ],
        "factory.develop_secretary": 123
    }
}

```

***建造・開発レシピプリセットの例***

---

上記のファイルを配置すると、工場パネルの左側にプリセットが表示されます。選択するだけで対応するレシピが適用されます。

<img width="359" height="145" alt="image" src="https://github.com/user-attachments/assets/99faad4d-c784-4d91-b96d-b6b53926da19" />
<img width="360" height="149" alt="image" src="https://github.com/user-attachments/assets/8a6152f6-72fe-49cf-a123-2b68145a7d63" />

***レシピプリセットの適用例***
