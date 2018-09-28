#!/bin/bash
for i in `seq 1 10`; do
  ./migratecoin.sh >> send_loop_$1
  sleep $(( RANDOM % 90 + 30 ))
done
