#!/usr/bin/env python3
import binascii
import sys
import re
import os
import requests
import json
import pprint

# configure pretty printer
pp = pprint.PrettyPrinter(width=41, compact=True)

# define function that fetchs rpc creds from .conf
def def_credentials(chain):
    #TODO: add osx/windows support for ac_dir
    ac_dir = os.environ['HOME'] + '/.komodo'

    # define config file path
    if chain == 'KMD':
        coin_config_file = str(ac_dir + '/komodo.conf')
    else:
        coin_config_file = str(ac_dir + '/' + chain + '/' + chain + '.conf')
    #define rpc creds
    with open(coin_config_file, 'r') as f:
        #print("Reading config file for credentials:", coin_config_file)
        for line in f:
            l = line.rstrip()
            if re.search('rpcuser', l):
                rpcuser = l.replace('rpcuser=', '')
            elif re.search('rpcpassword', l):
                rpcpassword = l.replace('rpcpassword=', '')
            elif re.search('rpcport', l):
                rpcport = l.replace('rpcport=', '')
    return('http://' + rpcuser + ':' + rpcpassword + '@127.0.0.1:' + rpcport)

# define function that posts json data
def post_rpc(url, payload, auth=None):
    try:
        r = requests.post(url, data=json.dumps(payload), auth=auth)
        return(json.loads(r.text))
    except Exception as e:
        raise Exception("Couldn't connect to " + url + ": ", e)

# define sendrawtransaction rpc
def getdatafromblock_rpc(RPCURL, block):
    sendrawpayload = {
        "jsonrpc": "1.0",
        "id": "python",
        "method": "getdatafromblock",
        "params": [block]}
    return(post_rpc(RPCURL, sendrawpayload))

# get arguments
if len(sys.argv) > 2:
    filename = sys.argv[1]
    startblock = sys.argv[2]
else:
    print('please specify path to output file to and block to start from')
    sys.exit()

# get rpc creds to be able to contact komodod
KOMODODURL = def_credentials('TEST2')

finished = 0
curblock = int(startblock)
lastseqid = 0
did1 = 0
while True :
    returnjson = getdatafromblock_rpc(KOMODODURL,str(curblock))
    try:
        datain = returnjson['result']['data']
    except Exception as e:
        print("block ",curblock," is empty or does not exist. We have reached the end of this stream.")
        break
    firstseqid =  int(returnjson['result']['firstseqid'])
    if firstseqid != 1 and did1 == 0:
        print("not starting at the first block, please start at block:", str(returnjson['result']['firstblockheight']))
        break
    if ( firstseqid != (lastseqid+1) ):
        print("first seq id in this block is not following the last in the last block.")
        break
    dataout = binascii.a2b_hex(datain)
    try:
        with open(filename, 'ab') as out_file:
            out_file.write(dataout)
    except Exception as e:
        print("write to file failed")
        break
    lastseqid = int(returnjson['result']['lastseqid'])
    curblock = curblock + 1
    if did1 == 0:
        did1 = 1
