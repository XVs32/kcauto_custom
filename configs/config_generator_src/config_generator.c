#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"
#include "scheduler.h"
#include "quest.h"
#include "ship_switch.h"
#include "expedition.h"
#include "pvp.h"
#include "combat.h"
#include "factory.h"

char BASE_PATH[500];

void init(cJSON *root){

    
    cJSON_AddNumberToObject(root, "general.jst_offset", 0);
    cJSON_AddStringToObject(root, "general.interaction_mode", "direct_control");
    cJSON_AddNumberToObject(root, "general.chrome_dev_port", 9222);
    cJSON_AddBoolToObject(root, "general.paused", 0);
    
    cJSON_AddBoolToObject(root, "passive_repair.enabled", 1);
    cJSON_AddNumberToObject(root, "passive_repair.repair_threshold", 1);
    //cJSON_AddNumberToObject(root, "passive_repair.slots_to_reserve", 1);
    
    cJSON_AddBoolToObject(root, "event_reset.enabled", 1);
    cJSON_AddNumberToObject(root, "event_reset.frequency", 3);
    cJSON_AddNumberToObject(root, "event_reset.reset_difficulty", 3);
    cJSON_AddNumberToObject(root, "event_reset.farm_difficulty", 2);

    return;
}

int option_to_expdst(int input){
    switch(input){
        case 1:
            return 2;
        case 2:
            return 3;
        case 3:
            return 5;
        case 4:
            return 6;
        case 5:
            return 11;
        case 6:
            return 21;
        case 7:
            return 37;
        case 8:
            return 38;
        default:
            return 0;
    }
}

