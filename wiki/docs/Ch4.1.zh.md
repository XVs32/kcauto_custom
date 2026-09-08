_We're all nerds, on one subject or another._

---

## Before you read
There is a User config wiki page in [Ch5 Configuration File](Ch5.md)  
You can find the explain for each option in user config  
Check that out if you find yourself surrounded by unknown terms

---

## Map specified Sortie setting (combat.override)

In most cases, kcauto_custom sortie with the same general logic.  

* Diamond for anti-air
* Line Abreast for anti-sub
* Vanguard instead of Line Ahead during event
* Get into night battle against boss for rank S result
* etc.

Though in some others maps, we do need to:

* Select node (ex. In 5-3, we select node K to node O) 
* Setup lbas (ex. In 6-4, 6-5, 7-4 etc.)
* Attempt using Nelson touch
* Attempt using smoke 
* etc.

Issue is those settings are not gonna work for other maps, and the map specified setting is here to help.

---

### What if I don't need this?
Set `combat.override` in your config to `true`.  
Your kcauto works the same as before.

---

There are 3 levels of Sortie settings:

1. User config(Your normal config, `configs/config_cui.json` if you're using CUI)
2. Default `data/config/combat/default.json` (Default sortie config for general map)
3. Map specified setting (ex.`data/config/combat/B-4-5.json`)(Sortie config made for specific map)

The priority here is `User config` < `Default` < `Map specified`  
And you can define `enabled`, `fleet_presets` and `sortie_map` from User config ***ONLY***(show as STATIC in the following pic).
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/0ee2f28f-7b6a-43cf-90bd-906f016da836)

Feel free to edit or add configs under `data/config/combat`.  
As long as `combat.override` in your own config is set to `false`, 
kcauto will read the corresponding setting automatically. 

---

## `Sortie mode: Auto` -- quest handling

***Before you read: Usually you don't need to set this up yourself if you are using the CUI.  
Do NOT edit the files here if you're not sure what you're doing***

Now we have told kcauto-custom what ship to use, but how do kcauto-custom pick a map and finish quests for me?

There are 3 files that would affect the behavior of quest & map picking (usually you don't have to edit them):

1. Your config file (`config/config_cui.json` for cui user)
2. ```data/quest/quest.json```
3. ```data/quest/quest_priority.json```

Let's take a look into the config file first:

```json
	"quest.enabled":	true,       #Enable the quest module
	"quest.quests":	["Bd1", "Bd2", "Bd3", "Bd4", "Bd5", "Bd6", "Bd7", "Bd8", "Bw1", "Bw2", "Bw3", "Bw4", "Bw5", "Bw7", "Bw8", "Bw9", "Bw10", "Bm2", "Bm3", "Bm4", "Bm5", "Bm6", "Bm8", "Bq1", "Bq3", "Bq4", "Bq8", "Bq9", "Bq10", "Bq11", "Bq12", "C2", "C3", "C4", "C8", "C16", "C29", "D2", "D3", "D4", "D9", "D11", "D22", "D24", "E3", "E4", "F5", "F6", "F7", "F8"]
	# The quests that kcauto-custom will attempt to finish
```

kcauto-custom will only handle the quests mentioned in `quest.quests`.  

Next one is ```data/quest/quest.json```, this file contains the details of a quest. Again, usually you wouldn't want to edit it.

```json

  "Bd1": {                         #The quest name
    "id": 201,                     #The quest ID
    "type": "daily",               #The quest type
    "intervals": [1, 0, 0],        #Intervals between kcauto-custom checking if the quest is finished, with the order as [sortie, pvp, expedition]
    "recommended_map": ["1-1"]     #The map which kcauto-custom will sortie to if no info could gather from KC3
  }

```

The last one is ```data/quests/sorite_quest_priority.json```, it defines what quest kcauto-costom will prioritizes when user is in `Sortie mode: Auto`
```json
{

  "time_limited": [
    "2412B5",
    "2509B5"
  ],
  "exact_ship_and_map": [
    "Bm1",
   ．．．
    "By15"
  ],
  "exact_ship_type_and_map": [
    "Bm3",
．．．
    "By11"
  ],
  "any_ship_with_exact_map": [
    "Bm8",
．．．
    "Bq10"
  ],
  "exact_area": [
    "Bw6",
    "Bw7"
  ],
  "exact_enemy_type": [
    "Bw2",
．．．
    "Bw3"
  ],
  "any_sortie": [
    "Bd1",
．．．
    "Bw1"
  ],
  "low_priority": [
    "Bd7"
  ]
}
```

The priority here is `daily` > `weekly` > `monthly` > `quarterly` > `yearly` > `low_priority`

---
