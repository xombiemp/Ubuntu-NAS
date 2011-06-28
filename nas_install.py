#!/usr/bin/python -tt
# Written by Andrew Parker

# This is a script to configure a Ubuntu NAS. 
# It was designed to be run on a fresh install of Ubuntu server 10.04 that had the OpenSSH and Samba File Server roles installed.
# It will perform the following: (* = requires user interaction.)
# - *Create a password for the root account.
# - Edit the .bashrc files of root and default user to include color and completion and create lla alias.
# - Install all updates available.
# - Remove all unnecessary packages.
# - Remove all kernel files in /boot except for the most recent one.
# - *Install and configure Postfix to work with a Gmail address. (will prompt for address and password)
# - *Install mdadm and create a raid 5 device named /dev/md0 using 4 drives that are user specified.
# - Install lvm2 and create a physical volume on /dev/md0, a volume group named vg with a physical extent of 32 MiB and a logical volume named vol1 taking all free space.
# - Install xfsprogs and create a xfs partition on the logical volume filling all freespace and set to mount on /mnt/vg/vol1.
# - *Configure samba by creating a share named data on the xfs file system and creating a smb user. The user will be the same as the default user and it will prompt for a password.
# - Install rtorrent and rutorrent front end:
# -- Install all the prereqs including php5 and apache2
# -- Install xmlrpc from svn.
# -- Install libtorrent from svn.
# -- Install rtorrent from svn configured with the --with-xmlrpc-c parameter.
# -- Create a default .rtorrent.rc config file in /root.
# -- Install rutorrent from svn.
# -- Install all rutorrent plugins from svn.
# -- Install mediainfo, which is a prereq for one of the plugins.
# -- *Create an auth file for the rutorrent interface. The user will be the same as the default user and it will prompt for a password.
# -- Create a start up script for rtorrent so it starts on boot without having to login. Control the service with "service rtorrentd start|stop|restart".
# -- Create an update script in /usr/local/bin named rtorrent_update that updates xmlrpc, libtorrent, rtorrent, rutorrent and all the plugins.

import sys
import os
import subprocess
import re
import shutil
import pwd
import time
import getpass


def saveBash(cmd):
  p = subprocess.Popen(cmd, shell=True, executable="/bin/bash", stdout=subprocess.PIPE)
  out = p.stdout.read().strip()
  return out  #This is the stdout from the shell command

def runBash(cmd):
  p = subprocess.call(['/bin/bash', '-c', cmd])
  return p

def naturallysorted(L, reverse=False): 
  """Similar functionality to sorted() except it does a natural text sort 
  which is what humans expect when they see a filename list. 
  """
  convert = lambda text: ('', int(text)) if text.isdigit() else (text, 0) 
  alphanum = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
  return sorted(L, key=alphanum, reverse=reverse)

