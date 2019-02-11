#!/usr/bin/env python3

from slickrpc import Proxy
import queue
from threading import Thread
import threading
import time
from slickrpc import Proxy
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

def print_balance(rpc_connection_source, rpc_connection_destination):
	balance_source = rpc_connection_source.getbalance()
	balance_destination = rpc_connection_destination.getbalance()
	source_chain_name = rpc_connection_source.getinfo()["name"]
	destination_chain_name = rpc_connection_destination.getinfo()["name"]
	print("Source chain " + source_chain_name + " balance: " + str(balance_source))
	print("Destination chain " + destination_chain_name + " balance: " + str(balance_destination) + "\n")


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
    dest_chain = selectRangeInt(1,len(assetChains),"Select destination chain: ")
else:
    print('No other asset chains with the same cc_id to migrate to, exiting')
    exit(0)
rpc_connection_destinationchain = def_credentials(assetChains[dest_chain-1])

rpc_connection_kmdblockchain = def_credentials('KMD')
migrations_amount = selectRangeInt(1,5000,"How many migrations?: ")
target_migrations = migrations_amount
balance=rpc_connection_sourcechain.getbalance()
max_per_loop=balance/migrations_amount
amount = selectRangeFloat(0,max_per_loop,"Amount of funds to send per migration (max: "+str(max_per_loop)+"): ")

addresses = rpc_connection_destinationchain.listaddressgroupings()

address = addresses[0][0][0]
print('sending to '+address)
 
BROADCASTED_EXPORT_TXS = 0
CONFIRMED_EXPORT_TXS = 0
CONFIRMED_IMPORT_TXS = 0
BROADCASTED_IMPORT_TXS = 0
IMPORT_TXS_CREATED = 0
IMPORT_TXS_COMPLETED = 0
BRK = []
list_threads = []

print_balance(rpc_connection_sourcechain, rpc_connection_destinationchain)

print("Sending " + str(amount * target_migrations) + " coins from " + rpc_connection_sourcechain.getinfo()["name"] + " chain " +\
	"to " + rpc_connection_destinationchain.getinfo()["name"] + " chain\n")

def input_thread(BRK):
	input()
	BRK.append(None)

def create_export_txs(rpc_connection_source, export_queue, txns_to_send):
	while True:
		for i in range(txns_to_send):
		#while True:
			if BRK: break
			raw_transaction = rpc_connection_source.createrawtransaction([], {address: amount})
			while True:
				try:
					export_data = rpc_connection_source.migrate_converttoexport(raw_transaction, rpc_connection_destinationchain.getinfo()["name"])
					break
				except Exception as e:
					print(e)
					time.sleep(1)
					break
			export_raw = export_data["exportTx"]
			export_funded_data = rpc_connection_source.fundrawtransaction(export_raw)
			export_funded_transaction = export_funded_data["hex"]
			payouts = export_data["payouts"]
			signed_hex = rpc_connection_source.signrawtransaction(export_funded_transaction)
			while True:
				try:
					sent_tx = rpc_connection_source.sendrawtransaction(signed_hex["hex"])
					break
				except Exception as e:
					print(e)
					time.sleep(1)
					break
			if len(sent_tx) != 64:
				print(signed_hex)
				print(sent_tx)
				print("Export TX not successfully created")
				time.sleep(1)
			else:
				data_for_queue = {"tx_id": sent_tx, "payouts": payouts, "signed_hex": signed_hex["hex"]}
				export_queue.put(data_for_queue)
				global BROADCASTED_EXPORT_TXS
				BROADCASTED_EXPORT_TXS += 1
				time.sleep(0.03)
		break

def create_import_txs(rpc_connection, queue_with_exports, import_queue):
	while True:
		data_from_queue = queue_with_exports.get()
		while True:
			try:
				import_tx = rpc_connection.migrate_createimporttransaction(data_from_queue["signed_hex"], data_from_queue["payouts"])
			except Exception as e:
				time.sleep(1)
				pass
			else:
				import_queue.put(import_tx)
				global IMPORT_TXS_CREATED
				IMPORT_TXS_CREATED += 1
				time.sleep(0.05)
				break
		if IMPORT_TXS_CREATED == BROADCASTED_EXPORT_TXS and IMPORT_TXS_CREATED > 0: break

