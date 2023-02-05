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
  * ex: `chrome --remote-debugging-port=9222`
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
***You will need a akashi kai to use this module***, or you could change the "187" => "182" if you only have a **akashi**.
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
Since kcauto-custom has to track the progress of a quest, [KC3](https://chrome.google.com/webstore/detail/kancolle-command-center-%E6%94%B9/hkgmldnainaglpjngpajnnjfhpdjkohh) is needed for advance to work.

KC3 is an awesome plug-in, highly recommended installing if you haven't done so.

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
The map for this preset              It is a small aircraft carriers
	
```
That's it, not difficult but it is tedious when you have to set this up for every map.  
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

All right the tutorial ends here for now, but how to run those daily, weekly quests automatically?

After you finish filling in ```fleet_list.json``` and ```fleet_preset.json```,  
you could set ```combat.sortie_map``` to auto: 
```
"combat.sortie_map":	"auto",        # kcauto-custom picks the map for you 
```

Note that the setting of ```quest.quests``` WILL affect the behaviour of map picking,  
but I ran out of time so the tutorial about ```quest``` setting will be the job for another day...
