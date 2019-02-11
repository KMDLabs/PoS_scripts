#!/usr/bin/env python3

#Needs PIP3 install pandas numpy

from slickrpc import Proxy
import time
import sys
import datetime
import os
from subprocess import check_output, CalledProcessError
import json
import re
import platform
import calendar
import pandas as pd
import numpy as np
from threading import Thread

utxoamt = 0.00010000
ntrzdamt = -0.00083600
kmdntrzaddr = "RXL3YXG2ceaB6C5hfJcN4fvmLH2C34knhA"
txscanamount = 77777

# define function that fetchs rpc creds from .conf
def def_credentials(chain):
    rpcport ='';
    operating_system = platform.system()
    if operating_system == 'Darwin':
        ac_dir = os.environ['HOME'] + '/Library/Application Support/Komodo'
    elif operating_system == 'Linux':
        ac_dir = os.environ['HOME'] + '/.komodo'
    elif operating_system == 'Windows':
        ac_dir = '%s/komodo/' % os.environ['APPDATA']
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

def rpcThreads(chain, t0,):
    #Get the chain RPC credentials
    rpc_connection = def_credentials(chain)
    #Run the RPC commands to get base info
    try:
        chain_getinfo = rpc_connection.getinfo()
        unspents = pd.DataFrame(rpc_connection.listunspent())
        notaries = rpc_connection.getnotarysendmany()
        #Query the RPC replies and manipulate for the list
        chain_balance = chain_getinfo ["balance"]
        chain_blocks = chain_getinfo ["blocks"]
        chain_last_blox = rpc_connection.getblock(str(chain_blocks))
        chain_ntzblk = chain_getinfo ["notarized"]
        chain_cncts = chain_getinfo ["connections"]
        blox_time = chain_last_blox ["time"]
    except Exception as e:
        chain_balance = "error"
        chain_blocks = 0
        chain_ntzblk = "error"
        chain_cncts = e
        blox_time = t0
    try:
        nnutxoset = unspents[unspents['amount']==0.0001]
    except Exception as e:
        unspents = []
        nnutxoset = []
    try:
        transactions = pd.DataFrame(rpc_connection.listtransactions("",(chain_blocks - 100)))
        nntransactions = transactions[transactions['address']==kmdntrzaddr]
        if len(nntransactions) > 0:
            nntxbyconfirms = nntransactions.sort_values('confirmations',ascending=True)
            t1 = nntxbyconfirms['time'].values[0]
            readabletime = to_readabletime(t0,t1)
        else:
            nntransactions = []
            readabletime = ""
    except Exception as e:
        nntransactions = []
        readabletime = "error"
    if chain != 'KMD':
        for block in range(2, chain_blocks):
            getblock_result = rpc_connection.getblock(str(block), 2)
            if len(getblock_result['tx'][0]['vout']) > 1:
                vouts = getblock_result['tx'][0]['vout']
                for vout in vouts[1:]:
                    blah = vout['scriptPubKey']['addresses'][0]
                    if blah in notaries:
                        notaries[blah] += 1
                    else:
                        print('what')
        all_ntrz_df = pd.DataFrame(notaries.items(), columns=['notary','count'])
        all_ntrz_count = all_ntrz_df.sum(axis = 0, skipna=True) ['count']
        #print(all_ntrz_df)
        print(chain + " Total Notarizations in timeframe: " + str(all_ntrz_count))
        addresses = rpc_connection.listaddressgroupings()
        myaddress = addresses[0][0][0]
        my_ntrz_count = all_ntrz_df.loc[all_ntrz_df['notary'] == myaddress, 'count'].sum()
        pct_ntrz = (my_ntrz_count / all_ntrz_count) * 100
    else:
        pct_ntrz = ""
        my_ntrz_count = 0
    try:
        blocktime = to_readabletime(t0, blox_time,)
    except Exception as e:
        print(e)
    #Build and append list items
    list = (chain,chain_balance,len(unspents),len(nnutxoset),my_ntrz_count,pct_ntrz,readabletime,chain_blocks,blocktime,chain_ntzblk,chain_cncts)
    alt_list = (chain,chain_balance,len(unspents),chain_blocks,blocktime,chain_ntzblk,chain_cncts)
    global tmpList
    tmpList.append(list)
    global alt_tmpList
    alt_tmpList.append(alt_list)

