#!/bin/bash

call_start_up(){
    
    echo "$ENA_EXP $PRS_EXP ${EXP_ID[2-2]} ${EXP_ID[3-2]} ${EXP_ID[4-2]} $ENA_PVP $PRS_PVP $ENA_COM $SORTIE_AREA $SORTIE_LEVEL $RETREAT_POINT $COMBA_COUNT $STOP_DONE $COMBA_FLEET ${SHIP_ID[0]} ${SHIP_ID[1]} ${SHIP_ID[2]} ${SHIP_ID[3]} ${SHIP_ID[4]} ${SHIP_ID[5]}" | \
    ./start_up.sh

}

go_5_2_c(){

    SORTIE_AREA="5"
    SORTIE_LEVEL="2"
    RETREAT_POINT="C0" #retreat at C
    COMBA_FLEET="0" #custon fleet
    COMBA_COUNT=$1
    STOP_DONE="1" #stop after finish combat
    SHIP_ID=("${SHIP_5_2_C[@]}") #use fleet set for 1-6
    call_start_up

}

go_drop(){
    SORTIE_AREA="2"
    SORTIE_LEVEL="3"
    RETREAT_POINT="0" #no retreat point
    COMBA_FLEET="0" #custon fleet
    COMBA_COUNT="1"
    STOP_DONE="1" #stop after finish combat
    SHIP_ID=("${SHIP_2_3[@]}") #use fleet set for 1-6
    call_start_up
}
    
go_month(){
    SORTIE_AREA="1"
    SORTIE_LEVEL="4"
    RETREAT_POINT="0" #no retreat point
    COMBA_FLEET="0" #custon fleet
    COMBA_COUNT="1"
    STOP_DONE="1" #stop after finish combat
    SHIP_ID=("${MONTH_1_4[@]}") #use fleet set for 1-4
    call_start_up

    SORTIE_AREA="4"
    SORTIE_LEVEL="2"
    RETREAT_POINT="0" #no retreat point
    COMBA_FLEET="0" #custon fleet
    COMBA_COUNT="1"
    STOP_DONE="1" #stop after finish combat
    SHIP_ID=("${MONTH_4_2[@]}") #use fleet set for 4-2
    call_start_up

    SORTIE_AREA="5"
    SORTIE_LEVEL="1"
    RETREAT_POINT="0" #no retreat point
    COMBA_FLEET="0" #custon fleet
    COMBA_COUNT="1"
    STOP_DONE="1" #stop after finish combat
    SHIP_ID=("${MONTH_5_1[@]}") #use fleet set for 5-1
    call_start_up
}

go(){
    SORTIE_AREA="2"
    SORTIE_LEVEL="2"
    RETREAT_POINT="0" #no retreat point
    COMBA_FLEET="0" #custon fleet
    COMBA_COUNT="20"
    STOP_DONE="1" #stop after finish combat
    SHIP_ID=("${SHIP_2_2[@]}") #use fleet set for 1-6
    call_start_up
}

cd ~/coding/kcauto

echo "start of the log" > /tmp/kc_log.txt

#( python3.7 kcauto --cli --cfg do_nothing |& grep --line-buffered " / Ammo:" >> /tmp/kc_log.txt )&
( python3.7 kcauto --cli --cfg do_nothing >> /tmp/kc_log.txt )&
READER_PID=$!

DD=(11 11 11 11 11) #Teruzuki Fubuki Ayanami Murakumo Yudachi
ASDD=(11) #Jervis
CL=(11 11 11) #Yubari L.d.S.D Honolulu
ASCL=(11) #Isuzu
CA=(11) #Maya
FBB=(11 11) #Conte Haruna
BB=(11 11 11) #Yamato Ise Hiyuuga
CLT=(11 11 11) #OOi Kitakami Kiso
CV=(11 11) #Zuikaku Shokaku
CVL=(11) #Ryujo
CVA=(11 11 11) #Chitose Chiyoda junyo   #Zero fighter CV
AV=(11) #Mizuho
SS=(11 11 11 11 11 11) #I504 U-511kai I401kai I203kai I47kai I58kai