def migrate_import_txs(rpc_connection, import_txs_queue, migrated_import_txs_queue):
	while True:
		import_tx = import_txs_queue.get()
		while True:
			try:
				complete_tx = rpc_connection.migrate_completeimporttransaction(import_tx)
			except Exception as e:
				time.sleep(1)
				pass
			else:
				migrated_import_txs_queue.put(complete_tx)
				global IMPORT_TXS_COMPLETED
				IMPORT_TXS_COMPLETED += 1
				time.sleep(0.05)
				break
		if IMPORT_TXS_COMPLETED == BROADCASTED_EXPORT_TXS and IMPORT_TXS_COMPLETED > 0: break

def broadcast_on_destinationchain(rpc_connection, complete_tx_queue, dest_tx_queue):
	while True:
		complete_tx = complete_tx_queue.get()
		while True:
			try:
				sent_itx = rpc_connection.sendrawtransaction(complete_tx)
			except:
				time.sleep(5)
			else:
				dest_tx_queue.put(sent_itx)
				global BROADCASTED_IMPORT_TXS
				BROADCASTED_IMPORT_TXS += 1
				time.sleep(1)
				break
		if BROADCASTED_IMPORT_TXS == BROADCASTED_EXPORT_TXS and BROADCASTED_IMPORT_TXS > 0: break


def check_if_confirmed_export(rpc_connection, queue_to_check, queue_with_confirmed):
	while True:
		data_from_queue = queue_to_check.get()
		while True:
			if int(rpc_connection.gettransaction(data_from_queue["tx_id"])["confirmations"]) > 0:
				queue_with_confirmed.put(data_from_queue)
				global CONFIRMED_EXPORT_TXS
				CONFIRMED_EXPORT_TXS +=1
				time.sleep(0.05)
				break
			else:
				time.sleep(10)
		if CONFIRMED_EXPORT_TXS == BROADCASTED_EXPORT_TXS and CONFIRMED_EXPORT_TXS > 0: break


def check_if_confirmed_import(rpc_connection, queue_to_check, queue_with_confirmed):
	while True:
		data_from_queue = queue_to_check.get()
		while True:
			try:
				if int(rpc_connection.getrawtransaction(data_from_queue, 1)["confirmations"]) > 0:
					queue_with_confirmed.put(data_from_queue)
					global CONFIRMED_IMPORT_TXS
					CONFIRMED_IMPORT_TXS += 1
					time.sleep(0.05)
					break
				else:
					time.sleep(10)
			except Exception as e:
				time.sleep(10)
				pass
		if CONFIRMED_IMPORT_TXS == BROADCASTED_EXPORT_TXS and CONFIRMED_IMPORT_TXS > 0: break


def print_imports():
	t0 = time.time()
	global IMPORT_TXS_COMPLETED
	imports_counter = IMPORT_TXS_COMPLETED
	time.sleep(5)
	while True:
		#time.sleep(60)
		if CONFIRMED_IMPORT_TXS < BROADCASTED_EXPORT_TXS:
			t1 = time.time()
			if imports_counter == 0:
				migrations_per_second = 0
			else:
				migrations_per_second = (t1 - t0) / imports_counter
			if thread_new_txns.isAlive():
				print("Press Enter to quit before " + str(target_migrations) + " broadcasted.")
			else:
				print("Running remaining tx's through the migration routine")
			print("Currently running " + str(threading.active_count() - 2) + " Threads")
			print("Export transactions broadcasted: " + str(BROADCASTED_EXPORT_TXS) + " Transactions of: " + str(amount))
			print("Export transactions confirmed: " + str(CONFIRMED_EXPORT_TXS) + " Queue: " + str(export_tx_queue.qsize()))
			print("Import transactions created: " + str(IMPORT_TXS_CREATED) + " Queue: " + str(confirmed_export_queue.qsize()))
			print("Import transactions completed on KMD chain: " + str(IMPORT_TXS_COMPLETED) + " Queue: " + str(import_tx_queue.qsize()))
			print("Import transactions broadcasted: " + str(BROADCASTED_IMPORT_TXS) + " Queue: " + str(migrated_import_tx_queue.qsize()))
			print("Import transactions confirmed: " + str(CONFIRMED_IMPORT_TXS) + " Queue: " + str(broadcasted_on_dest_queue.qsize()))
			print(str((t1 - t0) / 60) + " minutes elapsed")
			print(str(CONFIRMED_IMPORT_TXS) + " migrations complete")
			print(str(CONFIRMED_IMPORT_TXS / (t1 - t0)) + " migrations/second speed\n")
			time.sleep(60)
		else:
			break

