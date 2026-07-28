## Common
_You need to do this no matter what_

* Run POI(Brave stopped supporting V2 manifest too... farewell KC3) with `debug` mode
  * ***Use task manager to kill all POI process if needed.***   
This debug instance of POI must be the *first* instance for POI to run. If you have other POI windows open,  
close all of them before re-starting with `remote-debugging` enabled. 
  * Example: `poi --remote-debugging-port=9222 --remote-allow-origins=*`  
(For Windows user: If you don't know how to start POI with options, read [this](https://stackoverflow.com/a/56457835))  
(`--remote-allow-origins=*` is needed at the moment (2023/05/04)[ref](https://github.com/XVs32/kcauto_custom/issues/19)):
  * How do I know if the `debug` mode is on?
    * :heavy_check_mark:Access `127.0.0.1:9222`, you should see a blank screen as follow:  
![Screenshot from 2023-05-04 22-34-30](https://user-images.githubusercontent.com/16824564/236221380-f2b52443-b2f7-4510-899f-c8582f431d12.png)  
    * :x:Kill ALL POI process and retry if you see this:  
![Screenshot from 2023-05-04 22-28-56](https://user-images.githubusercontent.com/16824564/236221730-c5445cc8-b270-4cb9-b7d2-0ed4f892be56.png)  

* Install plugin `poi-plugin-noro6-exporter` and `poi-plugin-forwarder`

<img width="474" height="707" alt="image" src="https://github.com/user-attachments/assets/570ebbfa-ca5f-4082-a340-ebee58ccd6c2" />

* **For Linux(Ubuntu) users**:  
Wayland in Ubuntu does not work well with kcauto(and a lot of other stuffs, lol)  
You would want to run your Ubuntu with the good old X-windows  
![image](https://github.com/user-attachments/assets/696ed225-09da-4254-9a1c-956c4c1f87f9)    

---

## Start Up
Pick one from **Beginner**, **Gamer** or **Developer**

### Beginner  
_You have limited features but easiest installation and setup._

* Windows
    * Double click `kcauto_cui.exe` 
* Linux
    * Run `./kcauto_cui`

That's it!

### Gamer  
_You have to deal with Noro6 but full access to all features._

* Windows
    * run `.\kcauto_cui.exe` in Powershell for better user experience
    * or, run `.\kcauto_custom.exe --cfg <your_config_name>` to specify your own config file  
      (note that you do not need to add `.json` here)
* Linux
    * Run `./kcauto_cui`
    * or, run `./kcauto.bin --cfg <your_config_name>` to specify your own config file  
      (note that you do not need to add `.json` here)

### Expert
_Tweak everything from config file like a pro. Not for kid._

Always keep your backup.  
Do not join if you don't know what you're doing.

See Ch4 for detail

### Developer
_Your own Python environment, free to edit/fix the tool yourself._

* Install Python 3.11 and pip
* Install `pipenv` using `pip install pipenv`
* Create your `.venv`, quick [ref](https://gist.github.com/ryumada/c22133988fd1c22a66e4ed1b23eca233) if you forgot how to make one
* Activate venv by `source .venv/bin/activate`
* Install dependencies:
  * ```pip install -r requirements.txt```
* Check `requirements.txt` for more instructions if you find yourself missing library

* Windows
    * run `python .\kcauto\kcauto_cui.py`
    * or, run `python kcauto --cfg <your_config_name>` to specify your own config file  
      (note that you do not need to add `.json` here)
* Linux
    * Run `python3 ./kcauto/kcauto_cui.py`
    * or, run `python3 kcauto --cfg <your_config_name>` to specify your own config file  
      (note that you do not need to add `.json` here)

---