SHIP_1_6=(${DD[0]} ${DD[1]} ${DD[2]} ${DD[3]} ${ASDD[0]} ${ASCL[0]}) 
SHIP_2_1=(${SS[0]} ${SS[1]} ${SS[2]} ${SS[3]} ${SS[4]} ${SS[5]})
SHIP_2_2=(${SS[0]} ${CVA[0]} ${CVA[1]} ${CVA[2]} ${CLT[0]} ${AV[0]})
SHIP_2_3=(${SS[5]} ${CV[0]} ${CVL[0]} ${CLT[0]} ${CLT[1]} ${CLT[2]})
SHIP_2_5=(${DD[0]} ${CV[0]} ${CVL[0]} ${CL[0]} ${DD[1]} ${DD[2]})
SHIP_3_3=(${DD[0]} ${CV[0]} ${CVL[0]} ${CL[0]} ${DD[1]} ${CLT[0]})
SHIP_3_5=(${DD[0]} ${DD[1]} ${DD[2]} ${DD[3]} ${DD[4]} ${CL[0]}) 
SHIP_4_4=(${DD[0]} ${DD[1]} ${FBB[0]} ${CA[0]} ${CV[0]} ${CVL[0]}) 
SHIP_5_2=(${DD[0]} ${DD[1]} ${FBB[0]} ${FBB[1]} ${CV[0]} ${CV[1]}) 
SHIP_5_2_C=(129 ${SS[0]} ${SS[1]} ${SS[2]} ${SS[3]} ${SS[4]}) #Suzuya


MONTH_1_2=(${CL[0]} ${CL[1]} ${DD[0]} ${DD[1]} ${DD[2]} ${DD[3]}) #month quest 
MONTH_1_4=(${CL[0]} ${CL[1]} ${DD[0]} ${DD[1]} ${DD[2]} ${DD[3]}) #month quest 
MONTH_4_2=(${DD[0]} ${DD[1]} ${DD[2]} ${CL[0]} ${CV[0]} ${CV[1]}) #month quest
MONTH_5_1=(${DD[0]} ${DD[1]} ${BB[0]} ${BB[1]} ${BB[2]} ${CL[0]}) #month quest 


while true
do 
    RESEXS=$(grep " / Ammo:" /tmp/kc_log.txt)
    if [ "$RESEXS" != "" ]
    then
        
        echo "get"
        kill $READER_PID
        
        FUEL=$(grep -oP 'Fuel:\s*\K\d+' /tmp/kc_log.txt)
        AMMO=$(grep -oP 'Ammo:\s*\K\d+' /tmp/kc_log.txt)
        STEEL=$(grep -oP 'Steel:\s*\K\d+' /tmp/kc_log.txt)
        BAUXITE=$(grep -oP 'Bauxite:\s*\K\d+' /tmp/kc_log.txt)

        EXP_ID=("0" "0" "0")
        ID_BIAS=2

        if [ $BAUXITE -gt $FUEL ]
        then 
            #Marine escort mission
            #For Fuel
            EXP_ID[2-$ID_BIAS]="2"
        else
            #Air defense shooting
            #For BAUXITE
            EXP_ID[2-$ID_BIAS]="3"
        fi
        
        if [ $STEEL -gt 20000 ]
        then 
            if [ $AMMO -gt $FUEL ]
            then
                #Northern Tokyo
                #For Fuel and Ammo
                EXP_ID[3-$ID_BIAS]="6"
            else
                # Long-distance practice sailing
                # For Ammo
                EXP_ID[3-$ID_BIAS]="0"
            fi

        else
            #Tokyo express 1
            #For Ammo and Steel
            EXP_ID[3-$ID_BIAS]="8"
        fi
	
	TWO_AMMO=$AMMO*2
        if [ $STEEL -gt 20000 ] && [ $FUEL -gt $TWO_AMMO ]
        then 
            #Tokyo express 1
            #For Ammo
            EXP_ID[4-$ID_BIAS]="8"
        else
            #Tokyo express 2
            #For Fuel
            EXP_ID[4-$ID_BIAS]="9"
        fi

        ENA_EXP="1"
        PRS_EXP="0"
        ENA_PVP="1"
        PRS_PVP="3"
        ENA_COM="1"

