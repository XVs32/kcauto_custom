_Humanity is acquiring all the right technology for all the wrong reasons._

---

## Overview -- `Expedition mode: Auto`

`Expedition mode: Auto` is a fully automated expedition mode, it is capable to:

1. Assign ships to form a valid fleet for specific expedition
2. Balance player's resources by picking the most efficient expedition
3. Handle Landing Craft and Drum Canisters requirements 
4. Load fleets in Noro6 config if provided (See [section](https://github.com/XVs32/kcauto_custom/wiki/Ch3.2:-Gamer-user-guide-%E2%80%90%E2%80%90-Expedition#noro6) `Noro6`)

<img width="889" height="928" alt="image" src="https://github.com/user-attachments/assets/f46ca530-b1ab-4861-9ee4-680fb6a99070" />

***A simplified overview of `Expedition mode: Auto`***

---

## Ship pool
~~Same as combat module, ship pool is defined in ```ship_pool.json```.~~  
~~*You will have to set this up yourself.*~~

No, you don't have to set up the ship pool anymore  
Any ship which matches ALL in the following:

1. NOT assigned in ANY config in Noro6
2. Locked 
![image](https://github.com/user-attachments/assets/5198fb72-ab68-4c9d-a692-f6c252069d18)

Are automatically assigned to EXP ship pool

<img width="817" height="436" alt="image" src="https://github.com/user-attachments/assets/eb899526-2a3a-47ce-9848-66ddfcaf08c0" />

***How expedition ship pool is defined***

---

## Noro6
For combat expedition(ex. `A5`, `A6`) or expedition require ships occupied by Noro6 already,  
you can define an expedition Noro6 config so kcauto can still run those expeditions. 

### This only works when sortie and PvP are both disabled,  
since all Noro6 configs share the same ship and equipment pool

<img width="922" height="557" alt="image" src="https://github.com/user-attachments/assets/9f85be79-2b73-4f3a-8847-768dffa8797a" />

***Example of expedition Noro6 config***

### Setting up config

<img width="110" height="204" alt="image" src="https://github.com/user-attachments/assets/637e2009-a219-426f-bab0-587fce4b71b8" />

***Example file name for expedition config***

Things to be aware of:

1. The file name of every expedition config must be `D-<Expedition ID>`.  
For example, `D-A3` is the config made for `A3`,  
2. You can assign both ships and equipment in a config.
3. Noro6 config has priority over kcauto_custom's auto assigned fleet
4. **Again, expedition which reference Noro6 only works when sortie and PvP are both disabled,  
since all Noro6 configs share the same ship and equipment pool**
5. Feel free to add your own config 

The general idea is the same as sortie noro6 config in [Ch3.1](https://github.com/XVs32/kcauto_custom/wiki/Ch3.1:-Gamer-user-guide-%E2%80%90%E2%80%90-Sortie) 

---

## Ship assign
You can enable ship assign by selecting `auto`.

![螢幕擷取畫面 2023-07-18 194649](https://github.com/XVs32/kcauto_custom/assets/16824564/bd1a9f45-191d-41b4-9b4e-819417b3534e)

It's been a while but this is not an early version of `expedition mode: auto` anymore. 
`expedition mode: auto` now :

1. Does handle Level requirement
2. Does handle Drum Canister and landing crafts bonus requirement
3. Does handle expeditions like A1, B6 etc. (with the help from Noro6)
4. Expedition set is pick on fly, not on startup only anymore
5. Fleet switch would happens on whichever idle fleet, without the need of waiting for all fleets to return
