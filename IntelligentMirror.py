#!/usr/bin/env python

import os
import os.path
import stat
import sys
import urlparse
import urlgrabber

relevant_files = ['.rpm'] #, 'repomd.xml', 'primary.sqlite.bz2', 'primary.xml.gz', 'filelists.sqlite.bz2', 'filelists.xml.gz', 'other.sqlite.bz2', 'other.xml.gz', 'comps.xml', 'updateinfo.xml.gz']

cache_dir = '/var/spool/squid/yum/'
cache_url = 'http://172.17.8.175/yum/'
redirect = '303'

def yum_part(url, query):
    # do the non-squid part here
    path = cache_dir + query
    req_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    if os.path.isfile(path):
        mode = os.stat(path)[stat.ST_MODE]
        if stat.S_IMODE(mode) == req_mode:
            #print "Cache Hit"
            return redirect + ':' + cache_url + query
    else:
        #print "Cache Miss"
        try:
            file = urlgrabber.urlgrab(url, path)
            os.chmod(file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            return redirect + ':' + cache_url + query
        except:
            pass
    return url

def squid_part():
    # do the squid part here
    while True:
        url = sys.stdin.readline().strip().split(' ')
        #url = sys.argv[1].split(' ')
        new_url = '\n';
        path = urlparse.urlsplit(url[0])[2]
        query = os.path.basename(path)
        #print path, ',', query
        # If requested url is already a cache url, no need to screw things.
        if url[0].startswith(cache_url):
            pass
        else:
            for file in relevant_files:
                if query.endswith(file):
                    #print "URL Hit"
                    new_url = yum_part(url[0], query) + new_url
                    break
            else:
                pass
                #print "URL Miss"
        #print 'new url:', new_url
        #break
        sys.stdout.write(new_url)
        sys.stdout.flush()

if __name__ == '__main__':
    squid_part()
