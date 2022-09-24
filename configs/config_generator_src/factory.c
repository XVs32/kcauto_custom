#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

void factory(cJSON *root, int enable){

    cJSON_AddBoolToObject(root, "factory.enabled", enable);

    cJSON *develop_recipe = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "factory.develop_recipe", develop_recipe);
    cJSON_AddItemToObject(develop_recipe, "", cJSON_CreateNumber(10));
    cJSON_AddItemToObject(develop_recipe, "", cJSON_CreateNumber(10));
    cJSON_AddItemToObject(develop_recipe, "", cJSON_CreateNumber(10));
    cJSON_AddItemToObject(develop_recipe, "", cJSON_CreateNumber(10));

    cJSON *build_recipe = cJSON_CreateArray();
    cJSON_AddItemToObject(root, "factory.build_recipe", build_recipe);
    cJSON_AddItemToObject(build_recipe, "", cJSON_CreateNumber(30));
    cJSON_AddItemToObject(build_recipe, "", cJSON_CreateNumber(30));
    cJSON_AddItemToObject(build_recipe, "", cJSON_CreateNumber(30));
    cJSON_AddItemToObject(build_recipe, "", cJSON_CreateNumber(30));

    return; 
}

