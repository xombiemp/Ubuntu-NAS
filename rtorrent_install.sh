#!/bin/bash
#
#Written By: Randy Reed
#Date: 4/17/2011
#Modified By: Andrew Parker
#Date: 5/24/2011
#
#
# R A N D Y S T E C H . C O M

if [[ $EUID -ne 0 ]];then
    echo "rTorrent Installer: User has to be root"
    exit 1
fi

echo "R A N D Y S T E C H . C O M"

echo "UPDATING THE SYSTEM"
sudo apt-get update 
sudo apt-get upgrade -y
sudo apt-get install subversion build-essential automake libtool libcppunit-dev libcurl3-dev libsigc++-2.0-dev unzip unrar curl libncurses-dev -y
sudo apt-get install apache2 php5 php5-cli php5-curl php5-geoip -y

sudo apt-get install libapache2-mod-scgi -y
ln -s /etc/apache2/mods-available/scgi.load /etc/apache2/mods-enabled/scgi.load

echo "INSTALLING XMLRPC"
sleep 2
sudo mkdir -p /root/rtorrent/install
cd /root/rtorrent/install
sudo svn checkout http://xmlrpc-c.svn.sourceforge.net/svnroot/xmlrpc-c/advanced xmlrpc-c
cd xmlrpc-c
sudo ./configure
sudo make
sudo make install

echo "INSTALLING LIBTORRENT"
sleep 2
cd /root/rtorrent/install
sudo svn checkout svn://rakshasa.no/libtorrent/trunk/libtorrent
cd libtorrent
sudo ./autogen.sh
sudo ./configure
sudo make
sudo make install

echo "INSTALLING RTORRENT"
sleep 2
cd /root/rtorrent/install
sudo svn checkout svn://rakshasa.no/libtorrent/trunk/rtorrent
cd rtorrent
sudo ./autogen.sh
sudo ./configure --with-xmlrpc-c
sudo make
sudo make install
sudo ldconfig

echo "MAKING DIRECTORIES"
sudo mkdir /root/rtorrent/session
sudo mkdir /root/rtorrent/watch
sudo mkdir /root/rtorrent/downloads

cat > /root/.rtorrent.rc <<-END_SCRIPT
# This is an example resource file for rTorrent. Copy to
# ~/.rtorrent.rc and enable/modify the options as needed. Remember to
# uncomment the options you wish to enable.

# Maximum and minimum number of peers to connect to per torrent.
#min_peers = 40
#max_peers = 100

# Same as above but for seeding completed torrents (-1 = same as downloading)
#min_peers_seed = 10
#max_peers_seed = 50

# Maximum number of simultanious uploads per torrent.
#max_uploads = 15

# Global upload and download rate in KiB. "0" for unlimited.
#download_rate = 0
#upload_rate = 0

# Default directory to save the downloaded torrents.
directory = /root/rtorrent/downloads

# Default session directory. Make sure you don't run multiple instance
# of rtorrent using the same session directory. Perhaps using a
# relative path?
session = /root/rtorrent/session

# Watch a directory for new torrents, and stop those that have been
# deleted.
#schedule = watch_directory,5,5,load_start=./watch/*.torrent
#schedule = untied_directory,5,5,stop_untied=

# Close torrents when diskspace is low.
#schedule = low_diskspace,5,60,close_low_diskspace=100M

# Stop torrents when reaching upload ratio in percent,
# when also reaching total upload in bytes, or when
# reaching final upload ratio in percent.
# example: stop at ratio 2.0 with at least 200 MB uploaded, or else ratio 20.0
#schedule = ratio,60,60,"stop_on_ratio=200,200M,2000"

# The ip address reported to the tracker.
#ip = 127.0.0.1
#ip = rakshasa.no

# The ip address the listening socket and outgoing connections is
# bound to.
#bind = 127.0.0.1
#bind = rakshasa.no

# Port range to use for listening.
port_range = 6890-6999

# Start opening ports at a random position within the port range.
#port_random = no

# Check hash for finished torrents. Might be usefull until the bug is
# fixed that causes lack of diskspace not to be properly reported.
#check_hash = no

