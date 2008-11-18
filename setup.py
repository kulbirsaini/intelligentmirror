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


from intelligentmirror.config import readMainConfig, readStartupConfig
import logging
import logging.handlers
import os
import pwd
import shutil
import sys

# The user which runs the squid proxy server or daemon.
squid_user = 'squid'
# The group which runs the squid proxy server or daemon.
squid_group = 'squid'
# The location of squid configuration directory.
squid_conf_dir = '/etc/squid/'
# The location of directory where squid logs are stored.
squid_log_dir = '/var/log/squid'
# The directory to store application specific configuration files for Apache Web Server.
apache_conf_dir = '/etc/httpd/conf.d/'
# The directory to store man pages.
man_dir = '/usr/share/man/man8/'

# The location of system configuration file for intelligentmirror.
config_file = './intelligentmirror_sysconfig.conf'
# The location of logfile to write setup/install logs.
setup_logfile = './intelligentmirror_setup.log'
# Read the configure file.
mainconf =  readMainConfig(readStartupConfig(config_file, '/'))

# Gloabl Options
base_dir = mainconf.base_dir
temp_dir = os.path.join(base_dir, mainconf.temp_dir)
logfile = mainconf.logfile
format = '%s'

USAGE_ERROR = 1
UID_ERROR = 2
INSTALL_ERROR = 3

# rpm specific options
rpm_cache_dir = os.path.join(base_dir, mainconf.rpm_cache_dir)

# deb specific options
deb_cache_dir = os.path.join(base_dir, mainconf.deb_cache_dir)

# List of cache directories
squid_cache_dir_list = [base_dir, temp_dir, rpm_cache_dir, deb_cache_dir]

def set_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filename=setup_logfile,
                        filemode='w')
    return logging.info

def create_dir(dir, user=None, group=None, mode=0755):
    """Create a directory in the filesystem with user:group ownership and mode as permissions."""
    try:
        os.makedirs(dir, mode)
        log(format%("Created directory " + dir + " ."))
    except:
        log(format%("Could not create directory " + dir + " ."))
        return False

    return dir_perms_and_ownership(dir, user, group, mode)

def dir_perms_and_ownership(dir, user=None, group=None, mode=0755):
    """Change the permissions and ownership of a directory."""
    try:
        os.chmod(dir, mode)
    except:
        log(format%("Could not change permissions of directory " + dir + " ."))

    if user == None:
        return True

    user = pwd.getpwnam(user)[2]
    if group != None:
        group = pwd.getpwnam(group)[3]
    else:
        group = user

    try:
        os.chown(dir, user, group)
        log(format%("Changed ownership of " + dir + " ."))
    except:
        log(format%("Could not change ownership of directory " + dir + " ."))
        return False

    return True

def create_file(filename, user=None, group=None, mode=0755):
    """Create a file in the filesystem with user:group ownership and mode as permissions."""
    try:
        file = open(filename, 'a')
        file.close()
        log(format%("Created file " + filename + " ."))
    except:
        log(format%("Could not create file " + filename + " ."))
        return False
    
    try:
        os.chmod(filename, mode)
        log(format%("Changed mode of file " + filename + " ."))
    except:
        log(format%("Could not change the mode of the file " + filename + " ."))
        return False

    if user == None:
        return True

    user = pwd.getpwnam(user)[2]
    if group != None:
        group = pwd.getpwnam(group)[3]
    else:
        group = user

    try:
        os.chown(filename, user, group)
        log(format%("Changed ownership of file " + filename + " ."))
    except:
        log(format%("Could not change ownership of file " + filename + " ."))
        return False
    return True

def copy_file(source, dest):
    """Copies the source file to dest file."""
    try:
        shutil.copy2(source, dest)
        log(format%("Copied file " + source + " to " + dest + " ."))
    except:
        log(format%("Could not copy the file " + source + " to file " + dest + " ."))
        return False
    return True

def copy_dir(source, dest):
    """Copies the source directory recursively to dest dir."""
    try:
        if os.path.isdir(dest):
            shutil.rmtree(dest)
            log(format%("Removed already existing directory " + dest + " ."))
    except:
        log(format%("Could not remove the already existing destination directory " + dest + " ."))
        return False
    try:
        shutil.copytree(source, dest)
        log(format%("Copied source directory " + source + " to " + dest + " ."))
    except:
        log(format%("Could not copy directory " + source + " to " + dest + " ."))
        return False
    return True

