# kcauto_custom

**kcauto_custom** is a linux command line Kantai Collection automation tool. This is fock from an archived project [kcauto](https://github.com/perryhuynh/kcauto).  
In comparison with **kcauto**, **kcauto_custom** is less flexible while being more automatic for easy daily use.  
Same as **kcauto**, **kcauto_custom** is based on vision-based automation and **kcauto_custom** provide bug fix and addition functions like auto factory and more fleet preset for higher level of automation.

***Warnning*** : This thing is not made for Windows(althought it could theoretically run on Windows), ***feel free to send me a bug report*** but I might or might not fix any compatibility problems.

---

> ### Disclaimer

> kcauto_custom is meant for educational purposes only. Botting is against the rules and prolonged usage of kcauto_custom may result in your account being banned. The developer of kcauto_custom takes no responsibility for repercussions related to the usage of kcauto_custom. You have been warned!

> Although unlikely, users may lose ships and equipment when using kcauto_custom to conduct combat sorties. While kcauto_custom has been painstakingly designed to reduce the chances of this happening, the developer of kcauto_custom does not take responsibility for any loss of ships and/or resources.

### Original features form kcauto

* Expedition &mdash; automate expeditions
* PvP Module &mdash; automate PvP
* Combat Module &mdash; automate combat sorties
* LBAS Module &mdash; automatic LBAS management
* Ship Switcher Module &mdash; automatic switching of ships based on specified criteria between combat sorties
* Fleet Switcher Module &mdash; automatic switching of fleet presets for PvP and combat sorties
* Quests Module &mdash; automatic quest management
* Repair & Resupply Modules &mdash; automatic resupply and repair of fleet ships
* Stats &mdash; keeps stats on various actions performed
* Click Tracking &mdash; optional tracking of clicks done by kcauto
* Scheduled and manual sleeping and pausing of individual modules or entire script
* Automatic catbomb and script recovery
* Random variations in navigation, timers, and click positions to combat bot detection
* Hot-reload config files
* Open-source codebase

### Features form kcauto_custom

* More fleet presets that you could define in a config file
* Auto akashi repair 
* Auto factory which runs the daily develop and ship building
* Auto selection of sortie map based on currently available quest (KC3 is needed in this mode)
* Support for 7-4
* Bug fix(Fleet Switcher Module, interaction_mode, quest handling etc.)

## Installation


* Install Python 3.7.3
  * Warning for Windows users: This thing is not tested on Windows, the script are made for linux at the first place. WSL might be able to do the magic, but there is not promise.
* (Unix only) Install additional pacakges `python3-tk scrot`
* Install pip if not already installed
* (Optional, but recommended) Install `pipenv` using `pip install pipenv`
* Install dependencies:
  * `pip`-mode: `pip install -r requirements.txt`
  * `pipenv`-mode: `pipenv shell`, then `pipenv install --ignore-pipfile`

## Kancolle setup

* Run Chrome or Chromium equivalent with the `--remote-debugging-port` option:
  * ex: `chrome --remote-debugging-port=9222`(For Windows user: If you don't know how to start chrome with options, read [this](https://stackoverflow.com/a/56457835))
  * Note: ***Use task manager to kill all chrome process first if needed.*** This remote-debugging-enabled instance of Chrome must be the *first* instance of Chrome run. If you have other Chrome windows open, close all of them before re-starting it with remote-debugging enabled. 
* Load Kancolle
  * First run: leave it in the 'Start' screen, where you press the button to enter homeport. You will not have to start kcauto from this screen in subsequent runs, although it is recommended you do this after each game maintenance to allow kcauto to load the latest game data.
  * Ensure that the game is scaled to 100% size/1x scaling &mdash; the entire game should be 1200 pixels wide and 720 pixels tall if you take a screenshot of it
  
## Running kcauto

The following assumes the `python` alias points to Python 3.7. If your alias for Python 3.7 is different (e.g. `python3`, `py -3`), modify the commands as needed. Run these commands on the command line/shell.

* (Windows only) First run `set PYTHONIOENCODING=utf-8`
* Run kcauto in CLI mode with a custom config file `custom.json` in the `configs` folder: `python kcauto -cli -cfg custom` (note that you do not add `.json` here)
* Or, run kcauto in CLI mode with a custom config file in a custom path: `python kcauto -cli -cfg-path <full-path-to-cfg>`

# Tutorial
Since I am not going to update the GUI from the original kcauto, you will have to learn how to edit your config.json.
But hey, I have put together a few template configs that you can start with, so let's go~

## Basic
There are 5 basic configs in the ```configs/template``` folder:
1. basic-1-1.json: Sortie to 1-1 with your current #1 fleet
```
	"combat.enabled":	true,             #Enable the combat module
	"combat.sortie_map":	"1-1",            #The map you want to go
	"combat.fleet_mode":	"standard",       #The fleet mode, could be "stf", "strike", "tcf" or "ctf" in event
...
...
	"combat.retreat_limit":	4,                 #Retreat if any ship is heavily damaged (3: medium damage, 2:Minor damage, 1:scratch damage)
	"combat.repair_limit":	2,                 #Repair a ship if it is Minor damaged 
	"combat.repair_timelimit_hours":	2, #Use a bucket if a repair takes more than 2 hrs
	"combat.repair_timelimit_minutes":	0,
...
...
	"combat.fleet_presets":	[],           #The fleet preset you want to use in combat(ex. 1 or 2 or 3 etc.)
```
2. basic-exp.json: Expedition to #1, #2 and #3
```
	"expedition.enabled":	true,         #Enable the expedition module
	"expedition.fleet_2":	[1],          #Go for #1(練習航海) expedition
	"expedition.fleet_3":	[2],          #Go for #2(長距離練習航海) expedition
	"expedition.fleet_4":	[3],          #Go for #3(警備任務) expedition
```
3. basic-factory.json: Finish the daily develop and ship building quest for you  
***This thing is gonna break if your port is full***, I will fix it but in the meantime, just be careful if you turn this on.
```
	"factory.enabled":	true,                         #Enable the factory module
	"factory.develop_recipe":	[10, 10, 10, 10],     #The develop recipe
	"factory.build_recipe":	[30, 30, 30, 30],             #The ship build recipe
```
4. basic-pvp.json: Finish the daily pvp for you
```
	"pvp.enabled":	true,               #Enable the pvp module
	"pvp.fleet_preset":	1,          #The fleet preset you want to use in pvp(ex. 1 or 2 or 3 etc.)
```
5. basic-akashi.json: Call akashi to fix your ships  
***You will need an akashi kai to use this module***, or you could change the "187" => "182" if you only have an **akashi**.
```
	"ship_switcher.enabled":	true,                     #Enable the ship_switcher module (auto akashi repair is base on this module)
	"ship_switcher.slots":	{
		"1":	"morale:!=:0|ship:187:>=:1:>=:0:!=:0::",  #Put akashi kai to the #1 slot
                                                                  #"2"~"6": Put a ship under Minor damage to the slot
		"2":	"damage:==:0,damage:>=:3|class:1:!=:1:==:1:!=:0::,class:1:!=:1:==:2:!=:0::,class:2:!=:1:==:1:!=:0::,class:2:!=:1:==:2:!=:0::,class:3:!=:1:==:1:!=:0::,class:3:!=:1:==:2:!=:0::,class:4:!=:1:==:1:!=:0::,class:4:!=:1:==:2:!=:0::,class:5:!=:1:==:1:!=:0::,class:5:!=:1:==:2:!=:0::,class:6:!=:1:==:1:!=:0::,class:6:!=:1:==:2:!=:0::,class:7:!=:1:==:1:!=:0::,class:7:!=:1:==:2:!=:0::,class:8:!=:1:==:1:!=:0::,class:8:!=:1:==:2:!=:0::,class:9:!=:1:==:1:!=:0::,class:9:!=:1:==:2:!=:0::,class:10:!=:1:==:1:!=:0::,class:10:!=:1:==:2:!=:0::,class:11:!=:1:==:1:!=:0::,class:11:!=:1:==:2:!=:0::,class:13:!=:1:==:1:!=:0::,class:13:!=:1:==:2:!=:0::,class:14:!=:1:==:1:!=:0::,class:14:!=:1:==:2:!=:0::,class:16:!=:1:==:1:!=:0::,class:16:!=:1:==:2:!=:0::,class:17:!=:1:==:1:!=:0::,class:17:!=:1:==:2:!=:0::,class:18:!=:1:==:1:!=:0::,class:18:!=:1:==:2:!=:0::,class:19:!=:1:==:1:!=:0::,class:19:!=:1:==:2:!=:0::,class:20:!=:1:==:1:!=:0::,class:20:!=:1:==:2:!=:0::,class:21:!=:1:==:1:!=:0::,class:21:!=:1:==:2:!=:0::,class:22:!=:1:==:1:!=:0::,class:22:!=:1:==:2:!=:0::",
		"3":	"damage:==:0,damage:>=:3|class:1:!=:1:==:1:!=:0::,class:1:!=:1:==:2:!=:0::,class:2:!=:1:==:1:!=:0::,class:2:!=:1:==:2:!=:0::,class:3:!=:1:==:1:!=:0::,class:3:!=:1:==:2:!=:0::,class:4:!=:1:==:1:!=:0::,class:4:!=:1:==:2:!=:0::,class:5:!=:1:==:1:!=:0::,class:5:!=:1:==:2:!=:0::,class:6:!=:1:==:1:!=:0::,class:6:!=:1:==:2:!=:0::,class:7:!=:1:==:1:!=:0::,class:7:!=:1:==:2:!=:0::,class:8:!=:1:==:1:!=:0::,class:8:!=:1:==:2:!=:0::,class:9:!=:1:==:1:!=:0::,class:9:!=:1:==:2:!=:0::,class:10:!=:1:==:1:!=:0::,class:10:!=:1:==:2:!=:0::,class:11:!=:1:==:1:!=:0::,class:11:!=:1:==:2:!=:0::,class:13:!=:1:==:1:!=:0::,class:13:!=:1:==:2:!=:0::,class:14:!=:1:==:1:!=:0::,class:14:!=:1:==:2:!=:0::,class:16:!=:1:==:1:!=:0::,class:16:!=:1:==:2:!=:0::,class:17:!=:1:==:1:!=:0::,class:17:!=:1:==:2:!=:0::,class:18:!=:1:==:1:!=:0::,class:18:!=:1:==:2:!=:0::,class:19:!=:1:==:1:!=:0::,class:19:!=:1:==:2:!=:0::,class:20:!=:1:==:1:!=:0::,class:20:!=:1:==:2:!=:0::,class:21:!=:1:==:1:!=:0::,class:21:!=:1:==:2:!=:0::,class:22:!=:1:==:1:!=:0::,class:22:!=:1:==:2:!=:0::",
		"4":	"damage:==:0,damage:>=:3|class:1:!=:1:==:1:!=:0::,class:1:!=:1:==:2:!=:0::,class:2:!=:1:==:1:!=:0::,class:2:!=:1:==:2:!=:0::,class:3:!=:1:==:1:!=:0::,class:3:!=:1:==:2:!=:0::,class:4:!=:1:==:1:!=:0::,class:4:!=:1:==:2:!=:0::,class:5:!=:1:==:1:!=:0::,class:5:!=:1:==:2:!=:0::,class:6:!=:1:==:1:!=:0::,class:6:!=:1:==:2:!=:0::,class:7:!=:1:==:1:!=:0::,class:7:!=:1:==:2:!=:0::,class:8:!=:1:==:1:!=:0::,class:8:!=:1:==:2:!=:0::,class:9:!=:1:==:1:!=:0::,class:9:!=:1:==:2:!=:0::,class:10:!=:1:==:1:!=:0::,class:10:!=:1:==:2:!=:0::,class:11:!=:1:==:1:!=:0::,class:11:!=:1:==:2:!=:0::,class:13:!=:1:==:1:!=:0::,class:13:!=:1:==:2:!=:0::,class:14:!=:1:==:1:!=:0::,class:14:!=:1:==:2:!=:0::,class:16:!=:1:==:1:!=:0::,class:16:!=:1:==:2:!=:0::,class:17:!=:1:==:1:!=:0::,class:17:!=:1:==:2:!=:0::,class:18:!=:1:==:1:!=:0::,class:18:!=:1:==:2:!=:0::,class:19:!=:1:==:1:!=:0::,class:19:!=:1:==:2:!=:0::,class:20:!=:1:==:1:!=:0::,class:20:!=:1:==:2:!=:0::,class:21:!=:1:==:1:!=:0::,class:21:!=:1:==:2:!=:0::,class:22:!=:1:==:1:!=:0::,class:22:!=:1:==:2:!=:0::",
		"5":	"damage:==:0,damage:>=:3|class:1:!=:1:==:1:!=:0::,class:1:!=:1:==:2:!=:0::,class:2:!=:1:==:1:!=:0::,class:2:!=:1:==:2:!=:0::,class:3:!=:1:==:1:!=:0::,class:3:!=:1:==:2:!=:0::,class:4:!=:1:==:1:!=:0::,class:4:!=:1:==:2:!=:0::,class:5:!=:1:==:1:!=:0::,class:5:!=:1:==:2:!=:0::,class:6:!=:1:==:1:!=:0::,class:6:!=:1:==:2:!=:0::,class:7:!=:1:==:1:!=:0::,class:7:!=:1:==:2:!=:0::,class:8:!=:1:==:1:!=:0::,class:8:!=:1:==:2:!=:0::,class:9:!=:1:==:1:!=:0::,class:9:!=:1:==:2:!=:0::,class:10:!=:1:==:1:!=:0::,class:10:!=:1:==:2:!=:0::,class:11:!=:1:==:1:!=:0::,class:11:!=:1:==:2:!=:0::,class:13:!=:1:==:1:!=:0::,class:13:!=:1:==:2:!=:0::,class:14:!=:1:==:1:!=:0::,class:14:!=:1:==:2:!=:0::,class:16:!=:1:==:1:!=:0::,class:16:!=:1:==:2:!=:0::,class:17:!=:1:==:1:!=:0::,class:17:!=:1:==:2:!=:0::,class:18:!=:1:==:1:!=:0::,class:18:!=:1:==:2:!=:0::,class:19:!=:1:==:1:!=:0::,class:19:!=:1:==:2:!=:0::,class:20:!=:1:==:1:!=:0::,class:20:!=:1:==:2:!=:0::,class:21:!=:1:==:1:!=:0::,class:21:!=:1:==:2:!=:0::,class:22:!=:1:==:1:!=:0::,class:22:!=:1:==:2:!=:0::",
		"6":	"damage:==:0,damage:>=:3|class:1:!=:1:==:1:!=:0::,class:1:!=:1:==:2:!=:0::,class:2:!=:1:==:1:!=:0::,class:2:!=:1:==:2:!=:0::,class:3:!=:1:==:1:!=:0::,class:3:!=:1:==:2:!=:0::,class:4:!=:1:==:1:!=:0::,class:4:!=:1:==:2:!=:0::,class:5:!=:1:==:1:!=:0::,class:5:!=:1:==:2:!=:0::,class:6:!=:1:==:1:!=:0::,class:6:!=:1:==:2:!=:0::,class:7:!=:1:==:1:!=:0::,class:7:!=:1:==:2:!=:0::,class:8:!=:1:==:1:!=:0::,class:8:!=:1:==:2:!=:0::,class:9:!=:1:==:1:!=:0::,class:9:!=:1:==:2:!=:0::,class:10:!=:1:==:1:!=:0::,class:10:!=:1:==:2:!=:0::,class:11:!=:1:==:1:!=:0::,class:11:!=:1:==:2:!=:0::,class:13:!=:1:==:1:!=:0::,class:13:!=:1:==:2:!=:0::,class:14:!=:1:==:1:!=:0::,class:14:!=:1:==:2:!=:0::,class:16:!=:1:==:1:!=:0::,class:16:!=:1:==:2:!=:0::,class:17:!=:1:==:1:!=:0::,class:17:!=:1:==:2:!=:0::,class:18:!=:1:==:1:!=:0::,class:18:!=:1:==:2:!=:0::,class:19:!=:1:==:1:!=:0::,class:19:!=:1:==:2:!=:0::,class:20:!=:1:==:1:!=:0::,class:20:!=:1:==:2:!=:0::,class:21:!=:1:==:1:!=:0::,class:21:!=:1:==:2:!=:0::,class:22:!=:1:==:1:!=:0::,class:22:!=:1:==:2:!=:0::"
	},
```
## Advance
In short, advance function could finish daily, weekly and monthly quest fully automated

It brings you a highly automated experience:
1. kcauto-custom picks a available quest for you
2. It loads the preset you defined in the config file
3. It sorties to the map which requested from the quest


On the other hand, the setup is a bit more complicated, you will have to tell kcauto-custom a few things
1. What ship combo you want to use in a map? (ex. In 2-1, I would want 2 CVLs, 1 CLT, and 3 DDs)
2. What ship want to use (ex. You need 3 DDs, so which DDs in your port?)
3. What quest you want to do?

With that said, let's begin the tutorial~

### Dependece
Since kcauto-custom has to track the progress of a quest, [KC3](https://chrome.google.com/webstore/detail/kancolle-command-center-%E6%94%B9/hkgmldnainaglpjngpajnnjfhpdjkohh) is needed for advance functions to work.

After installing KC3, go to KC3 setting => DMM Options => Apply Customizations => uncheck
![](https://i.imgur.com/fqjx8dM.png)

By the way, KC3 is an awesome plug-in, highly recommended installing it if you haven't done so.

### Config setup
There are three files you will need to setup in this tutorial, they are all locate in ```configs/template``` folder:
1. fleet_preset_first_try.json
2. fleet_list_first_try.json
3. advance-2-1.json

Let's start with ```fleet_preset_first_try.json```  
Well it's kinda simple
```
                         The #1 ship          The SECOND CVL in your config, we will talk about it later 
                              |                            |
                              V                            V
	"2-1":	[{"type":"CVL","id":0}, {"type":"CVL","id":1}, {"type":"CLT","id":0}, {"type":"DD","id":0}, {"type":"DD","id":1}, {"type":"DD","id":2}],
	  ^                                       ^
	  |                                       |
The map for this preset              It is a small aircraft carrier
	
```
That's it, not difficult but it is tedious when you have to set this up for every map, the good news is you could put it right once and for all.  
Let's focus on map 2-1 for now.


Next one is ```fleet_list_first_try.json```  
You will need to tell kcauto which ship you want to send,  
the id is unique for every single ship so you will have to find it out yourself.  
Remember KC3? The plug-in could show you the id like this:  
![](https://i.imgur.com/JgeJnOA.png)  
So the id of this inazuma is ```4```  
Now we could fill in the ```fleet_list_first_try.json```  
```
{	
          The id of your ship, This ship will be the {"type":"DD","id":0} in fleet_preset_first_try.json
                  |
		  V
	"DD":   [ 4, 1111, 1111],
	"DD_NAME":["inazuma","時雨 改二","夕立"],
                       ^
		       |
              The name of your ship
	      It does NOT affect kcauto so whatever name you like
}
```

There you go, fill in the rest in ```fleet_list_first_try.json``` then take a look in ```advance-2-1.json```  
There is nothing you will need to change in this file:  
```
	"combat.enabled":	true,
	"combat.sortie_map":	"2-1",        #The map we are going to
	"combat.fleet_mode":	"standard",
	...
	...
	"combat.fleet_presets":	["auto"],     #The fleet preset we use
```

Now, rename ```fleet_preset_first_try.json``` => ```fleet_preset.json```  
and ```fleet_list_first_try.json``` =>  ```fleet_preset.json```.  
Replace the ```fleet_list.json``` and ```fleet_preset.json``` in ```configs``` (DO NOT forget to backup)  
then run ```python kcauto --cli --cfg template/advance-2-1```

kcauto-custom should now load the ships you defined and go for 2-1!

---

### Advance -- quest handling

Now we have tell kcauto-custom what ship to use, but how do kcauto-custom run those daily, weekly quests automatically?

**Long story in short**: Use ```"combat.sortie_map":    "auto"``` in your config file, that's it!

**Long story in long**:  
There are 3 files that would affect the behaviour of quest & map picking (usually you don't have to edit them):
1. Your config file
2. ```data/quest/quest.json```
3. ```data/quest/quest_priority.json```

Let's take a look into the config file first:
```json!
	"quest.enabled":	true,       #Enable the quest module
	"quest.quests":	["Bd1", "Bd2", "Bd3", "Bd4", "Bd5", "Bd6", "Bd7", "Bd8", "Bw1", "Bw2", "Bw3", "Bw4", "Bw5", "Bw7", "Bw8", "Bw9", "Bw10", "Bm2", "Bm3", "Bm4", "Bm5", "Bm6", "Bm8", "Bq1", "Bq3", "Bq4", "Bq8", "Bq9", "Bq10", "Bq11", "Bq12", "C2", "C3", "C4", "C8", "C16", "C29", "D2", "D3", "D4", "D9", "D11", "D22", "D24", "E3", "E4", "F5", "F6", "F7", "F8"]
	# The quest that kcauto-custom will attemp to finish
```
kcauto-custom will only handle the quests mentioned in `quest.quests`, you could remove those you don't want to finish, though it is not recommanded to add any quest into it.  
(Since there are quest that `advance` cannot handle at the moment)


Next one is ```data/quest/quest.json```, this file contains the details of a quest. Again, usually you wouldn't want to edit it.
```json!

  "Bd1": {                         #The quest name
    "id": 201,                     #The quest ID
    "type": "daily",               #The quest type
    "intervals": [1, 0, 0],        #Intervals between kcauto-custom checking if the quest is finished, with the order as [sortie, pvp, expedition]
    "recommended_map": ["1-1"]     #The map which kcauto-custom will sortie to is no info could gather from KC3
  }

```


The last one is ```data/quest/quest_priority.json```, it defines what quest kcauto-costom will prioritizes when user is in auto sortie_map mode (```"combat.sortie_map":	"auto"```)
```json!
{
  "daily":      ["Bd5","Bd4","Bd6","Bd8"],
  "weekly":     ["Bw2","Bw5",...,"Bw10"],
  "monthly":    ["Bm1","Bm2",...,"Bm7","Bm8"],
  "quarterly":  ["Bq1","Bq2",...,"Bq12","Bq13"],
  "yearly":     ["By1","By2",...,"By12","By13"],
  "low_priority":    ["Bw1","Bw3",...,"Bd2","Bd3"]
}
```

The priority here is `daily` > `weekly` > `monthly` > `quarterly` > `yearly` > `low_priority`


Finally, let's take a look into `configs/template/fleet_preset_idea.json`, this file shows you some ideas of fleet presets in different maps.
```json!
	"2-5-Bm1":	[{"type":"BBV","id":0}, {"type":"Myoko","id":0}, {"type":"Nachi","id":0}, {"type":"Haguro","id":0}, {"type":"CAV","id":0}, {"type":"CAV","id":1}],
	
	"1-4-Bm3":	[{"type":"CL","id":0}, {"type":"CL","id":1}, {"type":"DD","id":0}, {"type":"DD","id":1}, {"type":"DD","id":2}, {"type":"DD","id":3}],
```

The `Bm1` and `Bm3` here means the preset is specially made for the quest, that way when kcauto go for `Bm1`, it would pick the preset in `2-5-Bm1` first, instead of the normal `2-5` preset.

---


Ok, that's all for this week.
Next time I will update how to use those special made preset manually, and a FAQ section if possible. 
