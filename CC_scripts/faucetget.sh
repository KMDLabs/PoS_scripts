#!/bin/bash
source ac
chain="komodo-cli -ac_name=$ac "

$chain sendrawtransaction $($chain faucetget | jq -r .hex)
