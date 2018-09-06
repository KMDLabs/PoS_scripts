#!/bin/bash
for i in `seq 1 100`; do
  ./migratecoin.sh
  sleep 30
done
