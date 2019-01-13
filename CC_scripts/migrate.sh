#!/bin/bash

col_red="\e[31m"
col_green="\e[32m"
col_yellow="\e[33m"
col_blue="\e[34m"
col_magenta="\e[35m"
col_cyan="\e[36m"
col_default="\e[39m"
col_ltred="\e[91m"
col_dkgrey="\e[90m"
colors=($col_red $col_green $col_yellow $col_blue $col_magenta $col_cyan)

initTime=$SECONDS

if [[ ! -d $HOME/.komodo/migration_logs ]]; then
  mkdir $HOME/.komodo/migration_logs
fi

result_logfile="$HOME/.komodo/migration_logs/migrate_results.log"
if [[ ! -z $result_logfile ]]; then
  touch $result_logfile
fi

# This script makes the neccesary transactions to migrate
# coin between 2 assetchains on the same -ac_cc id
waitforconfirm () {
  logfile="$HOME/.komodo/migration_logs/${1}.log"
  #echo "logfile: $logfile"
  confirmations=0
  while [[ ${confirmations} -lt 1 ]]; do
    runTime=$(echo $SECONDS-$initTime|bc)
    #echo "$1 $2"
    echo "Waiting for confirmations ($runTime sec)"
    confirmations=$($2 gettransaction $1 | jq -r '.confirmations')
    # Keep re-broadcasting
    $2 getrawtransaction $1 > $logfile
    $2 sendrawtransaction $($2 getrawtransaction $1) > /dev/null 2>&1
    sleep 15
  done
}

printbalance () {
  src_balance=`$cli_source getbalance`
  tgt_balance=`$cli_target getbalance`
  echo -e "${col_cyan}[$source] : $src_balance"
  echo -e "[$target] : ${tgt_balance}${col_default}"
}

ac_json=$(cat "$HOME/StakedNotary/assetchains.json")
ac_list=();
src_balance=();
tgt_balance=();
for chain_params in $(echo "${ac_json}" | jq  -c -r '.[]'); do
  ac_name=$(echo $chain_params | jq -r '.ac_name')
  ccid=$(echo $chain_params | jq -r '.ac_cc')
  ac_list+=("$ac_name (ccid: ${ccid})")
  cli_source="komodo-cli -ac_name=$ac_name"
  src_balance=$($cli_source getbalance)
  echo -e "${col_green}$ac_name (balance: $src_balance)"
done

