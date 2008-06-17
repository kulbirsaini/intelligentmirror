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

from config import readMainConfig, readStartupConfig
import logging
import md5
import os
import rfc822
import stat
import sys
import time
import urlgrabber
import urlparse

# To modify configuration parameters, see /etc/sysconfig/intelligentmirror.conf .
# Read config file using Yum's config parsers.
mainconf = readMainConfig(readStartupConfig('/etc/sysconfig/intelligentmirror.conf', '/'))

relevant_files = ['.rpm'] #, 'repomd.xml', 'primary.sqlite.bz2', 'primary.xml.gz', 'filelists.sqlite.bz2', 'filelists.xml.gz', 'other.sqlite.bz2', 'other.xml.gz', 'comps.xml', 'updateinfo.xml.gz']

cache_dir = mainconf.cachedir
cache_url = mainconf.cacheurl
temp_dir = mainconf.tempdir
logfile = mainconf.logfile
redirect = '303'
format = '%-12s %s'

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=logfile,
                    filemode='a')
log = logging.info

def fork(f):
    """Generator for creating a forked process
    from a function"""
    # Perform double fork
    r = ''
    if os.fork(): # Parent
        # Return a function
        return  lambda *x, **kw: r 

    # Otherwise, we are the child 
    # Perform second fork
    os.setsid()
    os.umask(077)
    os.chdir('/')
    if os.fork():
        os._exit(0) 

    def wrapper(*args, **kwargs):
        """Wrapper function to be returned from generator.
        Executes the function bound to the generator and then
        exits the process"""
        f(*args, **kwargs)
        os._exit(0)

    return wrapper

def download_from_source(url, path, mode):
    """This function downloads the file from remote source and caches it."""
    download_path = os.path.join(temp_dir, md5.md5(os.path.basename(path)).hexdigest())
    file = urlgrabber.urlgrab(url, download_path)
    os.rename(download_path, path)
    os.chmod(path, mode)
    log(format%('DOWNLOAD', os.path.basename(path) + ': Package was downloaded and cached.'))
    return

def yum_part(url, query):
    """This function check whether a package is in cache or not. If not, it
    fetches it from the remote source and cache it and also streams it the client."""
    # The expected mode of the cached file, so that it is readable by apache
    # to stream it to the client.
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    path = cache_dir + query
    if os.path.isfile(path):
        log(format%('CACHE_HIT', os.path.basename(path) + ': Requested package was found in cache.'))
        try:
            modified_time = os.stat(path).st_mtime
            remote_file = urlgrabber.urlopen(url)
            remote_time = rfc822.mktime_tz(remote_file.info().getdate_tz('last-modified'))
            remote_file.close()
            if remote_time > modified_time:
                log(format%('REFRESH_MISS', os.path.basename(path) + ': Requested package was older.'))
                # If remote file is newer, cache the new one
                forked = fork(download_from_source)
                forked(url, path, mode)
                return ''
            else:
                log(format%('REFRESH_HIT', os.path.basename(path) + ': Cached package was uptodate.'))
        except urlgrabber.grabber.URLGrabError, e:
            log(format%('URL_ERROR', os.path.basename(path) + ': Could not retrieve timestamp for remote package. Trying to serve from cache.'))
            pass

        cur_mode = os.stat(path)[stat.ST_MODE]
        if stat.S_IMODE(cur_mode) == mode:
            log(format%('CACHE_SERVE', os.path.basename(path) + ': Package was served from cache.'))
            return redirect + ':' + cache_url + query
    elif os.path.isfile(os.path.join(temp_dir, md5.md5(query).hexdigest())):
        log(format%('INCOMPLETE', os.path.basename(path) + ': Package is still being downloaded.'))
        # File is still being downloaded
        return ''
    else:
        try:
            log(format%('CACHE_MISS', os.path.basename(path) + ': Requested package was not found in cache.'))
            forked = fork(download_from_source)
            forked(url, path, mode)
            return ''
        except urlgrabber.grabber.URLGrabError, e:
            log(format%('URL_ERROR', os.path.basename(path) + ': An error occured while retrieving the package.'))
            pass
    return ''

def squid_part():
    """This function will tap requests from squid. If the request is for rpm
    packages, they will be forwarded to function yum_part() for further processing.
    Finally this function will flush a cache url if package found in cache or a
    blank line in case on a miss to stdout. This is the only function where we deal
    with squid, rest of the program/project doesn't interact with squid at all."""
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
            log(format%('URL_IGNORE', 'Already a URL from cache.'))
            pass
        else:
            for file in relevant_files:
                if query.endswith(file):
                    # This signifies that URL is a rpm package
                    log(format%('URL_HIT', url[0]))
                    new_url = yum_part(url[0], query) + new_url
                    log(format%('NEW_URL', new_url.strip('\n')))
                    break
            else:
                pass
        # Flush the new url to stdout for squid to process
        sys.stdout.write(new_url)
        sys.stdout.flush()

def cmd_squid_part():
    """This function will tap requests from squid. If the request is for rpm
    packages, they will be forwarded to function yum_part() for further processing.
    Finally this function will flush a cache url if package found in cache or a
    blank line in case on a miss to stdout. This is the only function where we deal
    with squid, rest of the program/project doesn't interact with squid at all."""
    while True:
        url = sys.argv[1].split(' ')
        new_url = '\n';
        path = urlparse.urlsplit(url[0])[2]
        query = os.path.basename(path)
        # If requested url is already a cache url, no need to screw things.
        if url[0].startswith(cache_url):
            log(format%('URL_IGNORE', 'Already a URL from cache.'))
            pass
        else:
            for file in relevant_files:
                if query.endswith(file):
                    log(format%('URL_HIT', url[0]))
                    new_url = yum_part(url[0], query) + new_url
                    log(format%('NEW_URL', new_url.strip('\n')))
                    break
            else:
                log(format%('URL_MISS', 'Requested URL is of no interest.'))
                pass
        print 'new url:', new_url,
        break

if __name__ == '__main__':
    # For testing on command line, use this function
    cmd_squid_part()
    # For testing with squid, use this function
    # squid_part()
