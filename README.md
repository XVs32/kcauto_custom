# kcauto_custom

**kcauto_custom** is a command line Kantai Collection automation tool. This is fock from an archived project [kcauto](https://github.com/perryhuynh/kcauto).  
In comparison with **kcauto**, **kcauto_custom** is less flexible while being more automatic for easy daily use.  
Same as **kcauto**, **kcauto_custom** is based on vision-based automation and **kcauto_custom** provide bug fix and addition functions like auto factory and more fleet preset for higher level of automation.

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

## Installation

***Warnning*** : This thing is not made for Windows, althought it could theoretically run on Windows, I might or might not fix any compatibility problems.

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
  
### Preset setup
**You would need to do this only if yor are wishing to use start_up/auto_starter scirpt.**  
Open ```configs/fleet_preset.json```, replace the ship id with the ship you want to use.
You can find ship id from the wiki [here](https://m.kcwiki.cn/wiki/%E6%A8%A1%E5%9D%97:%E8%88%B0%E5%A8%98%E6%95%B0%E6%8D%AE), or start_up scirpt dose provide the ship id in fleet 1 (when start_up script is running in akashi repair mode)



## Running kcauto

The following assumes the `python` alias points to Python 3.7. If your alias for Python 3.7 is different (e.g. `python3`, `py -3`), modify the commands as needed. Run these commands on the command line/shell.

* (Windows only) First run `set PYTHONIOENCODING=utf-8`
* Run kcauto in GUI mode: `python kcauto`
* Or, run kcauto in CLI mode: `python kcauto --cli`
  * Run kcauto in CLI mode with a custom config file `custom.json` in the `configs` folder: `python kcauto -cli -cfg custom` (note that you do not add `.json` here)
  * Run kcauto in CLI mode with a custom config file in a custom path: `python kcauto -cli -cfg-path <full-path-to-cfg>`

### Running start_up script
Simply run ```./start_up.sh``` and follow the instructions, reply with number

### Running auto_start_up script
Simply run ```./auto_starter.sh``` and it will do the job for you