int main(int argc, const char * argv[]) {

    int expedition_enable=0, pvp_enable=0, combat_enable=0;
    
    cJSON *root = cJSON_CreateObject(); //workspace_config

    init(root);

    strcpy(BASE_PATH, argv[0]);
    int i;
    int len = strlen(BASE_PATH);
    for(i=len-1;i>=0;i--){
        if(BASE_PATH[i]=='/'){
            BASE_PATH[i+1] = '\0';
            break;
        }
    }


    /////////////////////////start factory/////////////////////////////////////
    int factory_enable = 0;
    printf("Fleet #%d auto factory?\n",i+2);
    printf("0 -- Disable\n");
    printf("1 -- Enable\n");
    scanf("%d",&factory_enable);
    factory(root, factory_enable);
    /////////////////////////end factory/////////////////////////////////////
    /////////////////////////start expedition/////////////////////////////////////
    
    int fleet_dst[5];
    for(i=0;i<3;i++){
        printf("Fleet #%d expedition destination?\n",i+2);
        printf("0 -- Disable\n");
        printf("1 -- Long-distance practice sailing\n");
        printf("2 -- Guard task\n");
        printf("3 -- Marine escort mission\n");
        printf("4 -- Air defense shooting exercises\n");
        printf("5 -- Bauxite transport mission\n");
        printf("6 -- Northern Tokyo Express Operation\n");
        printf("7 -- Tokyu Express\n");
        printf("8 -- Tokyo Express (2)\n");

        scanf("%d",&fleet_dst[i]);
        fleet_dst[i] = option_to_expdst(fleet_dst[i]);
    }
    
    expedition(root, fleet_dst);

    /////////////////////////end expedition/////////////////////////////////////
    /////////////////////////start pvp//////////////////////////////////////////
    

    int pvp_preset;
    printf("pvp?\n");
    printf("0 -- Disable \n");
    printf("1 -- Use fleet_preset 1\n");
    printf("2 -- Use fleet_preset 2\n");
    printf("3 -- Use fleet_preset 3\n");
    printf("4 -- Use current fleet \n");
    scanf("%d",&pvp_preset);

    pvp(root, pvp_preset);

    /////////////////////////end pvp/////////////////////////////////////
    /////////////////////////start combat//////////////////////////////////////////
    
    int sortie_count;
    int stop_after_combat;
    int sortie_preset;
    int sortie_area=1,sortie_level=1;
    char retreat_pt[100] = "0";

    cJSON_AddNumberToObject(root, "passive_repair.slots_to_reserve", 2);//reserve 2 slots for combat
        
    printf("Sortie area?\n");
    printf("0 -- Disable sortie\n");
    printf("1 -- Naval Base Area\n");
    printf("2 -- Southwestern island Area\n");
    printf("3 -- Northern Area\n");
    printf("4 -- Western Area\n");
    printf("5 -- Southern Area\n");
    printf("6 -- Central Area\n");
    printf("7 -- Southwestern Area\n");
    printf("8 -- Monthly quest preset\n");
    printf("9 -- Quarterly quest preset\n");
    scanf("%d",&sortie_area);

    if(sortie_area<8){
        printf("Sortie level?\n");
    }
    else if(sortie_area == 8){
        printf("0 -- Bm4-5-1\n");
        printf("1 -- Bm6-4-2\n");
        printf("2 -- Bm7-2-5\n");
        printf("3 -- Bm8-1-2\n");
        printf("4 -- Bm8-1-3\n");
        printf("5 -- Bm3/Bm8-1-4\n");
        printf("6 -- Bm8-2-1\n");
        printf("7 -- 2-2-A\n");
        printf("8 -- 5-2-C\n");
    }
    else if(sortie_area == 9){
        printf("0 -- Bq3-1-6\n");
        printf("1 -- Bq4-6-3\n");
        printf("2 -- Bq5-3-1\n");
        printf("3 -- Bq5-3-2//notworking yet\n");
        printf("4 -- Bq5-3-3\n");
        printf("5 -- Bq9-1-3\n");
        printf("6 -- Bq9/Bq11-1-4\n");
        printf("7 -- Bq9/Bq11-2-1\n");
        printf("8 -- Bq9/Bq11-2-2\n");
        printf("9 -- Bq9/Bq11-2-3\n");
    }

    scanf("%d",&sortie_level);
        
    printf("How many runs of sortie?\n");
    scanf("%d",&sortie_count);

    printf("Stop kc-auto after finish sortie?\n");
    printf("0 -- NO\n");
    printf("1 -- YES\n");
    scanf("%d",&stop_after_combat);

    printf("Combat fleet?\n");
    printf("0 -- use custom fleet\n");
    printf("1 -- use fleet_preset 1\n");
    printf("2 -- use fleet_preset 2\n");
    printf("3 -- use fleet_preset 3\n");
    printf("4 -- Use current fleet \n");
    scanf("%d",&sortie_preset);
    
    char comdst[5];
    sprintf(comdst,"%d-%d",sortie_area, sortie_level);
    
    printf("test:%s\n",comdst);
    combat(root, sortie_preset, comdst);

    
    /////////////////////////end combat/////////////////////////////////////
    /////////////////////////start ship switch//////////////////////////////////////////

    if(sortie_area == 0){
        cJSON_AddNumberToObject(root, "passive_repair.slots_to_reserve", 0);//reserve 0 slot for combat
        akashi_repair(root);
    }
    else if(sortie_preset!=0){
        ship_switch(root, "0-0");//disable ship switch
    }
    else if(sortie_preset==0){
        ship_switch(root, comdst);
    }
    /////////////////////////end ship switch//////////////////////////////////////////


    scheduler(root, sortie_count,stop_after_combat);

    quest(root, fleet_dst, pvp_preset, comdst);

    char *string = cJSON_Print(root);
    if (string == NULL){
        fprintf(stderr, "Failed to print monitor.\n");
    }
    cJSON_Delete(root);
    
    FILE *json_file;
    char file_path[500];

    strcpy(file_path, BASE_PATH);
    strcat(file_path, "config.json");
    json_file = fopen(file_path,"w");
    fprintf(json_file, "%s", string);
    fclose(json_file);
    
    return 0;
}
