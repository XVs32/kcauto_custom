#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

#define MIN(a,b) (((a)<(b))?(a):(b))
#define MAX(a,b) (((a)>(b))?(a):(b))

void pvp(cJSON *root, int fleet_preset){

    cJSON_AddBoolToObject(root, "pvp.enabled", MIN(1,fleet_preset));

    if(fleet_preset == 4){
        cJSON_AddNullToObject(root, "pvp.fleet_preset"); 
    }
    else{
        cJSON_AddNumberToObject(root, "pvp.fleet_preset", fleet_preset);
    }

    return;
}
