#!/bin/bash
#Txblaster script
chain="TEST2"						    # chain name
cli="$HOME/staked/StakedModo/src/komodo-cli -ac_name=$chain" # cli path
passphrase=testpassphraseforsmk702test                      #passphrase for blast address
address=RSNWwEWTTFH13LzWVp4EoPscKNxsT5bazt                  #Address that the passphrase makes
amount=1000                                                 #the amount to send to blast address
streamid="komodo-cli"				    # stream ID, max 32 chars, cant be null?
timeout=120						    # timeout of blast loop, after this many seconds without receiving any data it will stop and exit marketmaker, ending the stream.

#address to send to, really irrellavent, can be any valid address. Diffrent amounts are likely possible, I think a low TX fee is needed to make sure notarisations are aways included in full blocks.
outputsarray=(
'[{"RPym8YEujHqvZJ3HTFj8NMs2xhMe2ZuVva":0.0001}]'
)

#number of loops, this should be no longer than the amount of tx you can send with the amount of coins you send the blaster.
loops=1000000
outputs=${outputsarray[0]}

waitforconfirm () {
  confirmations=0
  while [[ ${confirmations} -lt 1 ]]; do
    sleep 1
    confirmations=$(${cli} gettransaction $1 2> /dev/null | jq -r .confirmations) > /dev/null 2>&1
    # Keep re-broadcasting
    ${cli} sendrawtransaction $(${cli} getrawtransaction $1 2> /dev/null) > /dev/null 2>&1
  done
}

TXID=$(${cli} sendtoaddress $address $amount)
echo $TXID
rpcport=$(${cli} getinfo | jq -r .rpcport)
./marketmaker "{\"gui\":\"nogui\",\"client\":1, \"userhome\":\"/${HOME#"/"}\", \"passphrase\":\""default"\", \"coins\":[{\"coin\":\"$chain\",\"asset\":\"$chain\",\"rpcport\":$rpcport}], \"netid\":77}" &
sleep 5

echo "[$chain] waiting for confirm"
waitforconfirm $TXID

blast () {
  NewUTXO=$(curl -s --url "http://127.0.0.1:7783" --data "{\"userpass\":\"1d8b27b21efabcd96571cd56f91a40fb9aa4cc623d273c63bf9223dc6f8cd81f\",\"broadcast\":1,\"numblast\":$loops,\"password\":\"$passphrase\",\"utxotxid\":\"${lastutxo:-$TXID}\",\"utxovout\":${lastutxovout:-1},\"utxovalue\":${lastutxovalue:-$(( $amount * 100000000 ))},\"txfee\":50000,\"method\":\"txblast\",\"coin\":\"$chain\",\"outputs\":$outputs,\"timeout\":$timeout,\"streamid\":\"$streamid\"}")
}

blast
echo $NewUTXO
pkill -15 marketmaker
