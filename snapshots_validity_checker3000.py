import readline
import json

# TODO: maybe add snapshot making wizard for initial files easy preparation?

# just opening snapshots
while True:
    snapshot_of_source_chain = input("Input absolute path to initial snapshot json: ")
    try:
        file1 = open(snapshot_of_source_chain, "r+")
        break
    except Exception as e:
        print("Please re-check path to your file and try again")
while True:
    snapshot_of_destination_chain = input("Input absolute path to airdrop block snapshot json: ")
    try:
        file2 = open(snapshot_of_destination_chain, "r+")
        break
    except Exception as e:
        print("Please re-check path to your file and try again")


print("\nWelcome to the SnapshotsValidityChecker3000 human!\n")

source_chain_data = json.load(file1)
destination_chain_data = json.load(file2)

funds_delta = source_chain_data["total"] - destination_chain_data["total"]
addresses_delta = source_chain_data["total_addresses"] - destination_chain_data["total_addresses"]

if funds_delta == 0:
    print("Same sum was airdroped")
elif funds_delta > 0:
    print("On destination chain was airdroped " + str(funds_delta) + " coins less than needed")
else:
    print("On destination chain was airdroped " + str(funds_delta) + " coins more than needed")

if addresses_delta == 0:
    print("Same amount addresses in chains connection blocks (snapshot block and airdrop block)")
elif addresses_delta > 0:
    print("On destination chain " + str(abs(addresses_delta)) + " addresses less than needed")
else:
    print("On destination chain " + str(abs(addresses_delta)) + " addresses more than needed")


# let's convert both files to KV dicts where key is address and value is balance
source_chain_data_kv = {}
for address in source_chain_data["addresses"]:
    source_chain_data_kv.update({address["addr"] : address["amount"]})


destination_chain_data_kv = {}
for address in destination_chain_data["addresses"]:
    destination_chain_data_kv.update({address["addr"]: address["amount"]})

if len(source_chain_data_kv) != source_chain_data["total_addresses"]\
        or len(destination_chain_data_kv) != destination_chain_data["total_addresses"]:
    print("Something went wrong")

# finding if there any addresses for which balance wasn't transferred
matched_addresses = []
for key in source_chain_data_kv.keys():
    if key in destination_chain_data_kv.keys():
        matched_addresses.append(key)
    else:
        print("Balance for address " + key + " not airdropped at all")
        print("Not airdropped funds: " + str(source_chain_data_kv[key]))

#  finding if there any addresses on destination chain which shouldn't have any balance
for key in destination_chain_data_kv.keys():
    if key in source_chain_data_kv.keys():
        pass
    else:
        print("Balance for address " + key + " airdropped not legit!!!")
        print("Not legit balance airdropped: " + str(destination_chain_data_kv[key]))

# and let's compare also sums for "legit" addresses (to find out airdropped more or less cases)
for address in matched_addresses:
    if float(source_chain_data_kv[address]) == float(destination_chain_data_kv[address]):
        pass
    else:
        airdropped_delta = float(source_chain_data_kv[address]) - float(destination_chain_data_kv[address])
        if airdropped_delta > 0:
            print("To address " + address + " airdropped " + str(abs(airdropped_delta)) + " coins less than needed" )
        else:
            print("To address " + address + " airdropped " + str(abs(airdropped_delta)) + " coins more than needed")
