#!/bin/bash

SESSION="kc_auto"

SESEXS=$(tmux ls | grep $SESSION)

if [ "$SESEXS" != "" ]
then
    
    tmux select-window -t kc_auto:Main
    tmux select-pane -t 0
    
    AT_HOME=$(tmux capture-pane -p | tail -n 1 | grep "marco" | wc -l)
    
    RETRY=0   
    while [ "$AT_HOME" == "0" ] && [ $RETRY -lt 60 ]
    do
        sleep 1m
        AT_HOME=$(tmux capture-pane -p | tail -n 1 | grep "marco" | wc -l)
        RETRY=$RETRY+1
    done
    
    tmux send-keys -t $SESSION:Main 'python3.7 kcauto --cli --cfg night_shift |& grep -v "scrot" ' C-m
    
fi
