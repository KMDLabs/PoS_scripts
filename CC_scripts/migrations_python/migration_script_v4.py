#!/usr/bin/env python3

from slickrpc import Proxy
import time
import sys
import datetime
import os
import json
import re
import platform
import threading
import calendar


# set your log directory here, make sure the directory exists. All exports and failed imports will be logged here.
# without this funds can be lost!

path = os.environ['HOME']+'/migrate_logs/'
if os.path.exists(path) is False:
	os.mkdir(path)

LOG_DIR = os.environ['HOME']+'/migrate_logs/'


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


def colorize(string, color):
    colors = {
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'green': '\033[92m',
        'red': '\033[91m'
    }
    if color not in colors:
        return string
    else:
        return colors[color] + string + '\033[0m'


# define function to load saved exports and resume process
def load_exports(filename):
    exports = []
    with open(filename) as file:
        for line in file:
            exports.append(json.loads(line))
    return exports


def print_balance(rpc_connection_source, rpc_connection_destination):
    balance_source = rpc_connection_source.getbalance()
    balance_destination = rpc_connection_destination.getbalance()
    source_chain_name = rpc_connection_source.getinfo()["name"]
    destination_chain_name = rpc_connection_destination.getinfo()["name"]
    print("Source chain " + source_chain_name + " balance: " + str(balance_source))
    print("Destination chain " + destination_chain_name + " balance: " + str(balance_destination))


# Create import tx on source chain 
def create_import_transaction(rpc_connection, signed_hex, payouts, index):
    while True:
        try:
            import_tx = rpc_connection.migrate_createimporttransaction(signed_hex, payouts)
        except Exception as e:
            #print(e)
            print(index + "Back notarization not yet confirmed. Waiting 60s...")
            time.sleep(60)
            continue
        return import_tx


# adds a MoMoM hash to the import tx on the KMD chain.
def sign_momom_hash(rpc_connection, import_tx, offset, index):
    complete_tx = "0"
    while True:
        try:
            complete_tx = rpc_connection.migrate_completeimporttransaction(import_tx, offset)
        except Exception as e:
            #print(e)
            if str(e) == "migrate_completeimporttransaction: offset higher than KMD chain height (code -1)":
                return(-1)
            if str(e) == "migrate_completeimporttransaction: Couldn't find MoM within MoMoM set (code -1)":
                return(-1)
            print(index + 'Waiting for enough MoM notarizations on KMD')
            time.sleep(60)
            continue
        if complete_tx != "0":
            return complete_tx


# if the import transaction is failing, we will try to use a diffrent MoMoM hash signing on KMD to sledgehammer it through.
def create_backup_importtx(rpc_connection, export, index, txns_used):
    offset = 0
    while offset < 77:
        offset = offset + 1
        ret = sign_momom_hash(rpc_connection, export['import_tx_src'], offset, index)
        if ret == -1:
            return("0")
        if not ret in txns_used:
            print(index + colorize('Created backup import tx no: ' + str(len(txns_used)), 'red'))
            return(ret)
    return("0")


# function to try and broadcast the transaction on destination chain
def sendrawtransaction_dest(rpc_connection, signed_hex, index):
    txid_sent = "0"
    try:
        txid_sent = rpc_connection.sendrawtransaction(signed_hex)
    except Exception as e:
        #print(str(e))
        if str(e) == "sendrawtransaction: 18: import tombstone exists (code -26)" or str(e) == "sendrawtransaction: transaction already in block chain (code -27)":
            print(index + colorize('Import is already completed.... exiting thread', 'red'))
            return(-1)
    return(txid_sent)


