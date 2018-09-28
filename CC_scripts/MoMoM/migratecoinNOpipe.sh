#!/bin/bash

# This script makes the neccesary transactions to migrate
# coin between 2 assetchains on the same -ac_cc id
waitforconfirm () {
  confirmations=0
  while [[ ${confirmations} -lt 1 ]]; do
    sleep 15
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

source=STAKEDB1
target=STAKEDW1
address="RAwx45zENMPa2p4AGnGmbrFEw6wtGoUXi6"
amount=1

# Alias for running cli
cli_target="komodo-cli -ac_name=$target"
cli_source="komodo-cli -ac_name=$source"

printbalance
echo "Sending $amount from $source to $target at $(date)"

echo "Raw tx that we will work with"
txraw=`$cli_source createrawtransaction "[]" "{\"$address\":$amount}"`
echo "$txraw txraw"
echo "Convert to an export tx"
exportData=`$cli_source migrate_converttoexport $txraw $target $amount`
echo "$exportData exportData"
exportRaw=`echo $exportData | jq -r .exportTx`
echo "$exportRaw exportRaw"
echo "Fund it"
exportFundedData=`$cli_source fundrawtransaction $exportRaw`
echo "$exportFundedData exportFundedData"
exportFundedTx=`echo $exportFundedData | jq -r .hex`
echo "$exportFundedTx exportFundedTx"
payouts=`echo $exportData | jq -r .payouts`
echo "$payouts payouts"

echo "4. Sign rawtx and export"
signedhex=`$cli_source signrawtransaction $exportFundedTx | jq -r .hex`
echo "$signedhex signedhex"
sentTX=`$cli_source sendrawtransaction $signedhex`
echo "$sentTX sentTX"

txidsize=${#sentTX}
if [[ $txidsize != "64" ]]; then
  echo "Export TX not sucessfully created"
  echo "$sentTX"
  echo "$signedhex"
  exit
fi

echo "5. Wait for a confirmation on source chain."
waitforconfirm "$sentTX" "$cli_source"
echo "[$source] : Confirmed export $sentTX"

echo " 6. Use migrate_createimporttransaction to create the import TX"
created=0
while [[ ${created} -eq 0 ]]; do
  sleep 60
  importTX=`$cli_source migrate_createimporttransaction $signedhex $payouts`
  echo "$importTX importTX"
  if [[ ${importTX} != "" ]]; then
    created=1
  fi
done
echo "importTX"
echo "Create import transaction sucessful!"

# 8. Use migrate_completeimporttransaction on KMD to complete the import tx
created=0
while [[ $created -eq 0 ]]; do
  sleep 60
  completeTX=`komodo-cli migrate_completeimporttransaction $importTX`
  echo "$completeTX completeTX"
  if [[ $completeTX != "" ]]; then
    created=1
  fi
done
echo "Sign import transaction on KMD complete!"

# 9. Broadcast tx to target chain
sent=0
tries=0
while [[ $sent -eq 0 ]]; do
  sleep 60
  sent_iTX=`$cli_target sendrawtransaction $completeTX 2> /dev/null`
  if [[ ${#sent_iTX} = "64" ]]; then
    sent=1
  elif [[ $sent_iTX != "" ]]; then
    echo "------------------------------------------------------------"
    echo "Invalid txid returned from send import transacton"
    echo "$sent_iTX"
    echo "$completeTX"
    echo "-------------------------------------------------------------"
    exit
  else
    tries=$(( $tries +1 ))
    if [[ $tries -ge 60 ]]; then
      echo "------------------------------------------------------------"
      echo "Failed Import TX on $target at $(date)"
      echo "Exiting after 90 tries: $completeTX"
      echo "From Chain: $source"
      echo "Export TX: $sentTX"
      echo "$signedhex $payouts"
      echo "------------------------------------------------------------"
      echo "$(date)   $signedhex $payouts" >> FAILED
      exit
    fi
  fi
done

waitforconfirm "$sent_iTX" "$cli_target"
echo "[$target] : Confirmed import $sent_iTX at $(date)"
printbalance

