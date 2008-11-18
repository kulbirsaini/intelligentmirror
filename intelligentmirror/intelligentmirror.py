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

__author__ = """Kulbir Saini <kulbirsaini@students.iiit.ac.in>"""
__docformat__ = 'plaintext'

from config import readMainConfig, readStartupConfig
import logging
import logging.handlers
import os
import random
import stat
import sys
import threading
import time
import urlgrabber
import urlparse
from xmlrpclib import ServerProxy
from SimpleXMLRPCServer import SimpleXMLRPCServer

# To modify configuration parameters, see /etc/intelligentmirror.conf .
# Read config file using Yum's config parsers.
mainconf = readMainConfig(readStartupConfig('/etc/intelligentmirror.conf', '/'))

# Global Options
base_dir = mainconf.base_dir
temp_dir = os.path.join(base_dir, mainconf.temp_dir)
max_parallel_downloads = int(mainconf.max_parallel_downloads)
cache_host =  mainconf.cache_host
rpc_host = mainconf.rpc_host
rpc_port = int(mainconf.rpc_port)
logfile = mainconf.logfile
max_logfile_size = int(mainconf.max_logfile_size) * 1024 * 1024
max_logfile_backups = int(mainconf.max_logfile_backups)
proxy = mainconf.proxy
proxy_username = mainconf.proxy_username
proxy_password = mainconf.proxy_password

BASE_PLUGIN = 0
XMLRPC_SERVER = 1
DOWNLOAD_SCHEDULER = 2
rpm_files = ['.rpm']
deb_files = ['.deb']
redirect = '303'
format = '%s %s %s %s %s'
cache_url = 'http://' + str(cache_host) + '/' 


# RPM related variables.
enable_rpm_cache = int(mainconf.enable_rpm_cache)
rpm_cache_dir = os.path.join(base_dir, mainconf.rpm_cache_dir)
rpm_cache_size = int(mainconf.rpm_cache_size)
max_rpm_size = int(mainconf.max_rpm_size)
min_rpm_size = int(mainconf.min_rpm_size)

# Deb related variables.
enable_deb_cache = int(mainconf.enable_deb_cache)
deb_cache_dir = os.path.join(base_dir, mainconf.deb_cache_dir)
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

def dir_size(dir):
    """
    This is not a standard function to calculate the size of a directory.
    This function will only give the sum of sizes of all the files in 'dir'.
    """
    # Initialize with 4096bytes as the size of an empty dir is 4096bytes.
    size = 4096
    try:
        for file in os.listdir(dir):
            size += int(os.stat(os.path.join(dir, file))[6])
    except:
        return -1
    return size / (1024*1024)

class PackagePool:
    """
    This class is for sharing the current packages being downloading
    across various instances of intelligentmirror via XMLRPC.
    """
    def __init__(self):
        self.scores = {}
        self.queue = {}
        self.active = []
        pass

    # Functions related to package queue-ing.
    def add(self, package, score = 1):
        """Queue a package for download. Score defaults to one."""
        if package not in self.queue.keys():
            self.queue[package] = []
        self.scores[package] = score
        return True

    def set(self, package, values):
        """Set the details of package to values."""
        self.queue[package] = values
        return True

    def set_score(self, package, score = 1):
        """Set the priority score of a package."""
        self.scores[package] = score
        return True

    def inc_score(self, package, incr = 1):
        """Increase the priority score of package represented by 'package'."""
        if package in self.scores.keys():
            self.scores[package] += incr
        return True

    def get(self):
        """Return all the packages currently in queue."""
        return self.queue.keys()

    def get_details(self, package):
        """Return the details of a particular package represented by 'package'."""
        if package in self.queue.keys():
            return self.queue[package]
        return False

    def get_popular(self):
        """Return the most frequently accessed package."""
        vk = [(v,k) for k,v in self.scores.items()]
        if len(vk) != 0:
            package = sorted(vk, reverse=True)[0][1]
            return package
        return "NULL"

    def remove(self, package):
        """Dequeue a package from the download queue."""
        if package in self.queue.keys():
            self.queue.pop(package)
        if package in self.scores.keys():
            self.scores.pop(package)
        return True

    def flush(self):
        """Flush the queue and reinitialize everything."""
        self.queue = {}
        self.scores = {}
        self.active = []
        return True

    # Functions related download scheduling.
    # Have to mess up things in single class because python
    # XMLRPCServer doesn't allow to register multiple instances
    # via register_instance
    def add_conn(self, package):
        """Add package to active connections list."""
        if package not in self.active:
            self.active.append(package)
        return True

    def get_conn(self):
        """Return a list of currently active connections."""
        return self.active

    def get_conn_number(self):
        """Return the number of currently active connections."""
        return len(self.active)

    def is_active(self, package):
        """Returns whether a connection is active or not."""
        if package in self.active:
            return True
        return False

    def remove_conn(self, package):
        """Remove package from active connections list."""
        if package in self.active:
            self.active.remove(package)
        return True