# function to send import transaction, we need to use the above functions to choose a MoMoM hash that is present on the target chain,
# there is such a large range avalible eventually one of them will have a match, unless notarizations have stopped. 
def broadcast_on_destinationchain(rpc_connection, kmd_rpc_connection, export, index):
    attempts = 0
    dest_txid = 0
    sent_itx = "0"
    txns_used = []
    txns_used.append(export['import_tx_kmd'])
    dest = rpc_connection.getinfo()['name']
    if len(sys.argv) == 2:
        backup_limit = 1
    else:
        backup_limit = 10
    while attempts < 90:
        sent_itx = sendrawtransaction_dest(rpc_connection, export['import_tx_kmd'], index)
        if str(sent_itx) == "-1":
            return(0)
        if sent_itx != "0" and len(sent_itx) == 64:
            return sent_itx
        if str(sent_itx) == "0" and attempts > backup_limit:
            backup_txn = create_backup_importtx(kmd_rpc_connection, export, index, txns_used)
            if backup_txn != "0":
                txns_used.append(backup_txn)
            for txn in txns_used:
                if export['import_tx_kmd'] == txn:
                    continue
                sent_itx = sendrawtransaction_dest(rpc_connection, txn, index)
                if sent_itx != "0" and len(sent_itx) == 64:
                    return sent_itx
        attempts = attempts + 1
        print(index + "Waiting for MoMoM notarization on " + str(dest) + "... Attempts: " + str(attempts))
        time.sleep(60)
    print(index + colorize('Failed to import the export transaction' + export['src_txid'], 'red'))
    with open(failed_filename, "a+") as failed_imports_file:
        failed_imports_file.write("%s\n" % json.dumps(export))
    print(index + colorize('Saved export information to: ' + failed_filename, 'red'))
    print(index + colorize('You will need to create the backup notary transaction from the info in this file!', 'red'))
    return(0)


# define function to do a single migrate after the export tx has been created. 
def do_migrate(src, dest, sent_tx, payouts, signed_hex, index):
    rpc_sourcechain = def_credentials(src)
    rpc_destinationchain = def_credentials(dest)
    rpc_kmdblockchain = def_credentials('KMD')
    export = {}
    export['src_txid'] = sent_tx
    export['payouts'] = payouts
    export['src_hex'] = signed_hex
    # Wait for a notarization on source for each export tx.
    finished = False
    while finished == False:
        ret = 0
        try: 
            ret = rpc_sourcechain.getrawtransaction(export['src_txid'], 1)["confirmations"]
        except Exception as e:
            if str(e) == "getrawtransaction: No information available about transaction (code -5)":
                print(index + colorize('Export transaction never sent exiting thread...','red'))
                return(0)
            print(index + 'Waiting for ' + colorize('confirmation','green') + ' for: ' + str(export['src_txid']))
            time.sleep(30)
        if ret >= 2:
            print(index + str(export['src_txid']) + ' is ' + colorize('notarized','blue') + ' on ' + str(src) + ' after ' + str(ret) + colorize(' confirmations','green'))
            finished = True
        elif ret == 1:
            print(index + 'Waiting for ' + colorize('notarization','blue') + ' for: ' + str(export['src_txid']))
            time.sleep(60)
    # Use migrate_createimporttransaction to create the import TX
    export['import_tx_src'] = create_import_transaction(rpc_sourcechain, export['src_hex'], export['payouts'], index)
    # Use migrate_completeimporttransaction on KMD to sign the MoMoM hash. 
    while True:
        ret = sign_momom_hash(rpc_kmdblockchain, export['import_tx_src'], 0, index)
        if ret == -1:
            time.sleep(30)
            continue
        else:
            export['import_tx_kmd'] = ret 
            break
    # Send the import on the source chain
    ret = broadcast_on_destinationchain(rpc_destinationchain, rpc_kmdblockchain, export, index)
    if ret != 0:
        print(index + 'Sent import: ' + str(ret))
        export['dest_txid'] = ret
        # Wait for a confirmation on destination chain
        finished = False
        while finished == False:
            ret = 0
            try: 
                ret = rpc_destinationchain.getrawtransaction(export['dest_txid'], 1)["confirmations"]
            except Exception as e:
                print(index + 'Waiting for ' + colorize('confirmation','green') + ' for: ' + str(export['dest_txid']))
                time.sleep(30)
            if ret >= 1:
                print(index + str(export['dest_txid']) + ' has ' + str(ret) + colorize(' confirmations','green') + ' on ' + str(dest))
                finished = True