go #do the month quest
exit 0

        DOW=$(date +%u)
        if [ $DOW -eq 1 ]
        then

            go_5_2_c 13
            go_drop
        
            SORTIE_AREA="3"
            SORTIE_LEVEL="5"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="1"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_3_5[@]}") #use fleet set for 3_5
            call_start_up
            
            SORTIE_AREA="1"
            SORTIE_LEVEL="5"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="2" #use fleet 2 
            COMBA_COUNT="5"
            STOP_DONE="1" #stop after finish combat
            echo "$ENA_EXP $PRS_EXP ${EXP_ID[2-2]} ${EXP_ID[3-2]} ${EXP_ID[4-2]} $ENA_PVP $PRS_PVP $ENA_COM $SORTIE_AREA $SORTIE_LEVEL $RETREAT_POINT $COMBA_COUNT $STOP_DONE $COMBA_FLEET" | \
                 ./start_up.sh
            
        elif [ $DOW -eq 2 ]
        then
       
            go_5_2_c 9 
            go_drop
            
            SORTIE_AREA="2"
            SORTIE_LEVEL="2"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="10"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_2_2[@]}") #use fleet set for 2_2 
            call_start_up

        elif [ $DOW -eq 3 ]
        then

            go_5_2_c 4
            go_drop
            
            SORTIE_AREA="2"
            SORTIE_LEVEL="1"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="10"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_2_1[@]}") #use fleet set for 1-6
            call_start_up
            
            SORTIE_AREA="1"
            SORTIE_LEVEL="5"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="2" #use fleet 2 
            COMBA_COUNT="4"
            STOP_DONE="1" #stop after finish combat
            echo "$ENA_EXP $PRS_EXP ${EXP_ID[2-2]} ${EXP_ID[3-2]} ${EXP_ID[4-2]} $ENA_PVP $PRS_PVP $ENA_COM $SORTIE_AREA $SORTIE_LEVEL $RETREAT_POINT $COMBA_COUNT $STOP_DONE $COMBA_FLEET" | \
                 ./start_up.sh
                 
            SORTIE_AREA="1"
            SORTIE_LEVEL="6"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="1"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_1_6[@]}") #use fleet set for 1-6
            call_start_up

        elif [ $DOW -eq 4 ]
        then
            
            go_5_2_c 9
            go_drop 

            SORTIE_AREA="3"
            SORTIE_LEVEL="3"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="10"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_3_3[@]}") #use fleet set for 3_3
            call_start_up
            
        elif [ $DOW -eq 5 ]
        then

            go_5_2_c 4
            go_drop

            SORTIE_AREA="2"
            SORTIE_LEVEL="2"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="15"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_2_2[@]}") #use fleet set for 2_2 
            call_start_up

        elif [ $DOW -eq 6 ]
        then

            go_5_2_c 4    
            go_drop

            SORTIE_AREA="2"
            SORTIE_LEVEL="2"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="0" #custon fleet
            COMBA_COUNT="15"
            STOP_DONE="1" #stop after finish combat
            SHIP_ID=("${SHIP_2_2[@]}") #use fleet set for 2_2 
            call_start_up

        else

            go_5_2_c 14    
            go_drop
            
            SORTIE_AREA="1"
            SORTIE_LEVEL="5"
            RETREAT_POINT="0" #no retreat point
            COMBA_FLEET="2" #use fleet 2 
            COMBA_COUNT="5"
            STOP_DONE="1" #stop after finish combat
            echo "$ENA_EXP $PRS_EXP ${EXP_ID[2-2]} ${EXP_ID[3-2]} ${EXP_ID[4-2]} $ENA_PVP $PRS_PVP $ENA_COM $SORTIE_AREA $SORTIE_LEVEL $RETREAT_POINT $COMBA_COUNT $STOP_DONE $COMBA_FLEET" | \
                 ./start_up.sh

        fi
        
        ENA_COM="0"
        echo "$ENA_EXP $PRS_EXP ${EXP_ID[2-2]} ${EXP_ID[3-2]} ${EXP_ID[4-2]} $ENA_PVP $PRS_PVP $ENA_COM" | \
             ./start_up.sh
        
        exit 1
    else
        sleep 1
    fi
done




