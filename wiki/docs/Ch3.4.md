_Automation is good, so long as you know exactly where to put the machine_

---

## Overview -- `Factory module`

**Factory module automatically handle daily develop and construction for you. Simple.**

To make sure user notice they have to setup `Factory module` before enabling it,  
factory module is **disabled by default**.  

You can enable it by editing your config file (`configs/config_cui.json` for CUI user),  
this can be done by changing `factory.enabled` to `true`.  
**Close the CUI panel before doing this, or else CUI might not notice the update you made.**

```json
    "factory.enabled": true,
```

***Enabling factory module***

---

## Factory panel

The factory panel could be open with `"` key (`shift` + `'`) in home page.  
User can setup the recipe and secretary ship for construction and development, respectively. 
Press `"` key again to leave.

<img width="360" height="146" alt="image" src="https://github.com/user-attachments/assets/f0ebc274-7523-4655-97f3-a501cec4b9f5" />

***Decide how many resources to invest***

---

## Selecting secretary ship by id
The id of secretary ship can be found in [plugin-ship-info](https://github.com/poooi/plugin-ship-info),  
it is the production id of the ship.  

<img width="398" height="174" alt="image" src="https://github.com/user-attachments/assets/6f8a1e75-54ae-4996-a68a-bb81d2525322" />
 
<img width="206" height="62" alt="image" src="https://github.com/user-attachments/assets/acb251f4-e88e-4171-b1c3-bf0e2401b08f" />

*Production id show in ship girls info*

So the id of this samidare is ```1```  
Now we could setup the secretary ship.   

<img width="439" height="134" alt="image" src="https://github.com/user-attachments/assets/b4ea5779-c20b-4b91-85c4-5610778244e7" />
<img width="439" height="134" alt="image" src="https://github.com/user-attachments/assets/ee91682a-4ed0-49a9-9a07-5f63c5ecabc5" />

***Specify secretary ship***

---

## Selecting secretary ship by ship type

Beside using ID, 
user can assign secretary ship by ship type

<img width="440" height="120" alt="image" src="https://github.com/user-attachments/assets/1e90613a-b7be-4f6b-89ff-0b54e917e854" />

---

## Disable specifing secretary ship

When secretary ship id is set to `0`,  
kcauto_custom would not switch secretary ship before commiting for construction or development.  

<img width="358" height="146" alt="image" src="https://github.com/user-attachments/assets/49628fd4-e7d7-45d2-9d83-abfaaad1a7fc" />

***Do not switch for specific secretary ship***

Press `"` key again to leave.

---





