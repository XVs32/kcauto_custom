#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void expedition(cJSON *root, int *exp){

    cJSON_AddBoolToObject(root, "expedition.enabled", 1);

    cJSON *fleet[3];
    int i;
    char buf[50];
    for(i=0;i<3;i++){
        sprintf(buf,"expedition.fleet_%d",i+2);
        fleet[i] = cJSON_CreateArray();
        cJSON_AddItemToObject(root, buf, fleet[i]);

        if(exp[i] == 0){
            continue;
        }
        cJSON_AddItemToObject(fleet[i], "", cJSON_CreateNumber(exp[i]));
    }

    return;
}
