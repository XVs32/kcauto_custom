#!/bin/bash

BASEDIR=$(dirname "$0")

$BASEDIR/configs/config_generator

rm $BASEDIR/click_matrix.npz

python3.7 $BASEDIR/kcauto --cli --cfg config |& grep -v "scrot"
