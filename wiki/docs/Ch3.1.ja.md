_No pain, no gain_

---

## Overview -- `Sortie mode: Auto`
In short, `Sortie mode: Auto` could finish daily, weekly and monthly quests fully automated

It brings you a highly automated experience:

1. kcauto-custom picks an available quest for you
2. It loads the preset you defined in Noro6
3. It sorties to the map which requested from the quest

![image](https://github.com/user-attachments/assets/3b141ad3-aae7-4c31-9949-f477bc9760a1)
　　　　***Setup your combat fleets in noro6***

On the other hand, the setup is a bit more complicated, you will have to setup a few things in Noro6 and kcauto_custom

1. map and quest id: What map does this fleet(編成) file setup for(ex. is it for 1-5? or 6-3 from Bq4?)
2. Ship and equipment: What ship and equipment to use
3. Quest pool: What quest you want to do

With that said, let's begin~

---

## Dependece

### Noro6
I mean... it's obvious we need this, right?  

[Noro6](https://noro6.github.io/kc-web/#/aircalc) is a great simulator and you can import your ship & equipment pool to setup your own fleet.  

More on that later.

---

## Config setup
There are three steps to setup your noro6 config file, a template is located in `configs/noro6/noro6`:

1. Export your ship and equipment to noro6
2. Create your noro6 config
3. Import the noro6 config to kcauto_custom

---

### Exporting

Let's start with exporting your own ship and equipment to noro6  
Well it's kinda simple, 

Open `Noro6 Exporter`

<img width="474" height="172" alt="image" src="https://github.com/user-attachments/assets/94ae6c1b-b111-47c3-9e7a-7a2a691df1ba" />

Click export to Noro6

<img width="339" height="117" alt="image" src="https://github.com/user-attachments/assets/3e465fc7-b8db-4f6b-ada5-6c3e19c7422a" />

![image](https://github.com/user-attachments/assets/ee4eff82-e3bf-448a-be37-1605dc388a6f)
***Your are automatically switched to noro6!***

Now click setting, then import the tutorial in "configs/noro6/noro6_template"  
![Screenshot from 2024-10-31 01-44-44](https://github.com/user-attachments/assets/48e0a662-bc35-46bf-b0cb-0b5a475dc0f1)  


<img width="496" height="157" alt="Screenshot_20260203_155850" src="https://github.com/user-attachments/assets/adf20a4a-8feb-4a0e-a7d7-73b14d40294a" />  


<img width="576" height="345" alt="image" src="https://github.com/user-attachments/assets/9aa14bdd-75fb-4a8f-a374-6d10cc030f47" />  

***That's it, we are done!***

---

### Setting up config

Next step, we are going to edit a fleet config  

Let's open `B-1-1`  
<img width="406" height="159" alt="image" src="https://github.com/user-attachments/assets/56b0adcc-406f-47bb-b1e8-704c60389a80" />

Ummmm... What can I say?  
Just set up your fleet and equipment here, don't forget to save I guess?  
There will be lots of configs to setup, the clipboard function in noro6 is a life saver.

![image](https://github.com/user-attachments/assets/7093eb12-26ed-41e8-b9ac-070e0c479348)  
　　　　***setup fleet in noro6***

![image](https://github.com/user-attachments/assets/21314488-3e17-4ae7-a813-929120b81180)  
　　　　***clipboard function could save you effort***


---

### Import to kcauto_custom

Click setting => Create backup file => Overwrite the `configs/noro6/noro6` template, that's it.


![Screenshot from 2024-10-31 12-39-55](https://github.com/user-attachments/assets/863037fc-d8d4-4879-b00f-7129d117d936)

---

### `Sortie mode: Auto` test run

After you setup `B-1-1` config,  
you can use this from kcauto_cui

<img width="543" height="351" alt="image" src="https://github.com/user-attachments/assets/0b1b5822-1ab8-46ee-95b6-3f829aaab646" />

　　　　***That's it, let's try it out!***

---

### Put together your own sortie noro6 config

The `B-1-1` is a huge step, but that alone doesn't do much.  
Now you want to create noro6 configs as needed,  
here are things to be aware of:

1. The file name of every fleet config must be `B<quest_id>-<world>-<stage>-<target_node>`.  
For example, `B-1-1` is the config made for `1-1`,  
`By6-1-2` is the config specially made for `1-2` in quest `By6`,  
`B-7-2-G` is the config made for `7-2-G`.
2. You can assign both ships and equipment in a config.
3. LBAS (Land-Based Air Squadrons) assign is sadly **NOT** supported yet.
4. If a quest specify config is not found(ex. `By6-1-2`), kcauto_custom would fall back to normal config (ex. `B-1-2`)
5. Feel free to add your own config (I am sure I've missed quite a few quest related configs)
6. **If you're too lazy to finish all the configs at once, REMOVE those you didn't setup, or kcauto_custom would get confuse**

---

**There is a template at `configs/noro6/noro6_template` to save you some naming time if you want to finish your setup in once  
You do have to remove those unuse config if you decide to start from this template**

---

<img width="1014" height="891" alt="image" src="https://github.com/user-attachments/assets/43ad5ea6-eba0-40fa-b7c4-80c757413b9f" />  

　　　　***An example of configs***

---

## Use `Sortie mode: Auto` in kcauto_cui

After finishing all config you need,  
you can use this from kcauto_cui

![image](https://user-images.githubusercontent.com/16824564/236405886-2115dcdd-35b7-4d0c-8e09-71c09bc51595.png)

---



