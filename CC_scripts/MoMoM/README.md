### Migrate Coin
To use these scripts you need a few things in place.
First you must be using the komodo verison from the StakedChain repo on MASTER branch.

You need to sync KMD, not just the STAKED5 chains.
You can use a KMD snapshot or a previously synced .komodo folder for KMD, but it will  not be able to see notarizations back past the block you started it at, with this new branch.

Inside migratecoin.sh there is a place for Address and amount, this is the address the coins will move from and to. make sure the private key is impoted for the address you use, on both chains before you start the process.It does not need to be imported on KMD.

Start with a small amount your first time, maybe 1 or 2 STAKED.

Use the print version of the script at all times unless you dont mind losing coins in case of some bug or computer crash etc.

When you run the print verison, it will print the cli call it is trying on the next step. If you are worried it is stuck, copy and paste this command into a new pane/terminal and run it to see what error its throwing.

Practice with this, you will soon figure out how the process works, seeing when it needs what info and what its looking for, the errors are pretty good generally until the very last step when trying to import the coin on the target chain.

Generally, just leaving the script to run will result in a sucessful migrate, but it can take some time. Especially if there has been a lag on notarizations. We have new people running notaries, so I dont expect them to work perfectly all the time although we hope that they do.

Good luck, and dont be afraid to ask  questions in the #staked in KMD discord. There will be a lot of staked up for grabs to the first people who get a decent chuck of STAKED onto the staking chain. As always finding bugs will be the best way to get STAKED, but error messages are not bugs, which is why this script pipes them to /dev/null :D

If you think something has happened, make sure to save the transactions the print script prints and give them to us so we can try and figure out what happened. Once again, start with small amounts ;)
