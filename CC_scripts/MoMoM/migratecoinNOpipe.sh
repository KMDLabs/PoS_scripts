#!/bin/bash

# This script makes the neccesary transactions to migrate
# coin between 2 assetchains on the same -ac_cc id
waitforconfirm () {
  confirmations=0
  while [[ ${confirmations} -lt 1 ]]; do
    sleep 1
    confirmations=$($2 gettransaction $1 | jq -r .confirmations)
    # Keep re-broadcasting
    $2 sendrawtransaction $($2 getrawtransaction $1) > /dev/null 2>&1
  done
}

printbalance () {
  src_balance=`$cli_source getbalance`
  tgt_balance=`$cli_target getbalance`
  echo "[$source] : $src_balance"
  echo "[$target] : $tgt_balance"
}

ac_json=$(curl https://raw.githubusercontent.com/blackjok3rtt/StakedNotary/master/assetchains.json 2>/dev/null)
source=$(echo $ac_json | jq -r '.[1].ac_name')
target=$(echo $ac_json | jq -r '.[0].ac_name')
address=$(echo komodo-cli -ac_name=STAKEDBB listaddressgroupings) | jq -c -r '.[0][0][0]'
amount=1

# Alias for running cli
cli_target="komodo-cli -ac_name=$target"
cli_source="komodo-cli -ac_name=$source"

printbalance
echo "Sending $amount from $source to $target at $(date)"

echo "Raw tx that we will work with"
txraw=`$cli_source createrawtransaction "[]" "{\"$address\":$amount}"`
echo "$txraw txraw"
echo "Convert to an export tx at $(date)"
exportData=`$cli_source migrate_converttoexport $txraw $target $amount`
echo "$exportData exportData"
exportRaw=`echo $exportData | jq -r .exportTx`
echo "$exportRaw exportRaw"
echo "Fund it at $(date)"
exportFundedData=`$cli_source fundrawtransaction $exportRaw`
echo "$exportFundedData exportFundedData"
exportFundedTx=`echo $exportFundedData | jq -r .hex`
echo "$exportFundedTx exportFundedTx"
payouts=`echo $exportData | jq -r .payouts`
echo "$payouts payouts"

echo "4. Sign rawtx and export at $(date)"
signedhex=`$cli_source signrawtransaction $exportFundedTx | jq -r .hex`
echo "$signedhex signedhex"
sentTX=`$cli_source sendrawtransaction $signedhex`
echo "$sentTX sentTX"

echo "5. Wait for a confirmation on source chain at $(date)"
waitforconfirm "$sentTX" "$cli_source"
echo "[$source] : Confirmed export $sentTX"

echo " 6. Use migrate_createimporttransaction to create the import TX at $(date)"
created=0
while [[ ${created} -eq 0 ]]; do
  importTX=`$cli_source migrate_createimporttransaction $signedhex $payouts`
  echo "$importTX importTX"
  if [[ ${importTX} != "" ]]; then
    created=1
  fi
  sleep 60
done
echo "importTX"
echo "Create import transaction sucessful! at $(date)"

# 8. Use migrate_completeimporttransaction on KMD to complete the import tx
created=0
while [[ $created -eq 0 ]]; do
  completeTX=`komodo-cli migrate_completeimporttransaction $importTX`
  echo "$completeTX completeTX"
  if [[ $completeTX != "" ]]; then
    created=1
  fi
  sleep 60
done
echo "Sign import transaction on KMD complete at $(date)!"

# 9. Broadcast tx to target chain
sent=0
while [[ $sent -eq 0 ]]; do
  sent_iTX=`$cli_target sendrawtransaction $completeTX`
  if [[ $sent_iTX != "" ]]; then
    sent=1
  fi
  sleep 60
done

waitforconfirm "$sent_iTX" "$cli_target"
echo "[$target] : Confirmed import $sent_iTX"
printbalance

