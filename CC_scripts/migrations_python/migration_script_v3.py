#!/usr/bin/env python3

from slickrpc import Proxy
import time
import sys
import datetime
import os
import json
import re
import platform
import calendar

def selectRangeInt(low,high, msg):
    while True:
        try:
            number = int(input(msg))
        except ValueError:
            print("integer only, try again")
            continue
        if low <= number <= high:
            return number
        else:
            print("input outside range, try again")


def selectRangeFloat(low,high, msg):
    while True:
        try:
            number = float(input(msg))
        except ValueError:
            print("integer only, try again")
            continue
        if low <= number <= high:
            return number
        else:
            print("input outside range, try again")


def print_balance(rpc_connection_source, rpc_connection_destination):
    balance_source = rpc_connection_source.getbalance()
    balance_destination = rpc_connection_destination.getbalance()
    source_chain_name = rpc_connection_source.getinfo()["name"]
    destination_chain_name = rpc_connection_destination.getinfo()["name"]
    print("Source chain " + source_chain_name + " balance: " + str(balance_source))
    print("Destination chain " + destination_chain_name + " balance: " + str(balance_destination))


def create_import_transaction(rpc_connection, signed_hex, payouts):
    while True:
        try:
            import_tx = rpc_connection.migrate_createimporttransaction(signed_hex, payouts)
        except Exception as e:
            print(e)
            print("Back notarization not yet confirmed. Waiting 60s...")
            time.sleep(60)
            continue
        return import_tx


# adds the MoMoM hash to the import tx on the KMD chain.
def sign_momom_hash(rpc_connection, import_tx, offset):
    complete_tx = 0
    while complete_tx == 0:
        try:
            complete_tx = rpc_connection.migrate_completeimporttransaction(import_tx, offset)
        except Exception as e:
            print(e)
            if str(e) == "migrate_completeimporttransaction: offset higher than KMD chain height (code -1)":
                return(-1)
            if str(e) == "migrate_completeimporttransaction: Couldn't find MoM within MoMoM set (code -1)":
                return(-1)
            if str(e) != "migrate_completeimporttransaction: Cannot find notarisation for target inclusive of source (code -1)":
                return(0)
            else:
                print('Waiting for enough MoMoM notarizations on KMD')
                time.sleep(60)
    return complete_tx


# if the import transaction is failing, we will try to use a diffrent MoMoM hash signing on KMD to sledgehammer it through.
def create_backup_importtx(export):
    offset = 0
    while offset < 20:
        offset = offset + 1
        ret = sign_momom_hash(rpc_connection_kmdblockchain, export['import_tx_src'], offset)
        if ret == -1:
            break
        if ret != 0 and ret != export['import_tx_kmd']:
            print('Created backup import tx')
            return(ret)
    return(0)


def broadcast_on_destinationchain(rpc_connection, export):
    attempts = 0
    sent_itx = 0
    while attempts < 90:
        try:
            sent_itx = rpc_connection.sendrawtransaction(export['import_tx_kmd'])
        except Exception as p:
            print(str(p))
            if attempts > 20:
                if not 'import_tx_kmd_backup' in export or export['import_tx_kmd_backup'] == 0:
                    export['import_tx_kmd_backup'] = create_backup_importtx(export)
                if export['import_tx_kmd_backup'] != 0:
                    print(export['import_tx_kmd_backup'])
                    try:
                        sent_itx = rpc_connection.sendrawtransaction(export['import_tx_kmd_backup'])
                    except Exception as e:
                        print(str(e))
            attempts = attempts + 1
            print("Tried to broadcast " + str(attempts) + " times")
            print("Will try to do it up to 90 times in total. Now rest for 60 seconds.")
            time.sleep(60)
        if sent_itx != 0 and len(sent_itx) == 64:
            return sent_itx
    print('Failed to import the export transaction' + export['src_txid'])
    with open(failed_filename, "a+") as failed_imports_file:
        failed_imports_file.write("%s\n" % json.dumps(export))
    print('Saved export information to: ' + failed_filename)
    print('You will need to create the backup notary transaction from the info in this file!')
    return(0)


