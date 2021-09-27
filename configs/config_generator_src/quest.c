#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void quest(cJSON *root, int expedition_enable, int pvp_enable, int combat_enable, char *sortie_map){

    cJSON_AddBoolToObject(root, "quest.enabled", 1);

    cJSON *quests = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "quest.quests", quests);

    if(combat_enable){
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd1"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd2"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd3"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw1"));
        if(strcmp("1-5",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd8"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw5"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw10"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm5"));
        }
        else if(strcmp("1-6",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd8"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw5"));
        }
        else if(strcmp("2-1",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd4"));
            //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd5"));
            //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd6"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd7"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw2"));
            //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw3"));
            //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw4"));
        }
        else if(strcmp("2-2",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd5"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd6"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw3"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw4"));
        }
        else if(strcmp("2-3",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd4"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd7"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw2"));
        }
        else if(strcmp("3-3",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd4"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw2"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw7"));
        }
        else if(strcmp("4-1",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd4"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd5"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd6"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd8"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw2"));
            //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw3"));
            //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw4"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw5"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw6"));
        }
        else if(strcmp("4-2",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd4"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bd8"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw2"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw5"));
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw6"));
        }
        else if(strcmp("4-4",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw8"));
        }
        else if(strcmp("5-2",sortie_map)==0){
            cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw9"));
        }
    }

    if(expedition_enable){
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("D2"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("D3"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("D4"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("D9"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("D11"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("D22"));
    }

    if(pvp_enable){
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("C2"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("C3"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("C4"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("C8"));
        cJSON_AddItemToObject(quests, "", cJSON_CreateString("C16"));
    }

    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw6"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw7"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw8"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bw9"));

    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm1"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm2"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm3"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm4"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm6"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm7"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bm8"));

    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq1"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq2"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq3"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq4"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq5"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq6"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq7"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq8"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq9"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq10"));
    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("Bq11"));

    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("C29"));

    //cJSON_AddItemToObject(quests, "", cJSON_CreateString("D24"));

    cJSON_AddItemToObject(quests, "", cJSON_CreateString("E3"));
    cJSON_AddItemToObject(quests, "", cJSON_CreateString("E4"));
    
    return;
}