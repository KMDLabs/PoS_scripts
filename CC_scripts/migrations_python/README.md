### Dependencies

```shell
sudo apt-get install python3-dev
sudo apt-get install python3 libgnutls28-dev libssl-dev
sudo apt-get install python3-pip
pip3 install base58 slick-bitcoinrpc
```

staked or stakednotary repos and the coin daemons running, including KMD. 

https://github.com/KMDLabs/staked

https://github.com/KMDLabs/StakedNotary

### Setup of script 

You need to set the LOG_DIR at the top of the v4 script. 
example 
```shell
# set your log directory here, make sure the directory exists. All exports and failed imports will be logged here.
# without this funds can be lost!
LOG_DIR = '/home/test/migrate_logs/'
```

To resume a failed migrate simply start the script like so:

`python3 migration_script_v4.py /home/test/migrate_logs/exports_1552382813.txt`

To start a new migration just run the script like this: 

`python3 migration_script_v4.py`

Then follow the prompts. 

### Suggested to only use v4 script!
