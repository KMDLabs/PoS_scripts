#!/bin/bash
for i in `seq 1 2000`; do
  ./migratecoin.sh >> logs_seq/$i &
  echo $i
  sleep 45
done
