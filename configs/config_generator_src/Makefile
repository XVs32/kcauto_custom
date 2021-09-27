mkfile_path := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

all:
	gcc cJSON.c scheduler.c quest.c ship_switch.c expedition.c pvp.c combat.c config_generator.c -o $(mkfile_path)/../config_generator

clean:
	rm  $(mkfile_path)/../config_generator