def remove(package):
    """Remove package from queue."""
    package_pool.remove(package)
    package_pool.remove_conn(package)
    return

def queue(package, values):
    """Queue package for scheduling later by download_scheduler."""
    package_pool.set(package, values)
    return

def fork(f):
    """Generator for creating a forked process
    from a function"""
    # Perform double fork
    r = ''
    if os.fork(): # Parent
        # Wait for children so that they don't get defunct.
        os.wait()
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

def download_from_source(args):
    """This function downloads the file from remote source and caches it."""
    client = args[0]
    url = args[1]
    path = args[2]
    mode = args[3]
    package = args[4]
    type = args[5]
    max_size = args[6]
    min_size = args[7]
    if max_size or min_size:
        try:
            log(format%(client, package, 'GET_SIZE', type, 'Trying to get the size of the package.'))
            remote_file = grabber.urlopen(url)
            remote_size = int(remote_file.info().getheader('content-length')) / 1024
            remote_file.close()
            log(format%(client, package, 'GOT_SIZE', type, 'Successfully retrieved the size of the package.'))
        except urlgrabber.grabber.URLGrabError, e:
            remove(package)
            log(format%(client, package, 'SIZE_ERR', type, 'Could not retrieve size of the package.'))
            return

        if max_size and remote_size > max_size:
            remove(package)
            log(format%(client, package, 'MAX_SIZE', type, 'Package size ' + str(remote_size) + ' is larger than maximum allowed.'))
            return
        if min_size and remote_size < min_size:
            remove(package)
            log(format%(client, package, 'MIN_SIZE', type, 'Package size ' + str(remote_size) + ' is smaller than minimum allowed.'))
            return

    try:
        download_path = os.path.join(temp_dir, os.path.basename(path))
        open(download_path, 'a').close()
        file = grabber.urlgrab(url, download_path)
        os.rename(file, path)
        os.chmod(path, mode)
        remove(package)
        size = os.stat(path)[6]
        log(format%(client, package, 'DOWNLOAD', type, str(size) + ' Package was downloaded and cached.'))
    except urlgrabber.grabber.URLGrabError, e:
        remove(package)
        log(format%(client, package, 'DOWNLOAD_ERR', type, 'An error occured while retrieving the package.'))
        os.unlink(download_path)

    return

def cache_package(client, url, type, package):
    """This function check whether a package is in cache or not. If not, it fetches
    it from the remote source and cache it and also streams it to the client."""
    # The expected mode of the cached file, so that it is readable by apache
    # to stream it to the client.
    global cache_url
    mode = 0755
    if type == 'RPM':
        params = urlparse.urlsplit(url)[3]
        path = os.path.join(rpm_cache_dir, package)
        cached_url = os.path.join(cache_url, base_dir.strip('/').split('/')[-1], type.lower())
        max_size = max_rpm_size
        min_size = min_rpm_size
        cache_size = rpm_cache_size
        cache_dir = rpm_cache_dir

    if type == 'DEB':
        params = urlparse.urlsplit(url)[3]
        path = os.path.join(deb_cache_dir, package)
        cached_url = os.path.join(cache_url, base_dir.strip('/').split('/')[-1], type.lower())
        max_size = max_deb_size
        min_size = min_deb_size
        cache_size = deb_cache_size
        cache_dir = deb_cache_dir

    if os.path.isfile(path):
        log(format%(client, package, 'CACHE_HIT', type, 'Requested package was found in cache.'))
        remove(package)
        log(format%(client, package, 'CACHE_SERVE', type, 'Package was served from cache.'))
        return redirect + ':' + os.path.join(cached_url, package)
    elif cache_size == 0 or dir_size(cache_dir) < cache_size:
        log(format%(client, package, 'CACHE_MISS', type, 'Requested package was not found in cache.'))
        queue(package, [client, url, path, mode, package, type, max_size, min_size])
    else:
        log(format%(client, package, 'CACHE_FULL', type, 'Cache directory \'' + cache_dir + '\' has exceeded the maximum size allowed.'))

    return url