echo -e -n "$col_blue"
PS3="Select source asset chain: "
while [[ ${#source} < 3 ]]; do
  select ac in "${ac_list[@]}"
  do
      echo -e -n "$col_yellow"
      selected=($ac)
      source=${selected[0]}
      ccid_src=$(echo "${selected[2]}" | sed 's=(==' | sed 's=)==')
      cli_source="komodo-cli -ac_name=$source"
      src_balance=$($cli_source getbalance)
      break
  done
  echo -e -n "$col_blue"
  PS3="Select source asset chain: "
  echo -e -n "$col_yellow"
done
echo "$source selected (balance: $src_balance)"

echo -e -n "$col_blue"
PS3="Select target asset chain: "
while [[ ${#target} < 3 ]]; do
  select ac in "${ac_list[@]}"
  do
  echo -e -n "$col_yellow"
      selected=($ac)
      target=${selected[0]}
      ccid_tgt=$(echo "${selected[2]}" | sed 's=(==' | sed 's=)==')
      cli_target="komodo-cli -ac_name=$target"
      tgt_balance=$($cli_target getbalance)
      break
  done
  echo -e -n "$col_blue"
  PS3="Select source asset chain: "
  echo -e -n "$col_yellow"
done
echo "$target selected (balance: $tgt_balance)"

if [[ "$ccid_tgt" != "$ccid_src"  ]]; then
    echo "Cant migrate to coins on different CC IDs! Aborting..."
   exit 1;
fi

int=${float%.*}
amount=$(echo ${src_balance%.*}+1|bc)
while [[ ${amount%.*} -gt ${src_balance%.*} ]]; do 
  echo -e -n "${col_blue}Enter sum to send: ${col_default}"
  read amount
done

echo -e -n "$col_blue"
PS3="Select target address: "
echo -e -n "$col_yellow"
addresses=($(komodo-cli -ac_name=$target listaddressgroupings | jq -r '.[][][0]'))
if [[ ${#addresses[@]} -gt 0 ]]; then
  while [[ ${#trg_addr} -ne 34 ]]; do
    select address in ${addresses[@]}
    do
      trg_addr=$address
      break
    done
  done
  else
    while [[ ${#trg_addr} -ne 34 ]]; do 
      echo -e -n "${col_blue}Enter target address: ${col_default}"
      read trg_addr
    done
fi
init_txt="Sending $amount from $source to $trg_addr on $target at $(date)"
echo $init_txt
echo $init_txt >> $result_logfile

printbalance

# Raw tx that we will work with
txraw=$($cli_source createrawtransaction "[]" "{\"$trg_addr\":$amount}")
echo "-------------createrawtransaction----------------------"
echo -e "${col_blue}"
echo -e 'createrawtransaction '${col_dkgrey}'"[]" "{\"'$trg_addr'\":'$amount'}"'
echo -e "${col_yellow}RETURNS txraw:${col_ltred} $txraw ${col_default}"
echo "-----------------------------------------------------"
# Convert to an export tx
exportData=`$cli_source migrate_converttoexport $txraw $target`
echo "exportData: $exportData" >> $result_logfile
exportTx=`echo $exportData | jq -r .exportTx`
payouts=`echo $exportData | jq -r .payouts`
echo "-------------migrate_converttoexport-----------------"
echo -e "${col_blue}"
echo -e "migrate_converttoexport ${col_ltred}$txraw ${col_dkgrey}$target"
echo -e "${col_yellow}RETURNS exportTx:${col_cyan} $exportTx"
echo -e "${col_yellow}RETURNS payouts:${col_magenta} $payouts ${col_default}"
echo "-----------------------------------------------------"

# Fund it
exportFundedData=`$cli_source fundrawtransaction $exportTx`
exportFundedTx=`echo $exportFundedData | jq -r .hex`
echo "exportFundedData: $exportFundedData" >> $result_logfile
echo "exportFundedTx: $exportFundedTx" >> $result_logfile
echo "-------------fundrawtransaction----------------------"
echo -e "${col_blue}"
echo -e "fundrawtransaction ${col_cyan} $exportTx"
echo -e "${col_yellow}RETURNS exportFundedData:${col_dkgrey} $exportFundedData"
echo -e "${col_yellow}RETURNS exportFundedTx:${col_red} $exportFundedTx ${col_default}"
echo "-----------------------------------------------------"

# 4. Sign rawtx and export
signedtx=`$cli_source signrawtransaction $exportFundedTx`
signedhex=`echo $signedtx | jq -r .hex`
echo "signedhex: $signedhex" >> $result_logfile
echo "-------------signrawtransaction----------------------"
echo -e "${col_cyan}"
echo -e "signrawtransaction ${col_red} $exportFundedTx"
echo -e "${col_yellow}RETURNS signedtx:${col_dkgrey} $signedtx"
echo -e "${col_yellow}RETURNS signedhex:${col_green} $signedhex ${col_default}"
echo "-----------------------------------------------------"

sentTX=`$cli_source sendrawtransaction $signedhex`
echo "sentTX: $sentTX" >> $result_logfile
echo "-------------sendrawtransaction----------------------"
echo -e "${col_cyan}"
echo -e "sendrawtransaction ${col_green}$signedhex"
echo -e "${col_yellow}RETURNS sentTX:${col_ltred} $sentTX ${col_default}"
echo "-----------------------------------------------------"


# Check if export transaction was created sucessfully
txidsize=${#sentTX}
if [[ $txidsize != "64" ]]; then
  echo -e "${col_red}Export TX not sucessfully created${col_default}"
  echo "$sentTX"
  echo "$signedhex"
  exit
fi

# 5. Wait for a confirmation on source chain.
waitforconfirm "$sentTX" "$cli_source"
echo -e "[$source] : ${col_ltred}Confirmed export $sentTX${col_default}"
echo "[$source] : Confirmed export $sentTX" >> $result_logfile

# 6. Use migrate_createimporttransaction to create the import TX
created=0
while [[ ${created} -eq 0 ]]; do
  echo "creating import tx... ($runTime sec)"
  sleep 60
  importTX=$($cli_source migrate_createimporttransaction $signedhex $payouts 2> /dev/null)
  if [[ "${importTX}" != "" ]]; then
    created=1
  fi
  runTime=$(echo $SECONDS-$initTime|bc)
done
echo "-------------migrate_createimporttransaction---------------"
echo -e "${col_cyan}"
echo -e "migrate_createimporttransaction ${col_green} $signedhex ${col_magenta} $payouts"
echo -e "${col_yellow}RETURNS importTX:${col_green} $importTX"
echo "-----------------------------------------------------------"
echo -e "${col_green}Create import transaction successful! ${runTime} sec${col_default}"
echo "importTX: $importTX" >> $result_logfile
echo "Create import transaction successful! (${runTime} sec)" >> $result_logfile


# 8. Use migrate_completeimporttransaction on KMD to complete the import tx
created=0
while [[ $created -eq 0 ]]; do
  echo "Signing import tx on KMD... ($runTime sec)"
  sleep 60
  completeTX=`komodo-cli migrate_completeimporttransaction $importTX 2> /dev/null`
  if [[ $completeTX != "" ]]; then
    created=1
  fi
  runTime=$(echo $SECONDS-$initTime|bc)
done
echo "-------------migrate_completeimporttransaction---------------"
echo -e "${col_cyan}"
echo -e "migrate_completeimporttransaction ${col_green} $importTX"
echo -e "${col_yellow}RETURNS completeTX:${col_ltred} $completeTX${col_default}"
echo "-----------------------------------------------------------"
echo "completeTX: $completeTX" >> $result_logfile
echo "Sign import transaction on KMD complete! ($runTime sec)" >> $result_logfile
echo -e "${col_green}Sign import transaction on KMD complete! ($runTime sec)${col_default}"

# 9. Broadcast tx to target chain
sent=0
tries=0
while [[ $sent -eq 0 ]]; do
  runTime=$(echo $SECONDS-$initTime|bc)
  echo "broadcasting import tx... ($runTime sec)"
  sleep 60
  sent_iTX=`$cli_target sendrawtransaction $completeTX 2> /dev/null`
  if [[ ${#sent_iTX} = "64" ]]; then
    sent=1
  elif [[ $sent_iTX != "" ]]; then
    echo -e "${col_red}"
    echo "------------------------------------------------------------"
    echo "Invalid txid returned from send import transacton"
    echo "Invalid txid returned from send import transacton" >> $result_logfile
    echo "$sent_iTX"
    echo "$completeTX"
    echo "-------------------------------------------------------------"
    echo -e "${col_default}"
    exit
  else
    tries=$(( $tries +1 ))
    if [[ $tries -ge 90 ]]; then
      echo -e "${col_red}"
      echo "------------------------------------------------------------"
      echo "Failed Import TX on $target at $(date)"
      echo "Exiting after 90 tries: $completeTX"
      echo "Exiting after 90 tries: $completeTX" >> $result_logfile
      echo "From Chain: $source"
      echo "Export TX: $sentTX"
      echo "$signedhex $payouts"
      echo "------------------------------------------------------------"
      echo -e "${col_default}"
      echo "$(date)   $signedhex $payouts" >> FAILED
      exit
    fi
  fi
done
echo "-------------sendrawtransaction----------------------"
echo -e "${col_cyan}"
echo -e "sendrawtransaction ${col_ltred} $completeTX"
echo -e "${col_yellow}RETURNS sent_iTX:${col_blue} $sent_iTX ${col_default}"
echo "-----------------------------------------------------"

waitforconfirm "$sent_iTX" "$cli_target"
runTime=$(echo $SECONDS-$initTime|bc)


import_blkhash=$($cli_target gettransaction $sent_iTX | jq '.blockhash')
import_blkheight=$($cli_target getblock $import_blkhash | jq '.height')
import_blktime=$($cli_target getblock $import_blkhash | jq '.time')
import_info=$($cli_target getimports $import_block)

export_blkhash=$($cli_source gettransaction $sent_TX | jq '.blockhash')
export_blkheight=$($cli_source getblock $export_blkhash | jq '.height')
export_blktime=$($cli_source getblock $import_blkhash | jq '.time')

migrate_json='{"export_txid":"'${sentTX}'","import_txid":"'${sent_iTX}'","amount":'${amount}',"to_address":"'${trg_addr}'","from_chain":"'${source}'","to_chain":"'${target}'","export_blkheight":"'${export_blkheight}'","import_blkheight":"'${import_blkheight}'"}'
echo "migrate_json: $migrate_json"


echo "sent_iTX: $sent_iTX" >> $result_logfile
echo -e "${col_green}[$source] : Confirmed export $sent_TX at ${export_blktime} ($runTime sec) on block ${export_blkheight}${col_default}"
echo -e "${col_green}[$target] : Confirmed import $sent_iTX at ${import_blktime} ($runTime sec) on block ${import_blkheight}${col_default}"
echo -e "${col_green}[$target] : Confirmed import $sent_iTX at ${import_blktime} ($runTime sec) on block ${import_blkheight}${col_default}" >> $result_logfile
echo "********************************************************************************************************************************" >> $result_logfile
printbalance
imports=$($cli_target getimports $import_blkheight)

echo "-------------getimports----------------------"
echo -e "${col_cyan}"
echo -e "getimports ${col_blue} $import_blkheight"
echo -e "${col_yellow}RETURNS imports:${col_blue} $imports ${col_default}"
echo "-----------------------------------------------------"

#komodo-cli -ac_name=CFEKX getimports $(echo $(komodo-cli -ac_name=CFEKX getinfo | jq '.blocks')-10 | bc)
#that wont give you any info about exports, until the import has been completed ...
#Becasuse that data is very hard to get ... which is why the migrate script its supposed to publish that to an oracle.