# Set whetever the client should try to connect to UDP trackers.
#use_udp_trackers = yes

# Alternative calls to bind and ip that should handle dynamic ip's.
#schedule = ip_tick,0,1800,ip=rakshasa
#schedule = bind_tick,0,1800,bind=rakshasa

# Encryption options, set to none (default) or any combination of the following:
# allow_incoming, try_outgoing, require, require_RC4, enable_retry, prefer_plaintext
#
# The example value allows incoming encrypted connections, starts unencrypted
# outgoing connections but retries with encryption if they fail, preferring
# plaintext to RC4 encryption after the encrypted handshake
#
# encryption = allow_incoming,enable_retry,prefer_plaintext

# Enable DHT support for trackerless torrents or when all trackers are down.
# May be set to "disable" (completely disable DHT), "off" (do not start DHT),
# "auto" (start and stop DHT as needed), or "on" (start DHT immediately).
# The default is "off". For DHT to work, a session directory must be defined.
# 
# dht = auto

# UDP port to use for DHT. 
# 
# dht_port = 6881

# Enable peer exchange (for torrents not marked private)
#
# peer_exchange = yes

#
# Do not modify the following parameters unless you know what you're doing.
#

# Hash read-ahead controls how many MB to request the kernel to read
# ahead. If the value is too low the disk may not be fully utilized,
# while if too high the kernel might not be able to keep the read
# pages in memory thus end up trashing.
#hash_read_ahead = 10

# Interval between attempts to check the hash, in milliseconds.
#hash_interval = 100

# Number of attempts to check the hash while using the mincore status,
# before forcing. Overworked systems might need lower values to get a
# decent hash checking rate.
#hash_max_tries = 10
scgi_port = 127.0.0.1:5000
END_SCRIPT

echo "INSTALLING RUTORRENT"
sleep 2
cd /var/www/
sudo svn checkout http://rutorrent.googlecode.com/svn/trunk/rutorrent
cd /var/www/rutorrent/
sudo rm -rf plugins/
sudo svn checkout http://rutorrent.googlecode.com/svn/trunk/plugins/
sudo chown -R www-data:www-data /var/www/rutorrent

echo "INSTALLING MEDIAINFO"
sleep 2
sudo apt-get install python-software-properties -y
sudo add-apt-repository ppa:shiki/mediainfo
sudo apt-get update
sudo apt-get install mediainfo -y

echo "CONFIGURING AUTH FILE"
sleep 2
cd /var/www/rutorrent
cat >> /etc/apache2/httpd.conf <<-END_PASTE
<VirtualHost *:80>
DocumentRoot /var/www
<Location /rutorrent>
Order Deny,Allow
AuthUserFile /var/www/rutorrent/.htpasswd
AuthName "ruTorrent login"
AuthType Basic
require valid-user
</Location>
SCGIMount /RPC2 127.0.0.1:5000
</VirtualHost>
END_PASTE

echo "ENTER A USERNAME"
read USERNAME
echo "ENTER PASSWORD FOR $USERNAME"
sudo htpasswd -c /var/www/rutorrent/.htpasswd $USERNAME

sudo chown www-data:www-data /var/www/rutorrent/.htpasswd

echo "INSTALLING SCREEN"
sleep 2
sudo apt-get install screen -y

echo "RESTARTING APACHE"
sudo /etc/init.d/apache2 restart
sleep 2

echo "GENERATING STARTUP SCRIPT"
cd /etc/init.d/
wget http://randystech.com/downloads/rtstart.sh
mv rtstart.sh rtorrentd
chmod +x /etc/init.d/rtorrentd
update-rc.d rtorrentd defaults

echo "STARTING RTORRENT"
sleep 5
service rtorrentd start

echo "R A N D Y S T E C H . C O M"
echo ""

echo "Your IP Address is:"
ifconfig | grep -m 1 inet\ addr: | cut -d: -f2 | awk '{print $1}' 
echo "YOU MAY NOW ACCESS YOUR RUTORRENT INTERFACE AT yourip/rutorrent"
echo ""
echo "TO START AND STOP YOUR RTORRENT USE:"
echo "service rtorrentd start|stop|restart"
sleep 5
