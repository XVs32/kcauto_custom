#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void scheduler(cJSON *root, int sorties_run, int stop_after_combat){

    cJSON_AddBoolToObject(root, "scheduler.enabled", 1);

    cJSON *rules = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "scheduler.rules", rules);
    cJSON_AddItemToObject(rules, "", cJSON_CreateString("time:2300:stop:kcauto:"));

    char buf[50];
    if(stop_after_combat){
        sprintf(buf, "sorties_run:%d:stop:kcauto:",sorties_run);
        cJSON_AddItemToObject(rules, "", cJSON_CreateString(buf));
    }
    else{
        sprintf(buf, "sorties_run:%d:stop:combat:",sorties_run);
        cJSON_AddItemToObject(rules, "", cJSON_CreateString(buf));
    }
   
   return; 
}

