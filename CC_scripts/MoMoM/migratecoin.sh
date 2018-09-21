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

ac_json=$(curl https://raw.githubusercontent.com/StakedChain/StakedNotary/master/assetchains.json 2>/dev/null)
#source=$(echo $ac_json | jq -r '.[1].ac_name')
#target=$(echo $ac_json | jq -r '.[0].ac_name')
source="STAKEDB1"
target="STAKEDPERC"

# Alias for running cli
cli_target="komodo-cli -ac_name=$target"
cli_source="komodo-cli -ac_name=$source"
amount=5

addresses=$($(echo komodo-cli -ac_name=$target listaddressgroupings))
#for row in $(echo "${addresses}" | jq -c -r '.[][]'); do
 #       _jq() {
  #              echo ${row} | jq -r ${1}
   #     }
    #    address=$(_jq '.[0]')
address="RR69169b1DAyGkFZPaHk1iu4c6ufAnDqye"

  printbalance
  echo "Sending $amount from $source to $target $address at $(date)"

  # Raw tx that we will work with
  txraw=`$cli_source createrawtransaction "[]" "{\"$address\":$amount}"`
  # Convert to an export tx
  exportData=`$cli_source migrate_converttoexport $txraw $target $amount`
  exportRaw=`echo $exportData | jq -r .exportTx`
  # Fund it
  exportFundedData=`$cli_source fundrawtransaction $exportRaw`
  exportFundedTx=`echo $exportFundedData | jq -r .hex`
  payouts=`echo $exportData | jq -r .payouts`

  # 4. Sign rawtx and export
  signedhex=`$cli_source signrawtransaction $exportFundedTx | jq -r .hex`
  sentTX=`$cli_source sendrawtransaction $signedhex`

  # 5. Wait for a confirmation on source chain.
  waitforconfirm "$sentTX" "$cli_source"
  echo "[$source] : Confirmed export $sentTX at $(date)"
  echo "$cli_source migrate_createimporttransaction $signedhex $payouts"

  # 6. Use migrate_createimporttransaction to create the import TX
  created=0
  while [[ ${created} -eq 0 ]]; do
    importTX=`$cli_source migrate_createimporttransaction $signedhex $payouts 2> /dev/null`
    if [[ ${importTX} != "" ]]; then
      created=1
    fi
    sleep 60
  done
  echo "Create import transaction sucessful at $(date)!"
  echo "komodo-cli migrate_completeimporttransaction $importTX"

  # 8. Use migrate_completeimporttransaction on KMD to complete the import tx
  created=0
  while [[ $created -eq 0 ]]; do
    completeTX=`komodo-cli migrate_completeimporttransaction $importTX 2> /dev/null`
    if [[ $completeTX != "" ]]; then
      created=1
    fi
    sleep 60
  done
  echo "Sign import transaction on KMD complete at $(date)!"
  echo "$cli_target sendrawtransaction $completeTX"

  # 9. Broadcast tx to target chain
  sent=0
  while [[ $sent -eq 0 ]]; do
    sent_iTX=`$cli_target sendrawtransaction $completeTX 2> /dev/null`
    if [[ $sent_iTX != "" ]]; then
      sent=1
    fi
    sleep 60
  done

  waitforconfirm "$sent_iTX" "$cli_target"
  echo "[$target] : Confirmed import $sent_iTX at $(date)"
  printbalance
#done
