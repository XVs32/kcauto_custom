#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"

extern char BASE_PATH[500];

void ship_switch(cJSON *root, char *sortie_map){

    char file_path[500];

    strcpy(file_path, BASE_PATH);
    strcat(file_path, "fleet_preset.json");

    printf("%s\n", file_path);
    
    
    char comdst[8];
    strcpy(comdst, sortie_map);
    
    if(comdst[0] == '0'){

    }
    else if(comdst[0] == '8'){
        switch(comdst[2]){
            case '0':
                strcpy(comdst, "Bm2-6-1");
                break;
            case '1':
                strcpy(comdst, "Bm4-5-1");
                break;
            case '2':
                strcpy(comdst, "Bm6-4-2");
                break;
            case '3':
                strcpy(comdst, "Bm7-2-5");
                break;
            case '4':
                strcpy(comdst, "Bm8-1-2");
                break;
            case '5':
                strcpy(comdst, "Bm8-1-3");
                break;
            case '6':
                strcpy(comdst, "Bm3/Bm8-1-4");
                break;
            case '7':
                strcpy(comdst, "Bm8-2-1");
                break;
            case '8':
                strcpy(comdst, "2-2-A");
                break;
            case '9':
                strcpy(comdst, "5-2-C");
                break;
        }
    }
    else if(comdst[0] == '9'){
        switch(comdst[2]){
            case '0':
                strcpy(comdst, "Bq3-1-6");
                break;
            case '1':
                strcpy(comdst, "Bq5-3-1");
                break;
            case '2':
                strcpy(comdst, "Bq5-3-2");
                break;
            case '3':
                strcpy(comdst, "Bq5-3-3");
                break;
            case '4':
                strcpy(comdst, "Bq9-1-3");
                break;
            case '5':
                strcpy(comdst, "Bq9/Bq11-1-4");
                break;
            case '6':
                strcpy(comdst, "Bq9/Bq11-2-1");
                break;
            case '7':
                strcpy(comdst, "Bq9/Bq11-2-2");
                break;
            case '8':
                strcpy(comdst, "Bq9/Bq11-2-3");
                break;
        }

    }
    
    printf("%s\n", comdst);

    cJSON *preset_root = read_json_file(file_path);
    cJSON *map = cJSON_GetObjectItem(preset_root, comdst);

    if(map == NULL){
        printf("Warning: No preset found in %s, disable ship_switcher.\n", file_path);
        cJSON_AddBoolToObject(root, "ship_switcher.enabled", 0);
        cJSON_AddObjectToObject(root, "ship_switcher.slots");
    }
    else{
        cJSON_AddBoolToObject(root, "ship_switcher.enabled", 1);
        cJSON *spsw = cJSON_AddObjectToObject(root, "ship_switcher.slots");
        int i;
        char slot[5];
        char condition[50];
        for(i=0;i<6;i++){
            cJSON *ref = cJSON_GetArrayItem(map, i);
            char *ship_type = cJSON_GetObjectItem(ref, "type")->valuestring;
            printf("shiptype %s\n", ship_type);
            int id = cJSON_GetObjectItem(ref, "id")->valueint;
            printf("id %d\n", id);

            cJSON *ship = cJSON_GetObjectItem(preset_root, ship_type);
            int ship_id = cJSON_GetArrayItem(ship, id)->valueint; 
            printf("ship_id %d\n", ship_id);
                   
            sprintf(slot, "%d", i+1);
            sprintf(condition, "morale:!=:0|ship:%d:>=:1:>=:0:!=:0::", ship_id);
            cJSON_AddItemToObject(spsw, slot, cJSON_CreateString(condition));
        }
    }

    return;
}

void akashi_repair(cJSON *root){
    
    cJSON_AddBoolToObject(root, "ship_switcher.enabled", 1);
    cJSON *spsw = cJSON_AddObjectToObject(root, "ship_switcher.slots");
    
    cJSON_AddStringToObject(spsw, "1", "morale:!=:0|ship:187:>=:1:>=:0:!=:0::");
    
    char cond[2048];
    int i,j;
    for(j=0;j<3;j++){
        strcpy(cond,"damage:==:0,damage:>=:3|");
        char slot[2] = {'\0'};
        slot[0] = j + 2 + '0';
        for(i=0;i<22;i++){
            if(i==12-1||i==15-1){continue;}
            char buf[50];
            sprintf(buf,"class:%d:!=:1:==:1:!=:0::,",i+1);
            strcat(cond,buf);
            sprintf(buf,"class:%d:!=:1:==:2:!=:0::,",i+1);
            strcat(cond,buf);
        }
        cond[strlen(cond)-1] = '\0'; //drop the last commarc and end the string.
        cJSON_AddStringToObject(spsw, slot, cond);
    }
    
    //switch in a whatever no damage DD, for easier PvP for others, cannot use morale here, or this will keep switching lol
    cJSON_AddStringToObject(spsw, "5", "damage:!=:0|class:2:!=:1:==:0:!=:0::");
    cJSON_AddStringToObject(spsw, "6", "damage:!=:0|class:2:!=:1:==:0:!=:0::");
    
    return;
}