def main():
  if os.geteuid() != 0:
      print "This program must be run as root. Aborting."
      sys.exit(1)


  ### Edit .bashrc, uncomment color prompt and completion ###
  print '\nEDITING .bashrc FOR COLOR AND COMPLETION\n...............'
  time.sleep(1.5)
  print('Create password for root:')
  runBash("""while !(passwd root) ; do
    echo "There was an error. Try again."
  done""")
  userName = pwd.getpwuid(1000)[0]
  dirs = ['/root/.bashrc', '/home/' + userName + '/.bashrc']
  for dir in dirs:
    f = open(dir, 'r+')
    lines = f.readlines()
  
    for line in lines[:]:
    
      if 'alias ll=' in line:
        if lines[lines.index(line) + 1] == "alias lla='ls -la'\n":
          continue
        else:
          lines[lines.index(line)] = "alias ll='ls -l'\nalias lla='ls -la'\n"
    
      if ('#force_color_prompt=yes' in line) or \
      ('#if [ -f /etc/bash_completion ] && ! shopt -oq posix; then' in line) or \
      ('. /etc/bash_completion' in line) or \
      ('#fi' in line and line == lines[-1]):
        lines[lines.index(line)] = line.replace('#', '')
  
    f.seek(0, 0)
    f.writelines(lines)
    f.close()
  
  
  ### Update system packages and clean up ###
  print '\nUPDATING SYSTEM AND CLEANING UP\n...............'
  time.sleep(1.5)
  updates = []
  updates.append('apt-get update -y')
  updates.append('apt-get dist-upgrade -y')
  updates.append('apt-get autoclean -y')
  updates.append('apt-get autoremove -y')
  
  for update in updates:
    runBash(update)
  
  files = '\n'.join(os.listdir('/boot/'))
  kernels = naturallysorted(list(set(re.findall(r'(\d\.\d.\d+-\d+)', files))))
  if len(kernels) != 1:
    for kernel in kernels:
      if kernel != kernels[-1]:
        runBash('rm /boot/*' + kernel + '*')
  runBash('update-grub')
  if os.path.exists('/etc/motd.tail'):
    os.remove('/etc/motd.tail')
  
  
  ### Configure Postfix for email alerts ###
  print '\nCONFIGURING POSTFIX FOR EMAIL ALERTS\n...............'
  time.sleep(1.5)
  runBash('DEBIAN_FRONTEND=noninteractive apt-get install postfix -y')
  shutil.copy('/usr/share/postfix/main.cf.debian', '/etc/postfix/main.cf')
  postfix_conf = """
# TLS parameters
smtpd_tls_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
smtpd_use_tls=no
smtpd_tls_session_cache_database = btree:${data_directory}/smtpd_scache
smtp_tls_session_cache_database = btree:${data_directory}/smtp_scache

# See /usr/share/doc/postfix/TLS_README.gz in the postfix-doc package for
# information on enabling SSL in the smtp client.

myhostname = nas
alias_maps = hash:/etc/aliases
alias_database = hash:/etc/aliases
virtual_alias_maps = hash:/etc/postfix/virtual
myorigin = gmail.com
mydestination =
relayhost = [smtp.gmail.com]:587
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
mailbox_size_limit = 0
recipient_delimiter = +
inet_interfaces = loopback-only
default_transport = smtp
relay_transport = smtp
inet_protocols = all

# SASL Settings
smtp_use_tls=yes
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_sasl_tls_security_options = noanonymous
smtp_tls_CAfile = /etc/postfix/cacert.pem
"""

  f = open('/etc/postfix/main.cf', 'a')
  f.write(postfix_conf)
  f.close()

  email = raw_input('Type your full Gmail address:\n')
  while True:
    email_passwd = getpass.getpass('\nGmail password:')
    email_passwd_conf = getpass.getpass('Retype Gmail password:')
    if email_passwd == email_passwd_conf:
      break
    else:
      print 'Passwords did not match. Try again'
  f = open('/etc/postfix/sasl_passwd', 'w')
  f.write('[smtp.gmail.com]:587 ' + email + ':' + email_passwd + '\n')
  f.close()
  os.chmod('/etc/postfix/sasl_passwd', 0400)

  f = open('/etc/postfix/virtual', 'w')
  f.write('root\troot@localhost\n' + userName + '\t' + userName + '@localhost\n')
  f.close()

  runBash('postmap /etc/postfix/virtual')
  runBash('postmap /etc/postfix/sasl_passwd')

  shutil.copy('/etc/ssl/certs/Equifax_Secure_CA.pem', '/etc/postfix/cacert.pem')
  runBash('/etc/init.d/postfix restart')


  ### Create Raid Partitions ###
  print '\nCREATING RAID PARTITIONS\n...............'
  time.sleep(1.5)
  runBash('parted -l')
  disks = re.findall(r'(/dev/\w{3})', saveBash('parted -l'))
  for i, disk in enumerate(disks):
    print i, '-', disk
  
  print """Please enter four corresponding numbers of the drives you would like 
to add to the raid with spaces inbetween, followed by the Enter key.
ex: 0 1 2 3"""
  
  while True:
    diskIndexes = sys.stdin.readline()
    if re.search(r'\d+\s\d+\s\d+\s\d+\n', diskIndexes):
      diskIndexes = naturallysorted(diskIndexes.split())
      if (all(int(num) < len(disks) for num in diskIndexes)) and (len(list(set(diskIndexes))) == 4):
        break
      else:
        print 'Please enter unique numbers in the range of 0 to ' + str(len(disks) - 1)
    else:
      print 'Please enter four numbers with spaces inbetween, followed by the Enter key.'
  
  raid_drives = []
  parted_cmds = []
  mdadm_cmd = 'mdadm --create --verbose /dev/md0 --level=5 --raid-devices=4'
  for diskIndex in diskIndexes:
    parted_cmd = []
    parted_cmd.append('parted -- ' + disks[int(diskIndex)] + ' mklabel gpt')
    parted_cmd.append('parted -- ' + disks[int(diskIndex)] + ' mkpart primary 1 -1')
    parted_cmd.append('parted -- ' + disks[int(diskIndex)] + ' set 1 raid on')
    parted_cmds.append(parted_cmd)
    mdadm_cmd += ' ' + disks[int(diskIndex)] + '1'
    raid_drives.append(disks[int(diskIndex)] + '1') 
  
  for parted_cmd in parted_cmds:
    for cmd in parted_cmd:
      runBash(cmd)
    
  runBash('partprobe')
  runBash('apt-get install mdadm -y')
  runBash(mdadm_cmd)
  firstRun = 1
  while True:
    mdstat = saveBash('cat /proc/mdstat')
    if not 'recovery' in mdstat:
      break
    elif firstRun:
      print 'Building raid array. Please wait...'
      firstRun = 0
  runBash('mdadm --detail --scan >> /etc/mdadm/mdadm.conf')
  
  f = open('/etc/mdadm/mdadm.conf', 'r+')
  lines = f.readlines()
  for line in lines[:]:
    if 'MAILADDR' in line:
      lines[lines.index(line)] = line.replace('root', email)
    elif '00.90' in line:
      lines[lines.index(line)] = line.replace('00.90', '0.90')
  f.seek(0, 0)
  f.writelines(lines)
  f.close()
  runBash('mdadm --monitor -1 --scan --test')


  ### Create LVM ###
  print '\nCREATING LVM\n...............'
  time.sleep(1.5)
  lvm_cmds = []
  lvm_cmds.append('apt-get install lvm2 -y')
  lvm_cmds.append('pvcreate /dev/md0')
  lvm_cmds.append('vgcreate -s 32768K vg /dev/md0')
  lvm_cmds.append('lvcreate -n vol1 -l 100%FREE vg')
  for lvm_cmd in lvm_cmds:
    runBash(lvm_cmd)
  
  
  ### Create XFS file system ###
  print '\nCREATING XFS FILE SYSTEM\n...............'
  time.sleep(1.5)
  xfs_cmds = []
  xfs_cmds.append('apt-get install xfsprogs -y')
  xfs_cmds.append('mkfs.xfs /dev/mapper/vg-vol1')
  for xfs_cmd in xfs_cmds:
    runBash(xfs_cmd)
    
  if not os.path.exists('/mnt/vg/vol1/'):
    os.makedirs('/mnt/vg/vol1/')
    
  f = open('/etc/fstab', 'a')
  f.write('/dev/vg/vol1 /mnt/vg/vol1 xfs defaults,usrquota,grpquota 0 0\n')
  f.close()
  
  runBash('mount -a')
  
  if not os.path.exists('/mnt/vg/vol1/data'):
    os.mkdir('/mnt/vg/vol1/data')
  
  gid = saveBash('getent group sambashare | cut -d: -f3')
  os.chown('/mnt/vg/vol1/data', 1000, int(gid))


  ### Configure Samba share ###
  print '\nCONFIGURING SAMBA SHARE\n...............'
  time.sleep(1.5)
  smb_conf = """
[global]
  workgroup = WORKGROUP
  server string = %h server
  log file = /var/log/samba/log.%m
  max log size = 1000
  display charset = LOCALE
  unix charset = UTF-8
  dos charset = CP850
  encrypt passwords = true
  security = user
  passdb backend = tdbsam
  unix password sync = yes
  passwd program = /usr/bin/passwd %u
  passwd chat = *Enter\snew\s*\spassword:* %n\n *Retype\snew\s*\spassword:* %n\n *password\supdated\ssuccessfully* .
  pam password change = no
  obey pam restrictions = yes
  load printers = no
  show add printer wizard = no
  printing = none
  printcap name = /dev/null
  disable spoolss = yes
  syslog = 0
  panic action = /usr/share/samba/panic-action %d
  unix extensions = no

[data]
  comment = data
  path = /mnt/vg/vol1/data
  read only = no
  writeable = yes
  oplocks = yes
  level2 oplocks = yes
  force security mode = 0
  dos filemode = yes
  dos filetime resolution = yes
  dos filetimes = yes
  fake directory create times = yes
  browseable = yes
  csc policy = manual
  share modes = yes
  veto oplock files = /*.mdb/*.MDB/*.dbf/*.DBF/
  veto files = /*:Zone.Identifier:*/
  create mode = 0770
  directory mode = 2770
  printable = no
  guest ok = no
  hosts allow =  192.168.0.0/16 10.0.0.0/8
  hosts readonly allow =
  store dos attributes = yes
  map acl inherit = yes
"""
  
  f = open('/etc/samba/smb.conf', 'w')
  f.write(smb_conf)
  f.close()
  runBash('service smbd restart')
  print '\nEnter a password for', userName + ':'
  runBash("""while !(smbpasswd -a """ + userName + """) ; do
    echo "There was an error. Try again."
  done""")


  ### Installing rtorrent ###
  print '\nINSTALLING RTORRENT\n...............'
  time.sleep(1.5)
  rtorrent_install = """
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


echo "INSTALLING PREREQS"
sudo apt-get install subversion build-essential automake libtool libcppunit-dev libcurl4-openssl-dev libsigc++-2.0-dev unzip unrar curl libncurses-dev -y
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

echo "ENTER RUTORRENT PASSWORD FOR """ + userName + """"
while !(htpasswd -c /var/www/rutorrent/.htpasswd """ + userName + """) ; do
  echo "There was an error. Try again."
done


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
sleep 2
service rtorrentd start
"""
  runBash(rtorrent_install)
  
  rtorrent_update = """
#!/bin/bash

updated="no"

xmlrpc_c_path="/root/rtorrent/install/xmlrpc-c"
libtorrent_path="/root/rtorrent/install/libtorrent"
rtorrent_path="/root/rtorrent/install/rtorrent"
rutorrent_path="/var/www/rutorrent"
plugins_path="/var/www/rutorrent/plugins"

xmlrpc_c_svn="http://xmlrpc-c.svn.sourceforge.net/svnroot/xmlrpc-c/advanced"
libtorrent_svn="svn://rakshasa.no/libtorrent/trunk/libtorrent"
rtorrent_svn="svn://rakshasa.no/libtorrent/trunk/rtorrent"
rutorrent_svn="http://rutorrent.googlecode.com/svn/trunk/rutorrent"
plugins_svn="http://rutorrent.googlecode.com/svn/trunk/plugins"


echo -e "UPDATING xmlrpc-c"
cd $xmlrpc_c_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $xmlrpc_c_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] ; then
  service rtorrentd stop
  svn up
  ./configure
  make
  make install
  echo -e "xmlrpc-c updated from $oldsvn to $newsvn\\n"
  sleep 2
  updated="yes"
else
  echo -e "xmlrpc-c is already at the latest version: $newsvn\\n"
  sleep 2
fi


echo -e "UPDATING libtorrent"
cd $libtorrent_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $libtorrent_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] ; then
  service rtorrentd stop
  svn up
  ./autogen.sh
  ./configure
  make
  make install
  echo -e "libtorrent updated from $oldsvn to $newsvn\\n"
  sleep 2
  updated="yes"
else
  echo -e "libtorrent is already at the latest version: $newsvn\\n"
  sleep 2
fi


echo -e "UPDATING rtorrent"
cd $rtorrent_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $rtorrent_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] || [ "$updated" == "yes" ] ; then
  service rtorrentd stop
  svn up
  ./autogen.sh
  ./configure --with-xmlrpc-c
  make
  make install
  ldconfig
  if [ "$newsvn" != "$oldsvn" ] ; then
    echo -e "rtorrent updated from $oldsvn to $newsvn\\n"
    sleep 2
  else
    echo -e "rtorrent was recompiled and is at version $newsvn\\n"
    sleep 2
  fi
  updated="yes"
else
  echo -e "rtorrent is already at the latest version: $newsvn\\n"
  sleep 2
fi


echo -e "UPDATING rutorrent"
cd $rutorrent_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $rutorrent_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] ; then
  service rtorrentd stop
  svn up
  echo -e "rutorrent updated from $oldsvn to $newsvn\\n"
  sleep 2
  updated="yes"
else
  echo -e "rutorrent is already at the latest version: $newsvn\\n"
  sleep 2
fi


echo -e "UPDATING plugins"
cd $plugins_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $plugins_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] ; then
  service rtorrentd stop
  svn up
  echo -e "plugins updated from $oldsvn to $newsvn\\n"
  sleep 2
  updated="yes"
else
  echo -e "plugins is already at the latest version: $newsvn\\n"
  sleep 2
fi


if [ "$updated" == "yes" ] ; then
  echo -e "Updates were installed. Restarting rtorrent..."
  service rtorrentd stop
  service apache2 restart
  service rtorrentd start
else
  echo -e "Already running the latest version of everything!\\n"
fi
"""
  f = open('/usr/local/bin/rtorrent_update', 'w')
  f.write(rtorrent_update)
  f.close()
  os.chmod('/usr/local/bin/rtorrent_update', 0755)


  ### Print summary and reboot ###
  print '\nNAS configured successfully:'
  time.sleep(1.5)
  print '\n  raid 5 device /dev/md0 created with drives:'
  for raid_drive in raid_drives:
    print '    ' + raid_drive
  time.sleep(1)
  pvSize = re.search(r'[\d.]+ \w+', saveBash('pvdisplay | grep "PV Size"')).group()
  print '\n  Physical Volume of size', pvSize, 'created on /dev/md0'
  time.sleep(1)
  vgSize = re.search(r'[\d.]+ \w+', saveBash('vgdisplay | grep "VG Size"')).group()
  print '\n  Volume Group vg of size', vgSize, 'created on Physical Volume'
  time.sleep(1)
  lvSize = re.search(r'[\d.]+ \w+', saveBash('lvdisplay | grep "LV Size"')).group()
  print '\n  Logical Volume vol1 of size', lvSize, 'created on vg'
  time.sleep(1)
  xfsSize = re.search(r'[\d.]+\w+', saveBash('df -h | grep "/dev/mapper/vg-vol1"')).group()
  print '\n  XFS filesystem of size', xfsSize, 'created on vol1 and mounted on /mnt/vg/vol1'
  time.sleep(1)
  smbSize = re.findall(r'[\d.]+\w+', saveBash('df -h /mnt/vg/vol1/data/'))[2]
  print '\n  Samba share "data" created on XFS filesystem and has', smbSize, 'available'
  time.sleep(1)
  print '\n  Samba user', userName, 'created to access the share'
  time.sleep(1)
  print '\n  Email address', email, 'configured to monitor the raid and a test email was sent'
  time.sleep(1)
  ipaddr = saveBash('ifconfig').split("\n")[1].split()[1][5:]
  print '\n  rtorrent installed with svn repositories in /root/rtorrent/install.'
  print '  rutorrent installed with svn repositories in /var/www'
  print '  Control the rtorrent service with "service rtorrentd start|stop|restart"'
  print '  Access the rutorrent interface at http://' + ipaddr + '/rutorrent with username ' + userName
  print '  Upaate all rtorrent files with "rtorrent_update" in /usr/local/bin'
  time.sleep(1)
  print '\nProcess complete!'
  
  reboot = raw_input('Reboot now? y/n\n')
  if reboot == 'y':
    runBash('reboot now')


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
  main()