def to_readabletime(t_zero, t_one,):
    t_time = (int(t_zero) - int(t_one))
    f_time = float(t_time)
    if f_time < 1:
        return ("0s")
    day = f_time // (24 * 3600)
    f_time %= (24 * 3600)
    hour = f_time // 3600
    f_time %= 3600
    minutes = f_time // 60
    f_time %= 60
    seconds = f_time
    d_sec = day + hour + minutes
    d_minutes = day + hour
    d_hours = day
    if d_sec == 0:
        return ("%ds" % (seconds))
    elif d_minutes == 0:
        return ("%dm:%ds" % (minutes, seconds))
    elif d_hours == 0:
        return ("%dh:%dm" % (hour, minutes))
    else:
        return("%dd:%dh:%dm" % (day, hour, minutes))

def print_balance():
    now = datetime.datetime.now()
    print("\nLatest stats " + (now.strftime("%Y-%m-%d %H:%M:%S")))
    t0 = time.time()
    tableCol = ['ASSET','BALANCE','UTXO','nnUTXO','NOTR','PCT','NOTR_t','chnBLOX','BLOX_t','NtrzHT','CNCT']
    alt_tableCol = ['ASSET','BALANCE','UTXO','chnBLOX','BLOX_t','NtrzHT','CNCT']
    #Create the thread loops
    for chain in assetChains:
        process = Thread(target=rpcThreads, args=[chain, t0,])
        process.start()
        threads.append(process)
    #Destroy the thread loops
    for process in threads:
        process.join()
    #Format the table and print
    pd.set_option('display.width', None)
    pd.set_option('display.max_columns',12)
    pd.set_option('precision', 4)
    pd.set_eng_float_format(accuracy=4, use_eng_prefix=True)
    #Assemble the table
    df = pd.DataFrame.from_records(tmpList, columns=tableCol)
    if (df.sum(axis = 0, skipna=True) ['NOTR']) == 0:
        df = pd.DataFrame.from_records(alt_tmpList, columns=alt_tableCol)
    df.sort_values(by=['chnBLOX'], ascending=False, inplace=True)
    df = df.reset_index(drop=True)
    print(df)
    print("")

# Define a function to check if chains are running
def running(chain):
    chain_name = chain
    try:
        pidlist = pd.DataFrame((list(map(int,check_output(["pidof", 'komodod']).split()))), columns = ['PID'])
    except  CalledProcessError:
        pidlist = []
    for row in pidlist.itertuples():
        output = str(check_output(['ps','-p',str(row.PID),'-o','cmd=']))
        if str(chain_name) in output:
            return True
            break
        elif str(chain_name) == 'KMD':
            operating_system = platform.system()
            if operating_system == 'Darwin':
                ac_dir = os.environ['HOME'] + '/Library/Application Support/Komodo'
            elif operating_system == 'Linux':
                ac_dir = os.environ['HOME'] + '/.komodo'
            elif operating_system == 'Win64':
                ac_dir = os.getenv('APPDATA') + '/komodo'
            KMD_pid_file = str(ac_dir + '/komodod.pid')
            try:
                with open(KMD_pid_file) as file:
                    KMD_pid = file.read()
                    file.close()
            except Exception as e:
                return False
                break
            if int(row.PID) == int(KMD_pid):
                return True
                break



#================================= Main Program =================================#

threads = []
assetChains = []
tmpList = []
alt_tmpList = []
HOME = os.environ['HOME']

#Get the chain names from the json file
try:
    with open(HOME + '/StakedNotary/assetchains.json') as file:
        assetchains = json.load(file)
except Exception as e:
    #print(e)
    #print("Trying alternate location for file")
    with open(HOME + '/staked/assetchains.json') as file:
        assetchains = json.load(file)

#Build the list of chains to report on
if running('KMD') == True:
    assetChains.append('KMD')
for chain in assetchains:
    if running(chain['ac_name']) == True:
        assetChains.append(chain['ac_name'])

#Run the loops and threads
print_balance()