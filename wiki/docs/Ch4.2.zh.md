_規模化的關鍵在於『標準化』，而非『追求完美』。_

---

## 工廠配方速查 (Factory recipe preset)

為避免每次更換配方時都要去翻閱 Wiki 查詢，  
`kcauto_custom` 支援讀取 JSON 格式的配方。  

這些檔案分別是 `data/factory/construct_recipe_preset.json` 與 `data/factory/develop_recipe_preset.json`。  
格式如下：

```json
    <配方名稱>: {
        "factory.build_recipe": [
            <燃料>,
            <彈藥>,
            <鋼材>,
            <鋁土>
        ],
        "factory.build_secretary": <艦娘 ID>
    }
```

```json
    <配方名稱>: {
        "factory.develop_recipe": [
            <燃料>,
            <彈藥>,
            <鋼材>,
            <鋁土>
        ],
        "factory.develop_secretary": <艦娘 ID>
    }
```

***建造與開發配方格式***

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

***建造與開發配方預設範例***

---

當你設定好上述檔案後，預設選項就會出現在工廠控制面板的左側。  
只需直接點選即可自動套用對應的配方。 

<img width="359" height="145" alt="image" src="https://github.com/user-attachments/assets/99faad4d-c784-4d91-b96d-b6b53926da19" />
<img width="360" height="149" alt="image" src="https://github.com/user-attachments/assets/8a6152f6-72fe-49cf-a123-2b68145a7d63" />

***套用配方預設之範例***
