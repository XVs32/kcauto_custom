_Humanity is acquiring all the right technology for all the wrong reasons._

---

## Overview -- `PvP mode: Auto`

`PvP mode: Auto` follow the same principle as `sortie mode: Auto` and `expedition mode: Auto`,  
it finish PvP quests automatically: 

1. User can setup fleet presets in Noro6
2. kcauto_custom pick a PvP quest
3. kcauto_custom load the corresponding fleet and attempt to finish the quest

---

## PvP quest handling

To prevent kcauto_custom from selecting every available PvP quest,  
kcauto_custom now has the ability to judge if the fleet matches the requirement of a quest. 

For example, if the fleet doesn't has 1CL+3DD or 4DD,  
kcauto_custom would not select the quest [`Cq4 (小艦艇群演習強化任務)`](https://wikiwiki.jp/kancolle/%E4%BB%BB%E5%8B%99#id-Cq).  
Or a warning will be sent if kcauto_custom is forced to attempt to finish this quest.

<img width="855" height="58" alt="image" src="https://github.com/user-attachments/assets/8beffcae-c763-4223-83c4-8b0b63c39930" />  

***Warning message for non valid fleet***

---

## Noro6

Here are things to be aware of:

1. The file name of every PvP config must be `C<quest id>-pvp`.  
For example, `Cm2-pvp` is the config made for quest `Cm2`,  
2. You can assign both ships and equipment in a config.
3. Feel free to add your own config 

<img width="138" height="255" alt="image" src="https://github.com/user-attachments/assets/2b95b355-6787-49c9-b9a3-cc1c2fcb8347" />

***Example PvP config name***

---

## Use `PvP mode: Auto` in kcauto_cui

After finishing all config you need,  
you can use this from kcauto_cui.  

<img width="489" height="260" alt="image" src="https://github.com/user-attachments/assets/6cbe212a-8668-4578-b0a6-e5317e328a37" />
