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
  echo -e "xmlrpc-c updated from $oldsvn to $newsvn\n"
  sleep 2
  updated="yes"
else
  echo -e "xmlrpc-c is already at the latest version: $newsvn\n"
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
  echo -e "libtorrent updated from $oldsvn to $newsvn\n"
  sleep 2
  updated="yes"
else
  echo -e "libtorrent is already at the latest version: $newsvn\n"
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
    echo -e "rtorrent updated from $oldsvn to $newsvn\n"
    sleep 2
  else
    echo -e "rtorrent was recompiled and is at version $newsvn\n"
    sleep 2
  fi
  updated="yes"
else
  echo -e "rtorrent is already at the latest version: $newsvn\n"
  sleep 2
fi


echo -e "UPDATING rutorrent"
cd $rutorrent_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $rutorrent_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] ; then
  service rtorrentd stop
  svn up
  echo -e "rutorrent updated from $oldsvn to $newsvn\n"
  sleep 2
  updated="yes"
else
  echo -e "rutorrent is already at the latest version: $newsvn\n"
  sleep 2
fi


echo -e "UPDATING plugins"
cd $plugins_path
oldsvn=$(svn info | grep "Revision" | cut -c11-)
newsvn=$(svn info $plugins_svn | grep "Revision" | cut -c11-)
if [ "$newsvn" != "$oldsvn" ] ; then
  service rtorrentd stop
  svn up
  echo -e "plugins updated from $oldsvn to $newsvn\n"
  sleep 2
  updated="yes"
else
  echo -e "plugins is already at the latest version: $newsvn\n"
  sleep 2
fi


if [ "$updated" == "yes" ] ; then
  echo -e "Updates were installed. Restarting rtorrent..."
  service rtorrentd stop
  service apache2 restart
  service rtorrentd start
else
  echo -e "Already running the latest version of everything!\n"
fi
