#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void pvp(cJSON *root, int enable, int fleet_preset){

    cJSON_AddBoolToObject(root, "pvp.enabled", enable);
    cJSON_AddNumberToObject(root, "pvp.fleet_preset", fleet_preset);

    return;
}