# define function that fetchs rpc creds from .conf
def def_credentials(chain):
    rpcport ='';
    operating_system = platform.system()
    if operating_system == 'Darwin':
        ac_dir = os.environ['HOME'] + '/Library/Application Support/Komodo'
    elif operating_system == 'Linux':
        ac_dir = os.environ['HOME'] + '/.komodo'
    elif operating_system == 'Win64':
        ac_dir = "dont have windows machine now to test"
    if chain == 'KMD':
        coin_config_file = str(ac_dir + '/komodo.conf')
    else:
        coin_config_file = str(ac_dir + '/' + chain + '/' + chain + '.conf')
    with open(coin_config_file, 'r') as f:
        for line in f:
            l = line.rstrip()
            if re.search('rpcuser', l):
                rpcuser = l.replace('rpcuser=', '')
            elif re.search('rpcpassword', l):
                rpcpassword = l.replace('rpcpassword=', '')
            elif re.search('rpcport', l):
                rpcport = l.replace('rpcport=', '')
    if len(rpcport) == 0:
        if chain == 'KMD':
            rpcport = 7771
        else:
            print("rpcport not in conf file, exiting")
            print("check "+coin_config_file)
            exit(1)

    return(Proxy("http://%s:%s@127.0.0.1:%d"%(rpcuser, rpcpassword, int(rpcport))))


# define function to load saved exports and resume process
def load_exports(filename):
    exports = []
    with open(filename) as file:
        for line in file:
            exports.append(json.loads(line))
    return exports


assetChains = []
ccids = []
ID=1
HOME = os.environ['HOME']

try:
    with open(HOME + '/StakedNotary/assetchains.json') as file:
        assetchains = json.load(file)
except Exception as e:
    print(e)
    print("Trying alternate location for file")
    with open(HOME + '/staked/assetchains.json') as file:
        assetchains = json.load(file)

for chain in assetchains:
    print(str(ID).rjust(3) + ' | ' + (chain['ac_name']+" ("+chain['ac_cc']+")").ljust(12))
    ID+=1
    assetChains.append(chain['ac_name'])
    ccids.append(chain['ac_cc'])
src_index = selectRangeInt(1,len(assetChains),"Select source chain: ")
src_chain = assetChains[src_index-1]
rpc_connection_sourcechain = def_credentials(src_chain)

ccid=ccids[src_index-1]
assetChains = []
ID=1
for chain in assetchains:
    if ccid == chain['ac_cc'] and src_chain != chain['ac_name']:
        print(str(ID).rjust(3) + ' | ' + (chain['ac_name']+" ("+chain['ac_cc']+")").ljust(12))
        ID+=1
        assetChains.append(chain['ac_name'])
if ID != 1:
    dest_index = selectRangeInt(1,len(assetChains),"Select destination chain: ")
else:
    print('No other asset chains with the same cc_id to migrate to, exiting')
    exit(0)
dest_chain = assetChains[dest_index-1]
rpc_connection_destinationchain = def_credentials(dest_chain)

rpc_connection_kmdblockchain = def_credentials('KMD')

