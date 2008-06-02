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

def log(str):
    """Write a string to the logfile."""
    file = open(logfile, 'a')
    file.write(str)
    file.close()
    return

def download_from_source(url, path, mode):
    """This function downloads the file from remote source and caches it."""
    file = urlgrabber.urlgrab(url, path)
    os.chmod(file, mode)
    log(time.ctime() + ' : ' + 'DOWNLOAD Package was downloaded and cached.\n')
    return

def yum_part(url, query):
    """This function check whether a package is in cache or not. If not, it fetches it from the remote source and cache it and also streams it the client."""
    # The expected mode of the cached file, so that it is readable by apache
    # to stream it to the client.
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    path = cache_dir + query
    if os.path.isfile(path):
        log(time.ctime() + ' : ' + 'CACHE_HIT Requested package was found in cache.\n')
        modified_time = os.stat(path).st_mtime
        remote_file = urlgrabber.urlopen(url)
        remote_time = rfc822.mktime_tz(remote_file.info().getdate_tz('last-modified'))
        remote_file.close()
        if remote_time > modified_time:
            log(time.ctime() + ' : ' + 'REFRESH_MISS Requested package was older.\n')
            # If remote file is newer, delete the local file from cache and cache the new one
            os.unlink(path)
            download_from_source(url, path, mode)
            return redirect + ':' + cache_url + query
        cur_mode = os.stat(path)[stat.ST_MODE]
        if stat.S_IMODE(cur_mode) == mode:
            log(time.ctime() + ' : ' + 'REFRESH_HIT Requested package was uptodate.\n')
            return redirect + ':' + cache_url + query
    else:
        try:
            log(time.ctime() + ' : ' + 'CACHE_MISS Requested package was found in cache.\n')
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
        log(time.ctime() + ' : ' + '=== BEGIN request for ' + url[0] + ' ===\n')
        # Retrieve the basename from the request url
        path = urlparse.urlsplit(url[0])[2]
        query = os.path.basename(path)
        # If requested url is already a cache url, no need to check.
        # DONT REMOVE THIS CHECK, OTHERWISE IT WILL RESULT IN INFINITE LOOP.
        if url[0].startswith(cache_url):
            log(time.ctime() + ' : ' + 'URL_IGNORE Already a URL from cache.\n')
            pass
        else:
            for file in relevant_files:
                if query.endswith(file):
                    # This signifies that URL is a rpm package
                    log(time.ctime() + ' : ' + 'URL_HIT Requested URL is of interest.\n')
                    new_url = yum_part(url[0], query) + new_url
                    break
            else:
                log(time.ctime() + ' : ' + 'URL_MISS Requested URL is of no interest.\n')
                pass
        # Flush the new url to stdout for squid to process
        log(time.ctime() + ' : ' + '=== END request for ' + url[0] + ' ===\n')
        sys.stdout.write(new_url)
        sys.stdout.flush()

def cmd_squid_part():
    """This function will tap requests from squid. If the request is for rpm packages, they will be forwarded to function yum_part() for further processing. Finally this function will flush a cache url if package found in cache or a blank line in case on a miss to stdout. This is the only function where we deal with squid, rest of the program/project doesn't interact with squid at all."""
    while True:
        url = sys.argv[1].split(' ')
        new_url = '\n';
        log(time.ctime() + ' : ' + '=== BEGIN request for ' + url[0] + ' ===\n')
        path = urlparse.urlsplit(url[0])[2]
        query = os.path.basename(path)
        # If requested url is already a cache url, no need to screw things.
        if url[0].startswith(cache_url):
            log(time.ctime() + ' : ' + 'URL_IGNORE Already a URL from cache.\n')
            pass
        else:
            for file in relevant_files:
                if query.endswith(file):
                    log(time.ctime() + ' : ' + 'URL_HIT Requested URL is of interest.\n')
                    new_url = yum_part(url[0], query) + new_url
                    break
            else:
                log(time.ctime() + ' : ' + 'URL_MISS Requested URL is of no interest.\n')
                pass
        log(time.ctime() + ' : ' + '=== END request for ' + url[0] + ' ===\n')
        print 'new url:', new_url
        break

if __name__ == '__main__':
    # For testing on command line, use this function
    cmd_squid_part()
    # For testing with squid, use this function
    # squid_part()
