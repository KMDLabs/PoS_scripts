#!/bin/bash
ac=$2
chain="/home/postest/komodo/src/komodo-cli -ac_name=$ac"
block=$($chain getblock $1)
HEIGHT=$(echo $block | jq -r .height)
pbHEIGHT=$(( $HEIGHT -1 ))
pblock=$($chain getblock $pbHEIGHT)
timelb=$(( $(echo $block | jq -r .time) - $(echo $pblock | jq -r .time) ))
transactions=$(echo $block | jq .tx)
lasttx=$(( $(echo $transactions | jq length) -1 ))
bt=$($chain getblocktemplate) 
PoSperc=$(echo $bt | jq .PoSperc)
target=$(echo $bt | jq -r .target)
targetU=$(echo $target | awk '{print toupper($0)}')
dec=14134776518227074636666380005943348126619871175004951664972849610340958207
tgtdec=$(echo "ibase=16; $targetU" | bc)
diff=$(echo "$dec / $tgtdec" | bc -l)
currdiff=$(echo $block | jq -r .difficulty)

if [[ $lasttx -gt 0 ]]; then
  # possibility of PoS block
  rawtx=$($chain getrawtransaction $(echo $transactions | jq -r .[$lasttx]))
  decodedTX=$($chain decoderawtransaction $rawtx)
  voutvalue=$(echo $decodedTX | jq -r '.vout | .[0] .value')
  vinvout=$(echo $decodedTX | jq -r '.vin | .[0] | .vout')
  vinTX=$($chain getrawtransaction $(echo $decodedTX | jq -r '.vin | .[0] | .txid') 1)
  vinvalue=$(echo $vinTX | jq .vout | jq  .[$vinvout] | jq -r .value)
  stakingADDRESS=$(echo $decodedTX | jq -r '.vout | .[0] | .scriptPubKey | .addresses[0]')
  vinADDRESS=$(echo $vinTX | jq .vout | jq .[$vinvout] | jq -r ' .scriptPubKey | .addresses[0]')
  if [[ "$vinvalue" = "$voutvalue" ]] && [[ $stakingADDRESS = $vinADDRESS ]]; then
    # very high chance this is a PoS block
    blockhash=$(echo $block | jq -r .hash)
    sbh=${blockhash:0:3}
    if [[ $sbh = "000" ]]; then
       # Is probably PoW, but maybe not... has to be more accurate than before though
       value=0
       age=0
       segid="PoW"
    else
      # Very likeley PoS
      value=$(printf '%.*f\n' 0 $voutvalue)
      locktime=$(echo $decodedTX | jq -r .locktime)
      vinlocktime=$($chain getrawtransaction $(echo $decodedTX | jq -r '.vin | .[0] | .txid') 1 | jq .blocktime)
      age=$(( $locktime -$vinlocktime ))
      segid=$(komodo-cli -ac_name=$chain validateaddress $stakingADDRESS | jq -r .segid )
    fi
  else
    # is proof of work block
    value=0
    age=0
    segid="PoW"
  fi
else
  # only 1 TX so block is PoW
  value=0
  age=0
  segid="PoW"
fi

CSV="\"$HEIGHT\",\"$timelb\",\"$segid\",\"$value\",\"$age\",\"$PoSperc\",\"$currdiff\",\"$diff\""
if [[ ! -f "$HOME/webserver/data_$ac.csv" ]]; then
 echo \"Block_Height\",\"Block_Time\",\"SegID\",\"UTXO_SIZE\",\"Age\",\"PoS_%\",\"Current_Diff\",\"Target_Diff\" > ~/webserver/data_$ac.csv 
fi
echo $CSV >> ~/webserver/data_$ac.csv
echo "[$ac] $CSV"
