#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# (C) Copyright 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
#

import os
import os.path
import rfc822
import stat
import sys
import time
import urlgrabber
import urlparse

relevant_files = ['.rpm'] #, 'repomd.xml', 'primary.sqlite.bz2', 'primary.xml.gz', 'filelists.sqlite.bz2', 'filelists.xml.gz', 'other.sqlite.bz2', 'other.xml.gz', 'comps.xml', 'updateinfo.xml.gz']

cache_dir = '/var/spool/squid/yum/'
cache_url = 'http://172.17.8.175/yum/'
logfile = '/var/spool/squid/yum/im.log'
redirect = '303'

def download_from_source(url, path, mode):
    """This function downloads the file from remote source and caches it."""
    file = urlgrabber.urlgrab(url, path)
    os.chmod(file, mode)
    return

def yum_part(url, query):
    """This function check whether a package is in cache or not. If not, it fetches it from the remote source and cache it and also streams it the client."""
    # The expected mode of the cached file, so that it is readable by apache
    # to stream it to the client.
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    path = cache_dir + query
    if os.path.isfile(path):
        cur_mode = os.stat(path)[stat.ST_MODE]
        if stat.S_IMODE(cur_mode) == mode:
            return redirect + ':' + cache_url + query
    else:
        try:
            download_from_source(url, path, mode)
            return redirect + ':' + cache_url + query
        except:
            pass
    return url

def squid_part():
    """This function will tap requests from squid. If the request is for rpm packages, they will be forwarded to function yum_part() for further processing. Finally this function will flush a cache url if package found in cache or a blank line in case on a miss to stdout. This is the only function where we deal with squid, rest of the program/project doesn't interact with squid at all."""
    while True:
        # Read url from stdin ( this is provided by squid)
        url = sys.stdin.readline().strip().split(' ')
        new_url = '\n';
        # Retrieve the basename from the request url
        path = urlparse.urlsplit(url[0])[2]
        query = os.path.basename(path)
        # If requested url is already a cache url, no need to check.
        # DONT REMOVE THIS CHECK, OTHERWISE IT WILL RESULT IN INFINITE LOOP.
        if url[0].startswith(cache_url):
            pass
        else:
            for file in relevant_files:
                if query.endswith(file):
                    # This signifies that URL is a rpm package
                    new_url = yum_part(url[0], query) + new_url
                    break
            else:
                pass
        # Flush the new url to stdout for squid to process
        sys.stdout.write(new_url)
        sys.stdout.flush()

if __name__ == '__main__':
    squid_part()
