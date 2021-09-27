#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void combat(cJSON *root, int enable, int fleet_preset, char* retreat_list, char* sortie_map){

    char buf[50];
    int i;

    cJSON_AddBoolToObject(root, "combat.enabled", enable);

    cJSON_AddStringToObject(root, "combat.sortie_map", sortie_map);

    cJSON_AddStringToObject(root, "combat.fleet_mode", "standard");
    cJSON_AddItemToObject(root, "combat.node_selects", cJSON_CreateArray());
    cJSON *retreat_points = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.retreat_points", retreat_points);
    
    for(i=0;retreat_list[i]!='0';i++){
        char point[2] = {'\0'};
        strncpy(point, retreat_list+i, 1);
        cJSON_AddStringToObject(retreat_points, "", point);
    }

    cJSON_AddItemToObject(root, "combat.push_nodes", cJSON_CreateArray());

    cJSON *node_formations = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_formations", node_formations);
    
    cJSON *node_night_battles = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_night_battles", node_night_battles);

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