mkfile_path := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

all:
	echo $(mkfile_path)
	gcc cJSON.c config_generator.c -o $(mkfile_path)/../config_generator

clean:
	rm  $(mkfile_path)/../config_generator