def generate_httpd_conf():
    """Generates /etc/httpd/conf.d/intelligentmirror.conf for apache web server for serving packages."""
    conf_file = os.path.join(apache_conf_dir, 'intelligentmirror.conf')
    intelligentmirror_conf = """
#
# file : """ + conf_file + """
#
# IntelligentMirror is a squid url rewriter to cache rpm/deb packages.
# Check http://fedora.co.in/intelligentmirror/ for more details.
#

# ------------------- Note This --------------------
# Don't forget to reload httpd and squid services if you change this file.

Alias /intelligentmirror """ + base_dir +"""

<Directory """ + base_dir + """>
  Options +Indexes
  Order Allow,Deny
  #Comment the following line and uncomment the next for public use 
  #Deny from all
  Allow from all
</Directory>
    """

    try:
        file = open(conf_file, 'w')
        file.write(intelligentmirror_conf)
        file.close()
        log(format%("Generated config file for Apache webserver in file " + config_file + " ."))
    except:
        log(format%("Could not write config file for apache web server to " + config_file + " ."))
        return False
    return True

def error(error_code):
    """Report error while updating/installing intelligentmirror with proper error code."""
    help_message =  """
Usage: python setup.py install (as root/super user)
Please see http://fedora.co.in/intelligentmirror for more information or getting help.
    """
    install_error =  """
An error has occured while installing intelligentmirror.
Please check intelligentmirror_setup.log for more details.
Please see http://fedora.co.in/intelligentmirror for more information or getting help.
    """
    uid_error = """
You must be root to setup/install intelligentmirror.
Please see http://fedora.co.in/intelligentmirror for more information or getting help.
    """
    if error_code == INSTALL_ERROR:
        print install_error
        sys.exit(error_code)
    if error_code == UID_ERROR:
        print uid_error
        sys.exit(UID_ERROR)
    if error_code == USAGE_ERROR:
        print help_message
        sys.exit(USAGE_ERROR)
    return

def success():
    """Print informative messages after successfull installation."""
    message = """
IntelligentMirror setup has completed successfully.
Now you must reload httpd service on your machine by using the following command
[root@localhost ~]# service httpd reload [ENTER]
Also, you need to configure squid so that it can use intelligentmirror as a url rewritor plugin.
Check README file for further configurations of squid, httpd and intelligentmirror.
In case of any bugs or problems, check http://fedora.co.in/intelligentmirror .
    """
    print message

def setup():
    """Perform the setup."""
    # Create Apache configuration directory.
    if not os.path.isdir(apache_conf_dir):
        if not create_dir(apache_conf_dir):
            error(INSTALL_ERROR)
    else:
        log(format%("Directory " + apache_conf_dir + " already exists."))

    # Create squid configuration directory.
    if not os.path.isdir(squid_conf_dir):
        if not create_dir(squid_conf_dir):
            error(INSTALL_ERROR)
    else:
        log(format%("Directory " + squid_conf_dir + " already exists."))

    # Create squid log directory.
    if not os.path.isdir(squid_log_dir):
        if not create_dir(squid_log_dir, squid_user, squid_group):
            error(INSTALL_ERROR)
    else:
        log(format%("Directory " + squid_log_dir + " already exists."))

    # Create directories for rpm/deb caching.
    for dir in squid_cache_dir_list:
        if not os.path.isdir(dir):
            if not create_dir(dir, squid_user, squid_group):
                error(INSTALL_ERROR)
        else:
            if not dir_perms_and_ownership(dir, squid_user, squid_group):
                error(INSTALL_ERROR)
            log(format%("Directory " + dir + " already exists."))

    # Create directory to store man page.
    if not os.path.isdir(man_dir):
        if not create_dir(man_dir):
            error(INSTALL_ERROR)
    else:
        log(format%("Directory " + man_dir + " already exists."))

    if not copy_dir('./intelligentmirror/', os.path.join(squid_conf_dir, 'intelligentmirror')):
        error(INSTALL_ERROR)

    if not copy_file('./update-im', '/usr/sbin/update-im'):
        error(INSTALL_ERROR)
    os.chmod('/usr/sbin/update-im',0744)

    if not copy_file('./intelligentmirror_sysconfig.conf', '/etc/intelligentmirror.conf'):
        error(INSTALL_ERROR)

    if not copy_file('./intelligentmirror.8.gz', os.path.join(man_dir, 'intelligentmirror.8.gz')):
        error(INSTALL_ERROR)

    if not create_file(os.path.join(squid_log_dir, 'intelligentmirror.log'), squid_user, squid_group):
        error(INSTALL_ERROR)

    if not generate_httpd_conf():
        error(INSTALL_ERROR)

    success()
    return

if __name__ == '__main__':
    log = set_logging()
    if len(sys.argv) == 2:
        if sys.argv[1] == 'install':
            if os.getuid() != 0:
                log(format%("You must be root to install/setup intelligentmirror."))
                error(UID_ERROR)
            else:
                setup()
        else:
            error(USAGE_ERROR)
    else:
        error(USAGE_ERROR)