def squid_part():
    """This function will tap requests from squid. If the request is for a rpm/deb
    package, they will be forwarded to function cache_package() for further processing.
    Finally this function will flush a cache_url if package found in cache or a
    blank line in case on a miss to stdout. This is the only function where we deal
    with squid, rest of the program/project doesn't interact with squid at all."""
    while True:
        try:
            # Read url from stdin ( this is provided by squid)
            url = sys.stdin.readline().strip().split(' ')
            new_url = url[0];
            # Retrieve the basename from the request url
            fragments = urlparse.urlsplit(url[0])
            host = fragments[1]
            path = fragments[2]
            params = fragments[3]
            client = url[1].split('/')[0]
            log(format%(client, '-', 'REQUEST', '-', url[0]))
        except IndexError, e:
            log(format%('-', '-', 'RELOAD', '-', 'IntelligentMirror plugin was reloaded.'))

        # rpm caching is handled here.
        try:
            if enable_rpm_cache and host.find(cache_host) < 0:
                for file in rpm_files:
                    if path.endswith(file):
                        # This signifies that URL is a rpm package
                        package = os.path.basename(path)
                        type = 'RPM'
                        packages = package_pool.get()
                        if package in packages:
                            package_pool.inc_score(package)
                            pass
                        else:
                            package_pool.add(package)
                            log(format%(client, package, 'URL_HIT', type, url[0]))
                            new_url = cache_package(client, url[0], type, package)
                            log(format%(client, package, 'NEW_URL', type, new_url))
        except:
            log(format%(client, '-', 'NEW_URL', 'RPM', 'Error in parsing the url ' + new_url))

        # deb caching is handled here.
        try:
            if enable_deb_cache and host.find(cache_host) < 0:
                for file in deb_files:
                    if path.endswith(file):
                        # This signifies that URL is a deb package
                        package = os.path.basename(path)
                        type = 'DEB'
                        packages = package_pool.get()
                        if package in packages:
                            package_pool.inc_score(package)
                            pass
                        else:
                            package_pool.add(package)
                            log(format%(client, package, 'URL_HIT', type, url[0]))
                            new_url = cache_package(client, url[0], type, package)
                            log(format%(client, package, 'NEW_URL', type, new_url))
        except:
            log(format%(client, '-', 'NEW_URL', 'DEB', 'Error in parsing the url ' + new_url))

        # Flush the new url to stdout for squid to process
        try:
            sys.stdout.write(new_url + '\n')
            sys.stdout.flush()
        except IOError, e:
            if e.errno == 32:
                os.kill(os.getpid(), 1)

def start_xmlrpc_server():
    """Starts the XMLRPC server in a threaded process."""
    try:
        server = SimpleXMLRPCServer((rpc_host, rpc_port), logRequests=0)
        server.register_instance(PackagePool())
        log(format%('-', '-', 'XMLRPCSERVER', '-', 'Starting XMLRPCServer on port ' + str(rpc_port) + '.'))
        # Rotate logfiles if the size is more than the max_logfile_size.
        if os.stat(logfile)[6] > max_logfile_size:
            roll = logging.handlers.RotatingFileHandler(filename=logfile, mode='r', maxBytes=max_logfile_size, backupCount=max_logfile_backups)
            roll.doRollover()
        server.serve_forever()
    except:
        pass

def download_scheduler():
    """Schedule packages from download queue for downloading."""
    log(format%('-', '-', 'SCHEDULEDER', '-', 'Download Scheduler starting.'))
    time.sleep(3)
    package_pool = ServerProxy('http://' + rpc_host + ':' + str(rpc_port))
    while True:
        if package_pool.get_conn_number() < max_parallel_downloads:
            #log(format%(str(package_pool.get_conn_number()), '-', 'CONN_AVAIL', '-', '-'))
            package = package_pool.get_popular()
            if package != "NULL" and package_pool.is_active(package) == False:
                #log(format%('-', '-', 'INACTIVE', '-', '-'))
                params = package_pool.get_details(package)
                if params != False:
                    package_pool.set_score(package, 0)
                    package_pool.add_conn(package)
                    log(format%(params[0], params[4], 'SCHEDULED', params[5], 'Package scheduled for download.'))
                    forked = fork(download_from_source)
                    forked(params)
            if package_pool.is_active(package) == True:
                package_pool.set_score(package, 0)
        time.sleep(3)
    return

class Function_Thread(threading.Thread):
    def __init__(self, fid):
        threading.Thread.__init__(self)
        self.fid = fid
        return

    def run(self):
        if self.fid == XMLRPC_SERVER:
            start_xmlrpc_server()
        elif self.fid == DOWNLOAD_SCHEDULER:
            download_scheduler()
        elif self.fid == BASE_PLUGIN:
            squid_part()
        else:
            return
        return

if __name__ == '__main__':
    global grabber, log, package_pool
    grabber = set_proxy()
    log = set_logging()

    # If XMLRPCServer is running already, don't start it again
    try:
        time.sleep(int(random.random()*100)%10)
        package_pool = ServerProxy('http://' + rpc_host + ':' + str(rpc_port))
        list = package_pool.get()
        # Flush previous values on reload
        package_pool.flush()
        # For testing with squid, use this function
        squid_part()
    except:
        # Start XMLRPC Server, Download Scheduler and Base Plugin in threads.
        thread_xmlrpc = Function_Thread(XMLRPC_SERVER)
        thread_download_scheduler = Function_Thread(DOWNLOAD_SCHEDULER)
        thread_base_plugin = Function_Thread(BASE_PLUGIN)
        thread_xmlrpc.start()
        thread_download_scheduler.start()
        thread_base_plugin.start()
        thread_xmlrpc.join()
        thread_download_scheduler.join()
        thread_base_plugin.join()

