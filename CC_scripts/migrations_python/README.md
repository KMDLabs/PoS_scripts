Dependencies:

pip3 install setuptools wheel slick-bitcoinrpc

Change this data to setup the migration:

# SET RPC CONNECTION DETAILS HERE
rpc_connection_sourcechain = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "pass", 30667))
rpc_connection_destinationchain = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "pass", 50609))
rpc_connection_kmdblockchain = Proxy("http://%s:%s@127.0.0.1:%d"%("user", "pass", 7771))
# SET ADDRESS AND MIGRATION AMOUNT HERE
address = "RHq3JsvLxU45Z8ufYS6RsDpSG4wi6ucDev"
amount = 0.1

Run as:

python3 migration_script.py
