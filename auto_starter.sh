#!/bin/bash
##############
#start kcauto#
##############


init(){
    

    BASEDIR=$(dirname "$0")

    WEEKDAY=$(date +%u)
    echo WEEKDAY:$WEEKDAY

    DAY=$(date +%d)
    echo DAY:$DAY
    
    rm $BASEDIR/click_matrix.npz

    PVP=3
    STOP=1
    PRESET=0
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

    echo FUEL:$FUEL AMMO:$AMMO STEEL:$STEEL BAUXITE:$BAUXITE
}

start_up(){
    echo ${EXP[0]} ${EXP[1]} ${EXP[2]} $PVP $1 $2 $3 $STOP $PRESET | $BASEDIR/start_up.sh
}

5_2_C(){
    echo ${EXP[0]} ${EXP[1]} ${EXP[2]} $PVP 8 9 $1 1 3 | $BASEDIR/start_up.sh
}

drop(){
    PRESET=0
    start_up 6 3 $1 
}

night_shift(){
    python3.7 $BASEDIR/kcauto --cli --cfg night_shift
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
PRESET=0

case $WEEKDAY in
    1)
        5_2_C 2
        drop 1
        start_up 8 2 1
        start_up 8 7 2
        start_up 8 3 1
        start_up 8 4 1
        start_up 8 5 1
        start_up 8 6 1
        5_2_C 5
        start_up 2 1 5
        
        STOP=0
        start_up 0 0 0
        ;;
    2)
        drop 1
        start_up 8 1 1
        start_up 8 0 1
        5_2_C 12
        start_up 2 1 5
        
        STOP=0
        start_up 0 0 0
        ;;
    3)
        drop 1
        start_up 2 5 1
        5_2_C 8
        start_up 2 1 5
        start_up 1 5 5
        
        STOP=0
        start_up 0 0 0
        ;;
    4)
        drop 1
        start_up 3 5 1
        5_2_C 9
        start_up 3 3 9
        
        STOP=0
        start_up 0 0 0
        ;;
    5)
        drop 1
        start_up 3 5 1
        5_2_C 6
        start_up 8 7 12
        
        STOP=0
        start_up 0 0 0
        ;;
    6)
        drop 1
        5_2_C 7
        start_up 8 7 12
        
        STOP=0
        start_up 0 0 0
        ;;
    *)
        drop 1
        5_2_C 11
        start_up 8 7 5
        start_up 1 5 3
        
        STOP=0
        start_up 0 0 0
        ;;
esac
night_shift

