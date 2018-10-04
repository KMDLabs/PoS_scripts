#!/bin/bash
set -eo pipefail
delay=3

$HOME/komodo/src/listassetchainparams | while read args; do
  ac=$(echo $args | grep -o 'ac_name=[^ ,]\+')
  ac=$(echo "${ac#*=}")
  blocknotify="-blocknotify=$HOME/PoS_scripts/STAKED_control/blocknotify.sh %s $ac"
  $HOME/komodo/src/komodod "$blocknotify" $args &
  sleep $delay
done
