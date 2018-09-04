#!/bin/bash
#Install Deps
sudo apt-get update
sudo apt-get install build-essential pkg-config libc6-dev m4 g++-multilib autoconf libtool ncurses-dev unzip git python python-zmq zlib1g-dev wget libcurl4-openssl-dev bsdmainutils automake curl
#Install Komodo
cd ~
git clone https://github.com/StakedChain/komodo.git -b dev
cd komodo
./zcutil/fetch-params.sh
./zcutil/build.sh -j$(nproc)
sudo ln -sf /home/$USER/komodo/src/komodo-cli /usr/local/bin/komodo-cli
sudo ln -sf /home/$USER/komodo/src/komodod /usr/local/bin/komodod
