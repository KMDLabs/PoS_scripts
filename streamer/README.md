# Streamer example scripts

### Needed software versions:
komodod from StakedChain/komodo branch: mastertest

SuperNET from StakedChain/SuperNET branch: streamer2

This repo for control scripts.

### To create your chain
Need -ac_name=<name> -ac_stream=2 and -ac_pubkey=03xxx... 
ac_supply will default to 100k if you dont set it. -ac_stream=1 is a private chain without easy mining (very fast blocks) ac_stream=2 is easy difficulty, allowing extreamly fast blocks, for streaming lots of data.

You need to import the private key for your ac_pubkey BEFORE block 128 or you cannot mine any blocks past 128.

DO NOT use -pubkey on the mining node, only -ac_pubkey *I think* maybe try this and see what happens?

### To activate the blaster loop
You will need to build marketmaker with `./m_mm` in SuperNET/iguana then move it to this directory.

running `./startmm.sh` will send a TX for the blaster to use, start marketmaker, wait for confirm, then activate the blast loop. There are options in this script at the top as follows:
```shell
chain="TEST2"                                               # chain name
cli="$HOME/staked/StakedModo/src/komodo-cli -ac_name=$chain" # cli path
passphrase=testpassphraseforsmk702test                      #passphrase for blast address
address=RSNWwEWTTFH13LzWVp4EoPscKNxsT5bazt                  #Address that the passphrase makes
amount=1000                                                 #the amount to send to blast address
streamid="streamnametouse"                                  # stream ID, max 32 chars, cant be null?
timeout=120                                                 # timeout of blast loop, after this many seconds without receiving any data it will stop and exit marketmaker, ending the stream.

#address to send to, really irrellavent, can be any valid address. Diffrent amounts are likely possible, I think a low TX fee is needed to make sure notarisations are aways included in full blocks.
outputsarray=(
'[{"RPym8YEujHqvZJ3HTFj8NMs2xhMe2ZuVva":0.0001}]'
)

#number of loops, this should be no longer than the amount of tx you can send with the amount of coins you send the blaster.
loops=1000000
```


### To send a file
`./sendfile.py <full path to file>`

example

`./sendfile.py /home/blackjok3r/marketmaker`

This script sends data into marketmaker via the secondary RPC port, its been tested in 2MB chunks and works fine, likely take more at once but is untested. Can change the CHUNKSIZE at the top of the script to test this.

### To extract a file from the blockchain
For this you need to know the block the stream starts at. I fould starting an explorer for your chain, and looking at the blocks there it was easy to see which block a stream starts, as there is an empty one 3 tx then instantly a full block after that. Likely need some better way to do this.

Also the RPC `getdatafromblock` will tell you the block height of the first chunk in the stream in that block. example:

```shell
$ ./komodo-cli -ac_name=TEST2 getdatafromblock 160 false
{
  "streamid": "testfileout",
  "firsttxid": "7ec91a91762574c65b0af23bca82164e06b6411f1d6f9cda47ba5c2292ee586f",
  "firstblockheight": 159,
  "firstseqid": 239,
  "lastseqid": 243
}
```
Line 62 of `getfile_fromchain.py` needs your chain name. example:

`KOMODODURL = def_credentials('TEST2')`

Once you have this info you can run the `getfile_fromchain.py <name of file to save> <block>` example:

`./getfile_fromchain.py marketmaker2 160`

That should be it... you can run `diff` on the two files to check they are the same. example:

`diff marketmaker marketmaker2`
