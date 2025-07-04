#!/bin/bash
cd ~
mkdir tvh-build
cd ~/tvh-build
sudo apt install build-essential git pkg-config libssl-dev bzip2 wget libavahi-client-dev zlib1g-dev libavcodec-dev libavutil-dev libavformat-dev libswscale-dev liburiparser-dev libbsd-dev gettext cmake libdvbcsa-dev python-is-python3
git clone https://github.com/tvheadend/tvheadend.git
cd tvheadend
./configure
make
sudo make install
