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
        case 0:
            return 2;
        case 1:
            return 3;
        case 2:
            return 5;
        case 3:
            return 6;
        case 4:
            return 11;
        case 5:
            return 12;
        case 6:
            return 21;
        case 7:
            return 24;
        case 8:
            return 37;
        case 9:
            return 38;
        default:
            return 0;
    }
}

int option_to_comdst(int input){
    switch(input){
        case 0:
            return 15;
        case 1:
            return 21;
        case 2:
            return 22;
        case 3:
            return 33;
        case 4:
            return 41;
        case 5:
            return 52;
        default:
            return 0;
    }
}

int main(int argc, const char * argv[]) {

    int expedition_enable=0, pvp_enable=0, combat_enable=0;
    
    cJSON *root = cJSON_CreateObject(); //workspace_config

    init(root);

    /////////////////////////start expedition/////////////////////////////////////
    
    printf("Enable expedition?\n");
    printf("0 -- NO\n");
    printf("1 -- YES\n");
    scanf("%d",&expedition_enable);

    int mode = 0;
    int fleet_dst[5];
    if(expedition_enable == 1){
        printf("Use preset?\n");
        printf("0 -- NO\n");
        printf("1 -- YES\n");
        
        int preset_enable;
        scanf("%d",&preset_enable);
        
        if(preset_enable == 1){
            printf("Expedition mode?\n");
            printf("0 -- optimal\n");
            printf("1 -- fuel\n");
            printf("2 -- ammo\n");
            printf("3 -- steel\n");
            printf("4 -- balance\n");
            printf("5 -- night\n");
            scanf("%d",&mode);
            expedition_set(fleet_dst, mode);
        }
        else{
            int i;
            for(i=0;i<3;i++){
                printf("Fleet #%d expedition destination?\n",i+2);
                printf("0 -- Long-distance practice sailing\n");
                printf("1 -- Guard task\n");
                printf("2 -- Marine escort mission\n");
                printf("3 -- Air defense shooting exercises\n");
                printf("4 -- Bauxite transport mission\n");
                printf("5 -- Resource transportation mission\n");
                printf("6 -- Northern Tokyo Express Operation\n");
                printf("7 -- Northern Sea Route Maritime Escort\n");
                printf("8 -- Tokyu Express\n");
                printf("9 -- Tokyo Express (2)\n");
                scanf("%d",&fleet_dst[i]);
                fleet_dst[i] = option_to_expdst(fleet_dst[i]);
            }
        }
    }
    expedition(root, expedition_enable, fleet_dst);

    /////////////////////////end expedition/////////////////////////////////////
    /////////////////////////start pvp//////////////////////////////////////////
    
    printf("Enable pvp?\n");
    printf("0 -- NO\n");
    printf("1 -- YES\n");
    scanf("%d",&pvp_enable);

    int preset = 1;
    if(pvp_enable == 1){
        printf("pvp fleet?\n");
        printf("1 -- use fleet_preset 1\n");
        printf("2 -- use fleet_preset 2\n");
        printf("3 -- use fleet_preset 3\n");
        scanf("%d",&preset);
    }
    
    pvp(root, pvp_enable, preset);

    /////////////////////////end pvp/////////////////////////////////////
    /////////////////////////start combat//////////////////////////////////////////
    
    printf("Enable combat?\n");
    printf("0 -- NO\n");
    printf("1 -- YES\n");
    scanf("%d",&combat_enable);

    int sortie_count;
    int stop_after_combat;
    preset = 1;
    int sortie_area=1,sortie_level=1;
    char retreat_pt[100] = "0";
    if(combat_enable == 1){
        cJSON_AddNumberToObject(root, "passive_repair.slots_to_reserve", 2);//reserve 2 slots for combat
        
        printf("Sortie area?\n");
        scanf("%d",&sortie_area);
        printf("Sortie level?\n");
        scanf("%d",&sortie_level);
        
        printf("Where to retreat sortie? Enter 0 for eof.\n");
        int i=0;
        
        do{
            scanf("%c",retreat_pt+i);
            if(retreat_pt[i]>='a'&&retreat_pt[i]<='z'){
                retreat_pt[i] -= ('a' - 'A'); //to uppercase
            }
            if(retreat_pt[i]<'0'||(retreat_pt[i]>'9'&&retreat_pt[i]<'A')||retreat_pt[i]>'Z'){
                printf("Please input alphanumeric.\n");
                continue;
            }
            i++;
        }while(retreat_pt[i-1]!='0');

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
        scanf("%d",&preset);
        
        /////////////////////////start ship switch//////////////////////////////////////////
        int *id;
        id = malloc(sizeof(int)*10);
        if(preset==0){
            int i;
            for(i=0;i<6;i++){
                printf("#%d ship id?\n",i+1);
                scanf("%d",&id[i]);
            }
        }
        else{
            id = NULL;
        }
        ship_switch(root, id);
        free(id);
        /////////////////////////end ship switch//////////////////////////////////////////
        
    }
    else{
        cJSON_AddNumberToObject(root, "passive_repair.slots_to_reserve", 0);//reserve 0 slot for combat
        akashi_repair(root);
    }
    char comdst[5];
    sprintf(comdst,"%d-%d",sortie_area, sortie_level);
    combat(root, combat_enable, preset, retreat_pt, comdst);
    
    /////////////////////////end combat/////////////////////////////////////


    scheduler(root, sortie_count,stop_after_combat);

    quest(root, expedition_enable, pvp_enable, combat_enable, comdst);

    char *string = NULL;
    string = cJSON_Print(root);
    if (string == NULL){
        fprintf(stderr, "Failed to print monitor.\n");
    }
    cJSON_Delete(root);
    
    FILE *json_file;
    char file_path[500];
    strcpy(file_path, argv[0]);
    int i;
    int len = strlen(file_path);
    int last_slash=0;
    for(i=0;i<len;i++){
        if(file_path[i]=='/'){
            last_slash = i;
        }
    }
    file_path[last_slash+1] = '\0';

    strcat(file_path, "config.json");
    json_file = fopen(file_path,"w");
    fprintf(json_file, "%s", string);
    fclose(json_file);
    
    return 0;
}
