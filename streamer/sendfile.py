#!/usr/bin/env python3
import requests
import json
import pprint
import binascii
import sys

# config area
mm_ip = '127.0.0.1'
mm_port = '7782'
# end of config area

#Define marketmaker URL
mm_url = 'http://' + mm_ip + ':' + mm_port
userpass = "1d8b27b21efabcd96571cd56f91a40fb9aa4cc623d273c63bf9223dc6f8cd81f"

# configure pretty printer
pp = pprint.PrettyPrinter(width=41, compact=True)

# define function that posts json data to marketmaker
def post_rpc(url,payload):
    try:
        r = requests.post(url, data=json.dumps(payload))
        return(json.loads(r.text))
    except Exception as e:
        print("Couldn't connect to " + url, e)
        sys.exit(0)

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    print('please spscify path to file')
    sys.exit()

with open(filename, 'rb') as in_file:
    datain = in_file.read()

# convert file to hex string
dataout = binascii.hexlify(datain).decode("ascii")

#Define streamerqadd API JSON
queueadd = {
    "userpass" : userpass,
    "method" : "streamerqadd",
    "data" : dataout,
    "seqid" : 1
}

#Send payload withdraw API
response = post_rpc(mm_url,queueadd)
print('== response ==')
pp.pprint(response)
