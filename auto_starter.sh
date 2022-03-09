#!/bin/bash
##############
#start kcauto#
##############


init(){
    rm $BASEDIR/click_matrix.npz

    BASEDIR=$(dirname "$0")

    WEEKDAY=$(date +%u)
    echo $WEEKDAY

    $PVP=3
    $STOP=1
    $PRESET=0
}

get_resources(){
    python3.7 $BASEDIR/kcauto --cli --cfg do_nothing >$BASEDIR/temp.txt &
    PID=$!
    tail -f $BASEDIR/temp.txt | grep -m 1 "Fuel"
    kill -9 $PID

    RESOURCE=$(cat temp.txt|& awk '/Fuel/ {print $3,$8,$13,$18}')

    FUEL=$(echo $RESOURCE | awk -F":| " '{print $2}')
    AMMO=$(echo $RESOURCE | awk -F":| " '{print $4}')
    STEEL=$(echo $RESOURCE | awk -F":| " '{print $6}')
    BAUXITE=$(echo $RESOURCE | awk -F":| " '{print $8}')
    
    echo $FUEL
    echo $AMMO
    echo $STEEL
    echo $BAUXITE
}

start_up(){
    echo ${EXP[0]} ${EXP[1]} ${EXP[2]} $PVP $1 $2 $3 $STOP $PRESET | $BASEDIR/start_up.sh
}

5_2_C(){
    echo ${EXP[0]} ${EXP[1]} ${EXP[2]} $PVP 8 9 $1 1 3 | $BASEDIR/start_up.sh
}

init

get_resources

if [ "$BAUXITE" -lt "$FUEL" ] && [ "$BAUXITE" -lt "$AMMO" ]
then
    EXP[0]=4 #Air defence for BAUXITE
elif [ "$FUEL" -lt "$AMMO" ]
then 
    EXP[0]=3 #Marine escort for FUEL
else
    EXP[0]=1 #Long-distance for AMMO
fi

if [ "$STEEL" -lt "$FUEL" ] || [ "$STEEL" -lt "$AMMO" ]
then
    EXP[1]=7 #Tokyu Express 1 for STEEL
    EXP[2]=8 #Tokyu Express 2 for STEEL
else
    EXP[1]=6 #Northern Express for FUEL and AMMO
    if [ "$FUEL" -lt "$AMMO" ]
    then
        EXP[2]=8 #Tokyu Express 2 for STEEL
    else
        EXP[2]=7 #Tokyu Express 1 for STEEL
    fi
fi

    echo ${EXP[0]}
    echo ${EXP[1]}
    echo ${EXP[2]}

STOP=1
PVP=3

case $WEEKDAY in
    1)
        5_2_C 2

    ;;
    2)
    ;;
    3)
    ;;
    4)
    ;;
    5)
    ;;
    6)
    ;;
    *)
    ;;



