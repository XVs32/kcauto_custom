#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void expedition(cJSON *root, int enable, int *exp){

    cJSON_AddBoolToObject(root, "expedition.enabled", enable);

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

void expedition_set(int *exp_dst, int mode){

    switch(mode){
        case 0: //optimal
            exp_dst[0]=6;
            exp_dst[1]=2;
            exp_dst[2]=3;
            break;
        case 1: //fuel
            exp_dst[0]=5;
            exp_dst[1]=21;
            exp_dst[2]=38;
            break;
        case 2: //ammo
            exp_dst[0]=2;
            exp_dst[1]=5;
            exp_dst[2]=37;
            break;
        case 3: //steel
            exp_dst[0]=3;
            exp_dst[1]=37;
            exp_dst[2]=38;
            break;
        case 4: //balance
            exp_dst[0]=6;
            exp_dst[1]=37;
            exp_dst[2]=38;
            break;
        case 5: //night
            exp_dst[0]=12;
            exp_dst[1]=11;
            exp_dst[2]=24;
            break;
        default:
            exp_dst[0]=1;
            exp_dst[1]=2;
            exp_dst[2]=3;
    }
    return;
}