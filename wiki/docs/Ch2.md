_Journey of a thousand miles begins with single step._

---

![Panel](https://github.com/XVs32/kcauto_custom/assets/16824564/0d582a36-60fb-4e18-b660-4b4c84a5cb18)


* Move around
    * Arrow key
* Confirm/Select
    * Enter key
* Exit
    * Esc key
* Pause on fly
    * Spacebar

---
### Expedition
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/2846046b-4800-4e67-8a3b-eb8bea06a706)

The expedition sets are locate in `.\data\expedition\expedition_preset.json`  
You can change the expedition Id as needed.
```
{
               #2(長距離練習航海)        #3(警備任務)     #6(防空射撃演習)
  "active":         [[2],                 [3],              [6]],
  "passive":      [[5],[21],[38]],
  "overnight":    [[11],[24],[38]],
  "user":  [[],[],[21]]
}
```

Auto assign is not available in beginner guide, please select `disable` here.  
![image](https://github.com/XVs32/kcauto_custom/assets/16824564/d2e35af7-314a-4226-9a1b-ede83bd1926f)

---
### Combat

![image](https://user-images.githubusercontent.com/16824564/236396966-32b58de4-0aaa-481e-a2fc-f31213592a8d.png)

#### Manual sortie mode
First, select your map with arrow key.  
![image](https://user-images.githubusercontent.com/16824564/236397921-9c79af0b-1edb-44b3-a0ee-8609d54b790a.png)  
Then select your kancolle in-game fleet preset(select `disable` to use the current fleet).  
![image](https://user-images.githubusercontent.com/16824564/236398074-ffff1651-e646-4331-979f-ca4c4d9873bf.png)  

#### Akashi repair
After selecting `disable(akashi mode)` in sortie menu,  
you could choose to turn on akashi repair.  
(you need an akashi kai to use this)  
![image](https://user-images.githubusercontent.com/16824564/236397397-689805f8-bfb5-4034-b5b1-14f11d9ce40c.png)

---

### PVP
Disalbe pvp or select the kancolle in-game fleet preset for pvp  
![image](https://user-images.githubusercontent.com/16824564/236402275-ee8a1fc6-812c-4208-bbfa-f0f6629a035b.png)

---

### Scheduler

![image](https://user-images.githubusercontent.com/16824564/236401065-96636c78-fcc9-476f-89bb-690e27a17657.png)

#### End time
The time to shutdown kcauto_custom(select the time with arrow key)  
(you should never run kcauto_custom 7/24)

![image](https://user-images.githubusercontent.com/16824564/236399553-8897a4ec-7d5c-4977-a039-752925a18fe7.png)

#### Sortie count
After the specified number of sorties, kcauto_custom will stop sortie.  
(select the sortie count with arrow key)  
![image](https://user-images.githubusercontent.com/16824564/236400038-03892b63-9cc9-4442-a490-2ce8ca0396c1.png)

---

### Quest panel

<img width="445" height="340" alt="image" src="https://github.com/user-attachments/assets/2fe76be4-ce87-40e1-a4a5-612383a8a72b" />

Press `?` (shift + /) key in home page,  
you can select what quest kcauto_custom will attempt to finish,  
press `?` again to leave quest panel

---

### Start kcauto_custom

#### On your first run, you would need to start kcauto in splash screen

![???](assets/569605507.png)

Select log panel, and reload your config.  
![image](https://user-images.githubusercontent.com/16824564/236402505-1eade161-ca58-4ab4-80da-7f9d7ff4bbc1.png)  
![image](https://user-images.githubusercontent.com/16824564/236402785-c0cd0858-cbad-41be-8c83-500a2e99003c.png)



You might get hit by the following error on the first run:
```java
[SUCCESS][2026-02-23 17:35:36] Initializing kcauto.
[DEBUG][2026-02-23 17:35:36] Loading data from 'configs/config_cui.json'.
[DEBUG][2026-02-23 17:35:36] Loading data from 'data/config/config_cui_template.json'.
[DEBUG][2026-02-23 17:35:36] Combat config init called
[DEBUG][2026-02-23 17:35:36] SET _sortie_map_read_only: {MapEnum(value)}
[DEBUG][2026-02-23 17:35:36] _repair_bucket_threshold set 500
[SUCCESS][2026-02-23 17:35:36] Config successfully loaded.
[DEBUG][2026-02-23 17:35:36] Loading data from 'data/temp/reinforce_general_category.json'.
[ERROR][2026-02-23 17:35:36] Reinforce equipment data not found, please start kcauto from splash screen
[ERROR][2026-02-23 17:35:36] [Errno 2] No such file or directory: 'data/temp/reinforce_general_category.json'
[DEBUG][2026-02-23 17:35:36] Loading data from 'data/temp/equipment_list.json'.
[ERROR][2026-02-23 17:35:36] Equipment data not found, please start kcauto from splash screen
[ERROR][2026-02-23 17:35:36] [Errno 2] No such file or directory: 'data/temp/equipment_list.json'
```

This is because kcauto_custom has never get the data it needs from kancolle.  
As long as your `data/temp` folder is fill with the following files after the first run,  
you are fine and can simply run kcauto_custom for second time.

<img width="870" height="256" alt="image" src="https://github.com/user-attachments/assets/0be41038-5a54-4f44-a7e8-60657589a91c" />

*All the temp files kcauto_custom acquire from kancolle*

~~***For Windows user:***~~  
~~There are reports show that kcauto_custom does not work well with `chrome_driver` mode on Windows.~~   
~~If you are having issue on mouse control,~~  
~~it is recommended to switch to `direct_control` mode.~~  

~~**How to:**~~  
~~1. Run kcauto_custom once~~  
~~2. Close kcauto_custom~~  
~~3. Open `configs/config_cui.json`~~  
~~4. Edit `"general.interaction_mode": "chrome_driver",` => `"general.interaction_mode": "direct_control",`~~  
~~5. Save and close~~  

Windows mouse issue should be fixed in latest version.(2026/07/28)

