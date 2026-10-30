_Standardization, not perfection, is the key to scale._

---

## `Factory recipe preset`

To avoid wiki-ing every time when changing recipe.  
kcauto_custom is capable to read recipe preset in JSON format.  

The files are `data/factory/construct_recipe_preset.json` and `data/factory/develop_recipe_preset.json`.  
The format is:
```json
    <preset name>: {
        "factory.build_recipe": [
            <fuel>,
            <ammo>,
            <steel>,
            <bauxite>
        ],
        "factory.build_secretary": <ship id>
    }
```

```json
    <preset name>: {
        "factory.develop_recipe": [
            <fuel>,
            <ammo>,
            <steel>,
            <bauxite>
        ],
        "factory.develop_secretary": <ship id>
    }
```

***Format of construct and develop recipe preset***

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

***Example of construct and develop recipe preset***

---

The preset will appear on the left of factory panel after you setup the above files.  
Simply selecting it will apply the corresponding recipe. 

<img width="359" height="145" alt="image" src="https://github.com/user-attachments/assets/99faad4d-c784-4d91-b96d-b6b53926da19" />
<img width="360" height="149" alt="image" src="https://github.com/user-attachments/assets/8a6152f6-72fe-49cf-a123-2b68145a7d63" />

***Example of applying recipe preset***