def is_finished():
	t0 = time.time()
	time.sleep(10)
	while True:
		if CONFIRMED_IMPORT_TXS < BROADCASTED_EXPORT_TXS and BROADCASTED_EXPORT_TXS > 0:
			time.sleep(0.5)
		else:
			t1 = time.time()
			print("_Import transactions confirmed: " + str(CONFIRMED_IMPORT_TXS))
			print("_Sent " + str(CONFIRMED_IMPORT_TXS * amount) + " coins")
			print(str(t1 - t0) + " _seconds elapsed")
			print(str(CONFIRMED_IMPORT_TXS) + " _migrations complete")
			print(str(CONFIRMED_IMPORT_TXS / (t1 - t0)) + " _migrations/second speed\n")
			print_balance(rpc_connection_sourcechain, rpc_connection_destinationchain)
			break		
		



# queue of export transactions
export_tx_queue = queue.Queue()
# queue with confirmed export transactions
confirmed_export_queue = queue.Queue()
# queue with import transactions
import_tx_queue = queue.Queue()
# queue with complee import transactions
migrated_import_tx_queue = queue.Queue()
# queue with imports broadcasted on destination chain
broadcasted_on_dest_queue = queue.Queue()
# queue with imports confirmed on destination chain
confirmed_on_dest_queue = queue.Queue()

# thread to interupt exports
thread_new_txns = Thread(target=input_thread, args=(BRK,))
list_threads.append(thread_new_txns)

# thread which creating export transactions
thread_export_txs = Thread(target=create_export_txs, args=(rpc_connection_sourcechain, export_tx_queue, target_migrations))
list_threads.append(thread_export_txs)

# thread which waiting for 1 confirmation on the source chain (estabilishing independed rpc proxy for each thread)
thread_wait_export_confirmation = Thread(target=check_if_confirmed_export, args=(rpc_connection_sourcechain, export_tx_queue, confirmed_export_queue,))
list_threads.append(thread_wait_export_confirmation)

# thread which creating import transactions
thread_import_txs = Thread(target=create_import_txs, args=(rpc_connection_sourcechain, confirmed_export_queue, import_tx_queue,))
list_threads.append(thread_import_txs)

# thread which complete import txs on KMD chain
thread_complete_txs = Thread(target=migrate_import_txs, args=(rpc_connection_kmdblockchain, import_tx_queue, migrated_import_tx_queue))
list_threads.append(thread_complete_txs)

# thread which trying to broadcast imports on destination chain
thread_broadcast_destination = Thread(target=broadcast_on_destinationchain, args=(rpc_connection_destinationchain, migrated_import_tx_queue, broadcasted_on_dest_queue))
list_threads.append(thread_broadcast_destination)

# thread which waiting for 1 confirmation on destination chain
thread_wait_import_confirmation = Thread(target=check_if_confirmed_import, args=(rpc_connection_destinationchain, broadcasted_on_dest_queue, confirmed_on_dest_queue,))
list_threads.append(thread_wait_import_confirmation)

# printer thread
printer_thread = Thread(target=print_imports)
list_threads.append(printer_thread)

# thread monitoring completion
thread_finished = Thread(target=is_finished)
list_threads.append(thread_finished)

for i in list_threads: i.start()
