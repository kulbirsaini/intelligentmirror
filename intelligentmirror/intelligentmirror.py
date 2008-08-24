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
from xmlrpclib import ServerProxy
from SimpleXMLRPCServer import SimpleXMLRPCServer

# To modify configuration parameters, see /etc/intelligentmirror.conf .
# Read config file using Yum's config parsers.
mainconf = readMainConfig(readStartupConfig('/etc/intelligentmirror.conf', '/'))
#mainconf = readMainConfig(readStartupConfig('/home2/Studies/project/btp/Yum/intelligentmirror/intelligentmirror_sysconf.conf', '/'))

# Global hard coded variables
rpm_files = ['.rpm']
deb_files = ['.deb']
redirect = '303'
format = '%-12s %s'

# Global variables from config file.
base_dir = mainconf.base_dir
temp_dir = base_dir + '/' + mainconf.temp_dir
cache_host =  mainconf.cache_host
rpc_host = mainconf.rpc_host
rpc_port = int(mainconf.rpc_port)
logfile = mainconf.logfile
proxy = mainconf.proxy
proxy_username = mainconf.proxy_username
proxy_password = mainconf.proxy_password

# RPM related variables.
enable_rpm_cache = int(mainconf.enable_rpm_cache)
rpm_cache_dir = base_dir + '/' + mainconf.rpm_cache_dir
rpm_cache_size = int(mainconf.rpm_cache_size)
max_rpm_size = int(mainconf.max_rpm_size)
min_rpm_size = int(mainconf.min_rpm_size)

# Deb related variables.
enable_deb_cache = int(mainconf.enable_deb_cache)
deb_cache_dir = base_dir + '/' + mainconf.deb_cache_dir
deb_cache_size = int(mainconf.deb_cache_size)
max_deb_size = int(mainconf.max_deb_size)
min_deb_size = int(mainconf.min_deb_size)

def set_proxy():
    if proxy_username and proxy_password:
        proxy_parts = urlparse.urlsplit(proxy)
        new_proxy = '%s://%s:%s@%s/' % (proxy_parts[0], proxy_username, proxy_password, proxy_parts[1])
    else:
        new_proxy = proxy
    return urlgrabber.grabber.URLGrabber(proxies = {'http': new_proxy, 'https': new_proxy, 'ftp': new_proxy})

def set_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filename=logfile,
                        filemode='a')
    return logging.info

grabber = set_proxy()
log = set_logging()

class Bucket:
    """
    This class is for sharing the current packages being downloading
    across various instances of intelligentmirror via XMLRPC.
    """
    def __init__(self, packages = []):
        self.packages = packages
        pass

    def get(self):
        return self.packages

    def set(self, packages):
        self.packages = packages
        return self.packages

    def add(self, package):
        if package not in self.packages:
            self.packages.append(package)
        return self.packages

    def remove(self, package):
        if package in self.packages:
            self.packages.remove(package)
        return self.packages

# If XMLRPCServer is running already, don't start it again
try:
    bucket = ServerProxy('http://' + rpc_host + ':' + str(rpc_port))
    list = bucket.get()
except:
    server = SimpleXMLRPCServer((rpc_host, rpc_port))
    server.register_instance(Bucket())
    log(format%('XMLRPCServer', 'Starting XMLRPCServer on port ' + str(rpc_port) + '.'))
    server.serve_forever()

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

def dir_size(dir):
    """
    This is not a standard function to calculate the size of a directory.
    This function will only give the sum of sizes of all the files in 'dir'.
    """
    # Initialize with 4096bytes as the size of an empty dir is 4096bytes.
    size = 4096
    try:
        for file in os.listdir(dir):
            size += int(os.stat(dir + '/' + file)[6])
    except:
        return -1
    return size / (1024*1024)

def download_from_source(url, path, mode, max_size, min_size):
    """This function downloads the file from remote source and caches it."""
    try:
        remote_file = grabber.urlopen(url)
        remote_size = int(remote_file.info().getheader('content-length')) / 1024
        remote_file.close()
    except urlgrabber.grabber.URLGrabError, e:
        log(format%('URL_ERROR', os.path.basename(path) + ' : Could not retrieve size of remote package.'))
        return

    if max_size and remote_size > max_size:
        return
    if min_size and remote_size < min_size:
        return

    try:
        download_path = os.path.join(temp_dir, md5.md5(os.path.basename(path)).hexdigest())
        open(download_path, 'a').close()
        file = grabber.urlgrab(url, download_path)
        os.rename(file, path)
        os.chmod(path, mode)
        log(format%('DOWNLOAD', os.path.basename(path) + ' : Package was downloaded and cached.'))
    except:
        log(format%('DELETE_TEMP', os.path.basename(download_path) + ' : An error occured while downloading. Temporary file was deleted.'))
        os.unlink(download_path)
    return

