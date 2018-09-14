#!/bin/bash
# Fetch assetchains.json
wget -qO assetchains.json https://raw.githubusercontent.com/blackjok3rtt/StakedNotary/master/assetchains.json

# Start KMD
echo "[KMD] : Starting KMD"
komodod & #> /dev/null 2>&1 &

# Start assets
./assetchains

# Validate Address on KMD + AC, will poll deamon until started then check if address is imported, if not import it.
echo "[KMD] : Checking your address and importing it if required."
./listassetchains.py | while read chain; do
  # Move our auto generated coins file to the iguana coins dir
  echo "[$chain] : $(./validateaddress.sh $chain)"
done
echo "Finished"
