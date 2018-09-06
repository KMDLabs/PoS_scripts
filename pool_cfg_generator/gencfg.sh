#!/bin/bash
# Put the address to mine to here, this is blackjok3r's please change to yours.
walletaddress=RPfQBwAmC6YK2SiedMmBgLPwoV1UihdeTW
# Put the chain name here
chain=STAKED3

# Stratum port to use
stratumport=4007

coinsdir=/home/$USER/Knomp/coins
poolconfigdir=/home/$USER/pool_configs
coinstpl=/home/$USER/Knomp/coins.template
pooltpl=/home/$USER/Knomp/poolconfigs.template

cointemplate=$(<$coinstpl)
pooltemplate=$(<$pooltpl)
string=$(printf '%08x\n' $(komodo-cli -ac_name=$chain getinfo | jq '.magic'))
magic=${string: -8}
magicrev=$(echo ${magic:6:2}${magic:4:2}${magic:2:2}${magic:0:2})

p2pport=$(komodo-cli -ac_name=$chain getinfo | jq '.p2pport')
thisconf=$(<~/.komodo/$chain/$chain.conf)

rpcuser=$(echo $thisconf | grep -Po "rpcuser=(\S*)" | sed 's/rpcuser=//')
rpcpass=$(echo $thisconf | grep -Po "rpcpassword=(\S*)" | sed 's/rpcpassword=//')
rpcport=$(echo $thisconf | grep -Po "rpcport=(\S*)" | sed 's/rpcport=//')

echo "$cointemplate" | sed "s/COINNAMEVAR/$chain/" | sed "s/MAGICREVVAR/$magicrev/" > $coinsdir/$chain.json
echo "$pooltemplate" | sed "s/P2PPORTVAR/$p2pport/" | sed "s/COINNAMEVAR/$chain/" | sed "s/WALLETADDRVAR/$walletaddress/" | sed "s/STRATUMPORTVAR/$stratumport/" | sed "s/RPCPORTVAR/$rpcport/" | sed "s/RPCUSERVAR/$rpcuser/" | sed "s/RPCPASSVAR/$rpcpass/" | sed "s/0.04/1/" > $poolconfigdir/$chain.json

