from slickrpc import Proxy
import queue
from threading import Thread
import time

BROADCASTED_EXPORT_TXS = 0
CONFIRMED_EXPORT_TXS = 0
CONFIRMED_IMPORT_TXS = 0
BROADCASTED_IMPORT_TXS = 0
IMPORT_TXS_CREATED = 0
IMPORT_TXS_COMPLETED = 0


def print_balance(rpc_connection_source, rpc_connection_destination):
	balance_source = rpc_connection_source.getbalance()
	balance_destination = rpc_connection_destination.getbalance()
	source_chain_name = rpc_connection_source.getinfo()["name"]
	destination_chain_name = rpc_connection_destination.getinfo()["name"]
	print("Source chain " + source_chain_name + " balance: " + str(balance_source))
	print("Destination chain " + destination_chain_name + " balance: " + str(balance_destination))


# SET RPC CONNECTION DETAILS HERE
rpc_connection_sourcechain = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "password", 30667))
rpc_connection_destinationchain = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "password", 50609))
rpc_connection_kmdblockchain = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "password", 7771))

rpc_connection_sourcechain_2 = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "password", 30667))
rpc_connection_sourcechain_3 = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "password", 30667))
rpc_connection_destinationchain_1 = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "password", 50609))


# SET ADDRESS AND MIGRATION AMOUNT HERE
address = "RHq3JsvLxU45Z8ufYS6RsDpSG4wi6ucDev"
amount = 1


print_balance(rpc_connection_sourcechain, rpc_connection_destinationchain)

print("Sending " + str(amount) + " coins from " + rpc_connection_sourcechain.getinfo()["name"] + " chain " +\
	"to " + rpc_connection_destinationchain.getinfo()["name"] + " chain")


def create_export_txs(rpc_connection_source, export_queue):
	while True:
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
			time.sleep(0.01)


def create_import_txs(rpc_connection, queue_with_exports, import_queue):
	while True:
		data_from_queue = queue_with_exports.get()
		while True:
			try:
				import_tx = rpc_connection.migrate_createimporttransaction(data_from_queue["signed_hex"], data_from_queue["payouts"])
			except Exception as e:
				#print(e)
				#print("Import transaction not created yet, waiting for 10 seconds more")
				time.sleep(10)
				pass
			else:
				#print("Seems tx created")
				import_queue.put(import_tx)
				global IMPORT_TXS_CREATED
				IMPORT_TXS_CREATED += 1
				break


def migrate_import_txs(rpc_connection, import_txs_queue, migrated_import_txs_queue):
	while True:
		import_tx = import_txs_queue.get()
		while True:
			try:
				complete_tx = rpc_connection.migrate_completeimporttransaction(import_tx)
			except Exception as e:
				time.sleep(10)
				pass
			else:
				#print("Seems tx created")
				migrated_import_txs_queue.put(complete_tx)
				global IMPORT_TXS_COMPLETED
				IMPORT_TXS_COMPLETED += 1
				break


def broadcast_on_destinationchain(rpc_connection, complete_tx_queue, dest_tx_queue):
	attempts = 0
	while True:
		complete_tx = complete_tx_queue.get()
		while True:
			try:
				sent_itx = rpc_connection.sendrawtransaction(complete_tx)
			except:
				attempts = attempts + 1
				print("Tried to broadcast " + str(attempts) + " times")
				print("Will try broadcast again in 15 seconds.")
				time.sleep(15)
			else:
				print("Transactinon broadcasted on destination chain")
				dest_tx_queue.put(sent_itx)
				global BROADCASTED_IMPORT_TXS
				BROADCASTED_IMPORT_TXS += 1
				break


def check_if_confirmed_export(rpc_connection, queue_to_check, queue_with_confirmed):
	while True:
		data_from_queue = queue_to_check.get()
		while True:
			if int(rpc_connection.gettransaction(data_from_queue["tx_id"])["confirmations"]) > 0:
				queue_with_confirmed.put(data_from_queue)
				global CONFIRMED_EXPORT_TXS
				CONFIRMED_EXPORT_TXS +=1
				break
			else:
				time.sleep(5)


def check_if_confirmed_import(rpc_connection, queue_to_check, queue_with_confirmed):
	while True:
		data_from_queue = queue_to_check.get()
		while True:
			try:
				if int(rpc_connection.getrawtransaction(data_from_queue, 1)["confirmations"]) > 0:
					queue_with_confirmed.put(data_from_queue)
					global CONFIRMED_IMPORT_TXS
					CONFIRMED_IMPORT_TXS += 1
					break
				except Exception as e:
				print(e)
				print("Transaction is not on blockchain yet. Let's wait a little.")
				time.sleep(10)
				pass


def print_imports():
	t0 = time.time()
	global IMPORT_TXS_COMPLETED
	imports_counter = IMPORT_TXS_COMPLETED
	while True:
			t1 = time.time()
			if imports_counter == 0:
				migrations_per_second = 0
			else:
				migrations_per_second = (t1 - t0) / imports_counter
			print("Export transactions broadcasted: " + str(BROADCASTED_EXPORT_TXS))
			print("Export transactions confirmed: " + str(CONFIRMED_EXPORT_TXS))
			print("Import transactions created: " + str(IMPORT_TXS_CREATED))
			print("Import transactions completed on KMD chain: " + str(IMPORT_TXS_COMPLETED))
			print("Import transactions broadcasted: " + str(BROADCASTED_IMPORT_TXS))
			print("Import transactions confirmed: " + str(CONFIRMED_IMPORT_TXS))
			print(str(t1 - t0) + " seconds elapsed")
			print(str(CONFIRMED_IMPORT_TXS) + " migrations complete")
			print(str(CONFIRMED_IMPORT_TXS / (t1 - t0)) + " migrations/second speed\n")
			time.sleep(10)


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

# thread which creating export transactions
thread_export_txs = Thread(target=create_export_txs, args=(rpc_connection_sourcechain, export_tx_queue, ))

# thread which waiting for 1 confirmation on the source chain (estabilishing independed rpc proxy for each thread)
thread_wait_export_confirmation = Thread(target=check_if_confirmed_export, args=(rpc_connection_sourcechain_2, export_tx_queue, confirmed_export_queue,))

# thread which creating import transactions
thread_import_txs = Thread(target=create_import_txs, args=(rpc_connection_sourcechain_3, confirmed_export_queue, import_tx_queue,))

# thread which complete import txs on KMD chain
thread_complete_txs = Thread(target=migrate_import_txs, args=(rpc_connection_kmdblockchain, import_tx_queue, migrated_import_tx_queue))

# thread which trying to broadcast imports on destination chain
thread_broadcast_destination = Thread(target=broadcast_on_destinationchain, args=(rpc_connection_destinationchain, migrated_import_tx_queue, broadcasted_on_dest_queue))

# thread which waiting for 1 confirmation on destination chain
thread_wait_import_confirmation = Thread(target=check_if_confirmed_import, args=(rpc_connection_destinationchain_1, broadcasted_on_dest_queue, confirmed_on_dest_queue,))

# printer thread
printer_thread = Thread(target=print_imports)


thread_export_txs.start()
thread_wait_export_confirmation.start()
thread_import_txs.start()
thread_complete_txs.start()
thread_broadcast_destination.start()
thread_wait_import_confirmation.start()
printer_thread.start()