# we can load a saved JSON to resume process.  
export_list = []
failed_filename = HOME + '/failed'+str(calendar.timegm(time.gmtime()))+'.txt'
t0 = time.time()
exports_filename = str(input('To load an export JSON file to resume enter the path to the file: '))
if len(exports_filename) == 0:
    migrations_amount = selectRangeInt(1,5000,"How many migrations?: ")
    balance=rpc_connection_sourcechain.getbalance()
    max_per_loop=balance/migrations_amount
    amount = selectRangeFloat(0,max_per_loop,"Amount of funds to send per migration (max: "+str(max_per_loop)+"): ")

    addresses = rpc_connection_destinationchain.listaddressgroupings()
    try:
        address = addresses[0][0][0]
    except:
        address = str(input('Address not found enter address: '))

    print('sending to '+ address)

    print_balance(rpc_connection_sourcechain, rpc_connection_destinationchain)

    print("Sending " + str(amount*migrations_amount) + " coins from " + rpc_connection_sourcechain.getinfo()["name"] + " chain " +\
          "to " + rpc_connection_destinationchain.getinfo()["name"] + " chain, with " + str(migrations_amount) + " migrateions.")

    counter_raw = migrations_amount
    # fixme save in current dir? or ask for file name? 
    exports_filename = HOME + '/exports_'+str(calendar.timegm(time.gmtime()))+'.txt'
    while counter_raw > 0:
        try:
            export_ret = rpc_connection_sourcechain.migrate_createburntransaction(str(dest_chain), str(address), str(amount))
        except Exception as e:
            if str(e) == "migrate_createburntransaction: You need to set -pubkey, or run setpukbey RPC, or imports are disabled on this chain. (code -1)":
                pubkey = str(input('Need to set pubkey, enter a pubkey: '))
                if len(pubkey) == 66:
                    rpc_connection_sourcechain.setpubkey(pubkey)
                    continue
                else:
                    sys.exit('pubkey wrong length, start again.')
            else: 
                print("Export TX not successfully created, waiting 30s before trying again.")
                time.sleep(30)
                continue
        signed_hex = export_ret["hex"]
        payouts = export_ret["payouts"]
        try: 
            sent_tx = rpc_connection_sourcechain.sendrawtransaction(str(signed_hex))
        except:
            print("Export TX not successfully sent, waiting 30s before trying again.")
            time.sleep(30)
            continue
        else:
            # save JSON object of each export, so we can resume it later if the script exits before finishing.
            export_obj = {}
            export_obj['src_txid'] = sent_tx
            export_obj['payouts'] = payouts
            export_obj['src_hex'] = signed_hex
            export_list.append(export_obj)
            with open(exports_filename, "a+") as export_transactions_file:
                export_transactions_file.write("%s\n" % json.dumps(export_obj))
            counter_raw = counter_raw - 1
    print("Export and payouts saved to: " + exports_filename + "\n")
    print(str(len(export_list)) + " export transactions sent:")
    for export in export_list:
        print(export['src_txid'])
    print("")

else:
    try:
        export_list = load_exports(exports_filename)
    except Exception as e:
        sys.exit(e)


# Wait for a notarization on source for each export tx.
for i in range(0, len(export_list)):
    finished = False
    while finished == False:
        ret = 0
        try: 
            ret = rpc_connection_sourcechain.getrawtransaction(export_list[i]['src_txid'], 1)["confirmations"]
        except Exception as e:
            print(str(export_list[i]['src_txid']) + ' not yet confirmed, waiting 30s...')
            time.sleep(30)
        if ret >= 2:
            print(str(export_list[i]['src_txid']) + ' has ' + str(ret) + ' confirmations on ' + str(dest_chain) + ' at ' + str(time.time()))
            finished = True
        elif ret == 1:
            print(str(export_list[i]['src_txid']) + ' not yet notarized, waiting 60s...')
            time.sleep(60)


# Use migrate_createimporttransaction to create the import TX
for i in range(0, len(export_list)):
    export_list[i]['import_tx_src'] = create_import_transaction(rpc_connection_sourcechain, export_list[i]['src_hex'], export_list[i]['payouts'])


# Use migrate_completeimporttransaction on KMD to sign the MoMoM hash. 
for i in range(0, len(export_list)):
    export_list[i]['import_tx_kmd'] = sign_momom_hash(rpc_connection_kmdblockchain, export_list[i]['import_tx_src'], 0)


# Send the import on the source chain
for i in range(0, len(export_list)):
    ret = broadcast_on_destinationchain(rpc_connection_destinationchain, export_list[i])
    if ret != 0:
        print('Sent import: ' + str(ret))
        export_list[i]['dest_txid'] = ret


# Wait for a confirmation on destination chain
for i in range(0, len(export_list)):
    finished = False
    while finished == False:
        ret = 0
        try: 
            ret = rpc_connection_destinationchain.getrawtransaction(export_list[i]['dest_txid'], 1)["confirmations"]
        except Exception as e:
            print(str(export_list[i]['dest_txid']) + ' not yet confirmed, waiting 30s...')
            time.sleep(30)
        if ret >= 1:
            print(str(export_list[i]['dest_txid']) + ' has ' + str(ret) + ' confirmations on ' + str(dest_chain) + ' at ' + str(time.time()))
            finished = True


t1 = time.time()
print("Total migrations amount: " + str(len(export_list)))
print(str(t1-t0) + " migration time (sec)")
