### Migrate Coin
To use these scripts you need a few things in place.
First you must be using the komodo verison from the StakedChain repo on MASTER branch.
To build and install this, use the `buildkomdod.sh` script in the install folder.

You need to sync KMD, not just the STAKED chains.
You can use a KMD snapshot: https://bootstrap.0x03.services/komodo/KMD.html

Komodo will  not be able to see notarizations back past the block you started it at, so it is best to start everything and wait for a while before starting any coin migrates.

`cp config_example.ini config.ini`

`nano config.ini`

Fill out the address details you will be using in migratecoin.sh.

Inside migratecoin.sh there is a place for Address and amount, this is the address the coins will move from and to make sure it is the same as the address in config.ini. Of course amount is the amount of coins  you are moving.

To start the chains and KMD simply run: `start.sh`

This will load KMD and the staked chain cluster and import the private key in config.ini. Once everything is synced here you are ready to go.

Start with a small amount your first time.

The default `migratecoin.sh` should be used IMO. If you seem to have having issues use the `migratecoinsNOpipe.sh` to get more prints.

When you run the print verison, it will print the cli call it is trying on the next step. If you are worried it is stuck, copy and paste this command into a new pane/terminal and run it to see what error its throwing.

Practice with this, you will soon figure out how the process works, seeing when it needs what info and what its looking for, the errors are pretty good generally until the very last step when trying to import the coin on the target chain.

Generally, just leaving the script to run will result in a sucessful migrate, but it can take some time. Especially if there has been a lag on notarizations.

If you think something has happened, make sure to save the transactions the print script prints and give them to us so we can try and figure out what happened. Once again, start with small amounts ;)
