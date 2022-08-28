#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"


void combat(cJSON *root, int fleet_preset, char* sortie_map){

    char buf[50];
    int i;

    if(sortie_map[0] == '0'){
        cJSON_AddBoolToObject(root, "combat.enabled", 0);
        cJSON_AddStringToObject(root, "combat.sortie_map", "1-1");
    }
    else if(sortie_map[0] == '8'){
        cJSON_AddBoolToObject(root, "combat.enabled", 1);
        switch(sortie_map[2]){
            case '0':
                cJSON_AddStringToObject(root, "combat.sortie_map", "5-1");
                break;
            case '1':
                cJSON_AddStringToObject(root, "combat.sortie_map", "4-2");
                break;
            case '2':
                cJSON_AddStringToObject(root, "combat.sortie_map", "2-5");
                break;
            case '3':
                cJSON_AddStringToObject(root, "combat.sortie_map", "1-2");
                break;
            case '4':
                cJSON_AddStringToObject(root, "combat.sortie_map", "1-3");
                break;
            case '5':
                cJSON_AddStringToObject(root, "combat.sortie_map", "1-4");
                break;
            case '6':
                cJSON_AddStringToObject(root, "combat.sortie_map", "2-1");
                break;
            case '7':
                cJSON_AddStringToObject(root, "combat.sortie_map", "2-2");
                break;
            case '8':
                cJSON_AddStringToObject(root, "combat.sortie_map", "5-2");
                break;
            case '9':
                //cJSON_AddStringToObject(root, "combat.sortie_map", "5-2");
                break;
        }
    }
    else if(sortie_map[0] == '9'){
        cJSON_AddBoolToObject(root, "combat.enabled", 1);
        switch(sortie_map[2]){
            case '0':
                cJSON_AddStringToObject(root, "combat.sortie_map", "1-6");
                break;
            case '1':
                cJSON_AddStringToObject(root, "combat.sortie_map", "6-3");
                break;
            case '2':
                cJSON_AddStringToObject(root, "combat.sortie_map", "3-1");
                break;
            case '3':
                cJSON_AddStringToObject(root, "combat.sortie_map", "3-2");
                break;
            case '4':
                cJSON_AddStringToObject(root, "combat.sortie_map", "3-3");
                break;
            case '5':
                cJSON_AddStringToObject(root, "combat.sortie_map", "1-3");
                break;
            case '6':
                cJSON_AddStringToObject(root, "combat.sortie_map", "1-4");
                break;
            case '7':
                cJSON_AddStringToObject(root, "combat.sortie_map", "2-1");
                break;
            case '8':
                cJSON_AddStringToObject(root, "combat.sortie_map", "2-2");
                break;
            case '9':
                cJSON_AddStringToObject(root, "combat.sortie_map", "2-3");
                break;
        }

    }
    else{
        cJSON_AddBoolToObject(root, "combat.enabled", 1);
        cJSON_AddStringToObject(root, "combat.sortie_map", sortie_map);


    }


    cJSON_AddStringToObject(root, "combat.fleet_mode", "standard");

    cJSON *select_point = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_selects", select_point);
    if(strcmp("6-3", sortie_map) == 0){
        cJSON_AddStringToObject(select_point, "", "A>C");
    }
    else if(strcmp("4-5", sortie_map) == 0){
        cJSON_AddStringToObject(select_point, "", "A>D");
        cJSON_AddStringToObject(select_point, "", "C>D");
    }
        
    cJSON *retreat_points = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.retreat_points", retreat_points);

    if(strcmp(sortie_map,"8-8") == 0){//5-2-C
        cJSON_AddStringToObject(retreat_points, "", "C");
    }

    cJSON_AddItemToObject(root, "combat.push_nodes", cJSON_CreateArray());

    cJSON *node_formations = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_formations", node_formations);
    
    cJSON *node_night_battles = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.node_night_battles", node_night_battles);

    cJSON_AddNumberToObject(root, "combat.retreat_limit", 4);

    cJSON_AddNumberToObject(root, "combat.repair_limit", 3);
    cJSON_AddNumberToObject(root, "combat.repair_timelimit_hours", 1);
    cJSON_AddNumberToObject(root, "combat.repair_timelimit_minutes", 0);
    
    if(strcmp(sortie_map,"8-8")==0){//5-2-C
        cJSON_AddBoolToObject(root, "combat.check_fatigue", 0);
    }
    else{
        cJSON_AddBoolToObject(root, "combat.check_fatigue", 1);
    }

    cJSON_AddItemToObject(root, "combat.lbas_groups", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "combat.lbas_group_1_nodes", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "combat.lbas_group_2_nodes", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "combat.lbas_group_3_nodes", cJSON_CreateArray());
    cJSON_AddBoolToObject(root, "combat.check_lbas_fatigue", 0);
    cJSON_AddBoolToObject(root, "combat.port_check", 0);
    cJSON_AddBoolToObject(root, "combat.clear_stop", 0);
    
    cJSON_AddBoolToObject(root, "combat.reserve_repair_dock", 0);

    cJSON *combat_fleet = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "combat.fleet_presets", combat_fleet);
    if(fleet_preset > 0 && fleet_preset < 4){//use preset, no ship switch
        cJSON_AddItemToObject(combat_fleet, "", cJSON_CreateNumber(fleet_preset));
    }

    return;
}