# we can load a saved JSON to resume process.
failed_filename = LOG_DIR + 'failed'+str(calendar.timegm(time.gmtime()))+'.txt'
exports_filename = ""
t0 = time.time()
thread_list = []
if len(sys.argv) == 2:
    exports_filename = sys.argv[1]

if len(exports_filename) == 0:
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
    src_index = selectRangeInt(1,len(assetChains),colorize("Select source chain: ", "green"))
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
        dest_index = selectRangeInt(1,len(assetChains),colorize("Select destination chain: ", "green"))
    else:
        print('No other asset chains with the same cc_id to migrate to, exiting')
        sys.exit(0)
    dest_chain = assetChains[dest_index-1]
    rpc_connection_destinationchain = def_credentials(dest_chain)

    migrations_amount = selectRangeInt(1,5000,colorize("How many migrations?: ", 'green'))
    sleepy_time = selectRangeInt(2,5000,colorize("Seconds between each import: ", 'green'))
    balance=rpc_connection_sourcechain.getbalance()
    max_per_loop=balance/migrations_amount
    amount = selectRangeFloat(0,max_per_loop,colorize("Amount of funds to send per migration (max: "+str(max_per_loop)+"): ", 'green'))

    addresses = rpc_connection_destinationchain.listaddressgroupings()
    try:
        address = addresses[0][0][0]
    except:
        address = str(input(colorize('Address not found enter address: ', 'green')))

    print('sending to '+ address)

    print_balance(rpc_connection_sourcechain, rpc_connection_destinationchain)

    print("Sending " + str(amount*migrations_amount) + " coins from " + rpc_connection_sourcechain.getinfo()["name"] + " chain " +\
          "to " + rpc_connection_destinationchain.getinfo()["name"] + " chain, with " + str(migrations_amount) + " migrations.")

    counter_raw = migrations_amount
    # fixme save in current dir? or ask for file name? 
    exports_filename = LOG_DIR + 'exports_'+str(calendar.timegm(time.gmtime()))+'.txt'
    while counter_raw > 0:
        index = colorize('[' + str(migrations_amount - counter_raw + 1) + ']: ', 'magenta')
        try:
            export_ret = rpc_connection_sourcechain.migrate_createburntransaction(str(dest_chain), str(address), str(amount))
        except Exception as e:
            if str(e) == "migrate_createburntransaction: You need to set -pubkey, or run setpukbey RPC, or imports are disabled on this chain. (code -1)":
                pubkey = str(input(colorize('Need to set pubkey, enter a pubkey: ', 'green')))
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
        counter_raw = counter_raw - 1
        # save JSON object of each export, so we can resume it later if the script exits before finishing.
        export_obj = {}
        export_obj['src_chain'] = src_chain
        export_obj['dest_chain'] = dest_chain
        export_obj['src_txid'] = sent_tx
        export_obj['payouts'] = payouts
        export_obj['src_hex'] = signed_hex
        with open(exports_filename, "a+") as export_transactions_file:
            export_transactions_file.write("%s\n" % json.dumps(export_obj))
        t = threading.Thread(target=do_migrate, args=(src_chain, dest_chain, sent_tx, payouts, signed_hex, index))
        thread_list.append(t)
        thread_list[len(thread_list)-1].start()
        time.sleep(sleepy_time)
else:
    export_list = []
    try:
        export_list = load_exports(exports_filename)
    except Exception as e:
        sys.exit(e)
    for i in range(0, len(export_list)):
        src_chain = export_list[i]['src_chain']
        dest_chain = export_list[i]['dest_chain']
        sent_tx = export_list[i]['src_txid'] 
        payouts = export_list[i]['payouts']
        signed_hex = export_list[i]['src_hex']
        index = colorize('[' + str(i+1) + ']: ', 'magenta')
        t = threading.Thread(target=do_migrate, args=(src_chain, dest_chain, sent_tx, payouts, signed_hex, index))
        thread_list.append(t)
        thread_list[len(thread_list)-1].start()
        time.sleep(0.005)

for thread in thread_list:
    thread.join()

t1 = time.time()
print("Total migrations amount: " + str(len(thread_list)))
print(str(t1-t0) + " migration time (sec)")
