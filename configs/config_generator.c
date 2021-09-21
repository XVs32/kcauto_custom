#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void init(cJSON *root){
    
    cJSON_AddNumberToObject(root, "general.jst_offset", 0);
    cJSON_AddStringToObject(root, "general.interaction_mode", "direct_control");
    cJSON_AddNumberToObject(root, "general.chrome_dev_port", 9222);
    cJSON_AddBoolToObject(root, "general.paused", 0);
    
    cJSON_AddBoolToObject(root, "passive_repair.enabled", 1);
    cJSON_AddNumberToObject(root, "passive_repair.repair_threshold", 1);
    cJSON_AddNumberToObject(root, "passive_repair.slots_to_reserve", 1);
    
    cJSON_AddBoolToObject(root, "event_reset.enabled", 1);
    cJSON_AddNumberToObject(root, "event_reset.frequency", 3);
    cJSON_AddNumberToObject(root, "event_reset.reset_difficulty", 3);
    cJSON_AddNumberToObject(root, "event_reset.farm_difficulty", 2);

    return;
}

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

void ship_switch(cJSON *root, int *id){

   if(id == NULL){
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
           sprintf(slot, "%d", i+1);
           sprintf(condition, "morale:!=:0|ship:%d:>=:1:>=:0:!=:0::", id[i]);
           cJSON_AddItemToObject(spsw, slot, cJSON_CreateString(condition));
       }
   }

   return;
}

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

void pvp(cJSON *root, int enable, int fleet_preset){

    cJSON_AddBoolToObject(root, "pvp.enabled", enable);
    cJSON_AddNumberToObject(root, "pvp.fleet_preset", fleet_preset);

    return;
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


void combat(cJSON *root, int enable, int fleet_preset, char* sortie_map){

    cJSON_AddBoolToObject(root, "combat.enabled", enable);

    cJSON_AddStringToObject(root, "combat.sortie_map", sortie_map);

    cJSON_AddStringToObject(root, "combat.fleet_mode", "standard");
    cJSON_AddItemToObject(root, "combat.node_selects", cJSON_CreateArray());
    cJSON *retreat_points = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.retreat_points", retreat_points);
       /* case 52://5-2-c
            cJSON_AddItemToObject(retreat_points, "", cJSON_CreateString("C"));
            break;*/

    cJSON_AddItemToObject(root, "combat.push_nodes", cJSON_CreateArray());

    cJSON *node_formations = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_formations", node_formations);
    
    cJSON *node_night_battles = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_night_battles", node_night_battles);
    char buf[50];
    int i;
    for(i=0;i<26;i++){
        sprintf(buf,"%c:True",'A'+i);
        cJSON_AddItemToObject(node_night_battles, "", cJSON_CreateString(buf));
    }

    cJSON_AddNumberToObject(root, "combat.retreat_limit", 4);

    cJSON_AddNumberToObject(root, "combat.repair_limit", 3);
    cJSON_AddNumberToObject(root, "combat.repair_timelimit_hours", 1);
    cJSON_AddNumberToObject(root, "combat.repair_timelimit_minutes", 0);

    cJSON_AddBoolToObject(root, "combat.check_fatigue", 1);

    cJSON_AddItemToObject(root, "combat.lbas_groups", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "combat.lbas_group_1_nodes", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "combat.lbas_group_2_nodes", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "combat.lbas_group_3_nodes", cJSON_CreateArray());
    cJSON_AddBoolToObject(root, "combat.check_lbas_fatigue", 0);
    cJSON_AddBoolToObject(root, "combat.port_check", 0);
    cJSON_AddBoolToObject(root, "combat.clear_stop", 0);
    
    if(enable){
        cJSON_AddBoolToObject(root, "combat.reserve_repair_dock", 1);
    }
    else{
        cJSON_AddBoolToObject(root, "combat.reserve_repair_dock", 0);
    }

    cJSON *combat_fleet = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.fleet_presets", combat_fleet);
    if(fleet_preset!=0){//use preset, no ship switch
        cJSON_AddItemToObject(combat_fleet, "", cJSON_CreateNumber(fleet_preset));
    }


    return;
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
    if(combat_enable == 1){
        printf("Sortie area?\n");
        scanf("%d",&sortie_area);
        printf("Sortie level?\n");
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
        scanf("%d",&preset);
    }
    char comdst[5];
    sprintf(comdst,"%d-%d",sortie_area, sortie_level);
    combat(root, combat_enable, preset, comdst);
    
    /////////////////////////end combat/////////////////////////////////////
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