def yum_part(url, query, type):
    """This function check whether a package is in cache or not. If not, it
    fetches it from the remote source and cache it and also streams it the client."""
    # The expected mode of the cached file, so that it is readable by apache
    # to stream it to the client.
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    if type == 'rpm':
        path = rpm_cache_dir + '/' + query
        max_size = max_rpm_size
        min_size = min_rpm_size
    elif type == 'deb':
        path = deb_cache_dir + '/' + query
        max_size = max_deb_size
        min_size = min_deb_size

    if os.path.isfile(path):
        log(format%('CACHE_HIT', os.path.basename(path) + ' : Requested package was found in cache.'))
        cur_mode = os.stat(path)[stat.ST_MODE]
        if stat.S_IMODE(cur_mode) == mode:
            log(format%('CACHE_SERVE', os.path.basename(path) + ' : Package was served from cache.'))
            return redirect + ':http://' + cache_host + '/intelligentmirror/' + type + '/' + query
    elif os.path.isfile(os.path.join(temp_dir, md5.md5(query).hexdigest())):
        log(format%('INCOMPLETE', os.path.basename(path) + ' : Package is still being downloaded.'))
        # File is still being downloaded
        return ''
    else:
        log(format%('CACHE_MISS', os.path.basename(path) + ' : Requested package was not found in cache.'))
        forked = fork(download_from_source)
        forked(url, path, mode, max_size, min_size)

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
        if url[0].find(cache_host) > -1:
            log(format%('URL_IGNORE', 'Already a URL from cache.'))
            pass
        else:
            if enable_rpm_cache and (rpm_cache_size == 0 or dir_size(rpm_cache_dir) < rpm_cache_size):
                for file in rpm_files:
                    if query.endswith(file):
                        # This signifies that URL is a rpm package
                        md5id = md5.md5(query).hexdigest()
                        packages = bucket.get()
                        if md5id in packages:
                            break
                        else:
                            bucket.add(md5id)
                        log(format%('URL_HIT', url[0]))
                        new_url = yum_part(url[0], query, 'rpm') + new_url
                        log(format%('NEW_URL', new_url.strip('\n')))
                        bucket.remove(md5id)
                        break
            if enable_deb_cache and (deb_cache_size == 0 or dir_size(deb_cache_dir) < deb_cache_size):
                for file in deb_files:
                    if query.endswith(file):
                        # This signifies that URL is a deb package
                        md5id = md5.md5(query).hexdigest()
                        packages = bucket.get()
                        if md5id in packages:
                            break
                        else:
                            bucket.add(md5id)
                        log(format%('URL_HIT', url[0]))
                        new_url = yum_part(url[0], query, 'deb') + new_url
                        log(format%('NEW_URL', new_url.strip('\n')))
                        bucket.remove(md5id)
                        break
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
        if url[0].find(cache_host) > -1:
            log(format%('URL_IGNORE', 'Already a URL from cache.'))
            pass
        else:
            if enable_rpm_cache and (rpm_cache_size == 0 or dir_size(rpm_cache_dir) < rpm_cache_size):
                for file in rpm_files:
                    if query.endswith(file):
                        # This signifies that URL is a rpm package
                        md5id = md5.md5(query).hexdigest()
                        packages = bucket.get()
                        if md5id in packages:
                            break
                        else:
                            bucket.add(md5id)
                        log(format%('URL_HIT', url[0]))
                        new_url = yum_part(url[0], query, 'rpm') + new_url
                        log(format%('NEW_URL', new_url.strip('\n')))
                        bucket.remove(md5id)
                        break
            if enable_deb_cache and (deb_cache_size == 0 or dir_size(deb_cache_dir) < deb_cache_size):
                for file in deb_files:
                    if query.endswith(file):
                        # This signifies that URL is a deb package
                        md5id = md5.md5(query).hexdigest()
                        packages = bucket.get()
                        if md5id in packages:
                            break
                        else:
                            bucket.add(md5id)
                        log(format%('URL_HIT', url[0]))
                        new_url = yum_part(url[0], query, 'deb') + new_url
                        log(format%('NEW_URL', new_url.strip('\n')))
                        bucket.remove(md5id)
                        break
        print 'new url:', new_url,
        break

if __name__ == '__main__':
    # For testing on command line, use this function
    cmd_squid_part()
    # For testing with squid, use this function
    #squid_part()
