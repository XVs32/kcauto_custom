# kcauto_custom

### ***Lastest download link: [Windows](https://github.com/XVs32/kcauto_custom/releases/tag/Windows_v1.0.0_pre-release), [Linux](https://github.com/XVs32/kcauto_custom/releases/tag/Linux_v1.0.0_pre-release)***

**kcauto_custom** is a linux customized version of an archived project [kcauto](https://github.com/perryhuynh/kcauto) that includes additional features and functionality.  
In comparison with **kcauto**, **kcauto_custom** is less flexible while being more automatic for easy daily use.  
This tool is designed to help users automate repetitive tasks such as Expedition, Combat, PvP, Repair & Resupply, ultimately saving time and improving efficiency. 

***Warnning*** : kcauto_custom is not made for Windows(althought it could theoretically run on Windows), I might or might not fix any compatibility problems.

![image](https://user-images.githubusercontent.com/16824564/236409480-df6d6c27-9d64-417a-b515-12df1fa5e5d8.png)


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

* CUI(Character User Interface) for daily use cases
* More fleet presets that you could define in a config file
* Auto akashi repair 
* Auto factory which runs the daily develop and ship building
* Auto selection of sortie map based on currently available quest (KC3 is needed in this mode)
* Support for 7-4
* Bug fix(Fleet Switcher Module, interaction_mode, quest handling etc.)

## Installation

[wiki](https://github.com/XVs32/kcauto_custom/wiki/Ch1:-Setup-guide)  
For non-developer:
* Windows
    * Double click `kcauto_cui.exe` 
        * Or, run `.\kcauto_cui.exe` in Powershell for better user experience
* Linux
    * Run `./kcauto_cui`
    
---

For developer(Those who know what they are doing):
* Install Python 3.7.3
* (Unix only) Install additional pacakges `python3-tk scrot`
* Install pip if not already installed
* (Optional, but recommended) Install `pipenv` using `pip install pipenv`
* Install dependencies:
  * `pip`-mode: `pip install -r requirements.txt`
  * `pipenv`-mode: `pipenv shell`, then `pipenv install --ignore-pipfile`

## Wiki page
[Setup guide](https://github.com/XVs32/kcauto_custom/wiki/Ch1:-Setup-guide)  
[Beginner user guide](https://github.com/XVs32/kcauto_custom/wiki/Ch2.1:-Beginner-user-guide)  
