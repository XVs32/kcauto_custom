#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

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