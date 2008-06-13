#!/usr/bin/python -tt
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
# Copyright 2004 Duke University
#
# Errors.py has been taken from yum source code.
#

"""
Exceptions and Errors thrown by yum.
"""

class YumBaseError(Exception):
    """
    Base Yum Error. All other Errors thrown by yum should inherit from
    this.
    """
    def __init__(self, value=None):
        Exception.__init__(self)
        self.value = value
    def __str__(self):
        return "%s" %(self.value,)

class YumGPGCheckError(YumBaseError):
    pass

class YumDownloadError(YumBaseError):
    pass

class YumTestTransactionError(YumBaseError):
    pass

class YumRPMCheckError(YumBaseError):
    pass
        
class LockError(YumBaseError):
    def __init__(self, errno, msg):
        YumBaseError.__init__(self)
        self.errno = errno
        self.msg = msg
        
class DepError(YumBaseError):
    pass
    
class RepoError(YumBaseError):
    pass

class DuplicateRepoError(RepoError):
    pass

class NoMoreMirrorsRepoError(RepoError):
    pass
    
class ConfigError(YumBaseError):
    pass
    
class MiscError(YumBaseError):
    pass

class GroupsError(YumBaseError):
    pass

class InstallError(YumBaseError):
    pass

class UpdateError(YumBaseError):
    pass
    
class RemoveError(YumBaseError):
    pass

class ReinstallError(YumBaseError):
    pass

class RepoMDError(YumBaseError):
    pass

class PackageSackError(YumBaseError):
    pass

class CompsException(YumBaseError):
    pass

class MediaError(YumBaseError):
    pass
    
class YumDeprecationWarning(DeprecationWarning):
    """
    Used to mark a method as deprecated.
    """
    def __init__(self, value=None):
        DeprecationWarning.__init__(self, value)

class YumFutureDeprecationWarning(YumDeprecationWarning):
    """
    Used to mark a method as deprecated. Unlike YumDeprecationWarning,
    YumFutureDeprecationWarnings will not be shown on the console.
    """
    def __init__(self, value=None):
        YumDeprecationWarning.__init__(self, value)
