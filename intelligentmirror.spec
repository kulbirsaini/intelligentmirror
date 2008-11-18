%define prefix /

Name:         intelligentmirror
Version:      0.5
Release:      1
Summary:      Squid url rewriter to cache rpm/deb packages.
License:      GPL
Group:        Applications/Internet
URL:          https://fedorahosted.org/intelligentmirror
Source:       %{name}-%{version}.tar.gz
Buildroot:    %{_tmppath}/%{name}-%{version}-root 
BuildArch:    noarch
Requires:     python
Requires:     python-iniparse
Requires:     python-urlgrabber
Requires:     squid
Requires:     httpd

%description
IntelligentMirror can be used to create a mirror of static HTTP content on your local network.
When you download something (say a software package) from Internet, it is stored/cached on a
local machine on your network and subsequent downloads of that particular software package are
supplied from the storage/cache of the local machine. This facilitate the efficient usage
of bandwidth and also reduces the average download time. 
%prep

%setup -n %{name}-%{version}

%build
echo "No building... its python..." > /dev/null

%install
rm -rf $RPM_BUILD_ROOT/
mkdir -p $RPM_BUILD_ROOT
install -d ${RPM_BUILD_ROOT}%{prefix}/etc/httpd/conf.d/
install -m 755 -d ${RPM_BUILD_ROOT}%{prefix}/etc/squid/intelligentmirror/
install -m 755 -d ${RPM_BUILD_ROOT}%{prefix}/usr/sbin/
install -m 700 -o squid -g squid -d ${RPM_BUILD_ROOT}%{prefix}/var/log/squid/
install -m 755 -o squid -g squid -d ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror/
install -m 755 -o squid -g squid -d ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror/rpm/
install -m 755 -o squid -g squid -d ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror/deb/
install -m 755 -o squid -g squid -d ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror/tmp/
install -m 744 -d ${RPM_BUILD_ROOT}%{prefix}/usr/share/man/man8/
install -m 644 intelligentmirror/* -t ${RPM_BUILD_ROOT}%{prefix}/etc/squid/intelligentmirror/
install -m 644 intelligentmirror_sysconfig.conf -T ${RPM_BUILD_ROOT}%{prefix}/etc/intelligentmirror.conf
install -m 644 intelligentmirror_httpd.conf -T ${RPM_BUILD_ROOT}%{prefix}/etc/httpd/conf.d/intelligentmirror.conf
install -m 644 intelligentmirror.8.gz -T ${RPM_BUILD_ROOT}%{prefix}/usr/share/man/man8/intelligentmirror.8.gz
install -m 744 update-im -T ${RPM_BUILD_ROOT}%{prefix}/usr/sbin/update-im
touch ${RPM_BUILD_ROOT}%{prefix}/var/log/squid/intelligentmirror.log

%clean
rm -rf $RPM_BUILD_ROOT
rm -rf $RPM_BUILD_DIR/%{name}-%{version}

%files
%{prefix}/etc/squid/intelligentmirror/
%{prefix}/etc/intelligentmirror.conf
%{prefix}/etc/httpd/conf.d/intelligentmirror.conf
%{prefix}/var/log/squid/intelligentmirror.log
%{prefix}/usr/share/man/man8/intelligentmirror.8.gz
%{prefix}/usr/sbin/update-im

%post
chown squid:squid ${RPM_BUILD_ROOT}%{prefix}/var/log/squid/intelligentmirror.log
chown -R squid:squid ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror
echo "Reloading httpd service..."
/sbin/service httpd reload
echo "You need to modify /etc/intelligentmirror.conf to make caching work properly."
echo "Also you need to configure squid. Check intelligentmirror manpage for more details."

%preun

%changelog
* Fri Sep 19 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Fixed spec file for package name specification.

* Fri Sep 19 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Updated and corrected spec file. Also updated to new version 0.4.

* Fri Sep 19 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Fixed the defunct process bug. Ready to cache debian packages as well.
Introduced limits on package and cache sizes. Option to enable/disable
caching rpm/deb packages are available now.

* Tue Sep 16 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
A few corrections in INSTALL file.

* Mon Aug 25 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Implemented the new set of options. Also a lot of performance enhancement. IM is faster now. Deb caching working perfectly.

* Sat Aug 23 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
A new series of options has been proposed. Not implemented yet, but will be implemented very soon.

* Tue Aug 19 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Working version with squid-2.6STABLE16 and above. Forked processes still defuct after download.
Need to dig more to figure it out.

* Wed Jun 25 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Bumped to version 0.2

* Wed Jun 25 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Fixed few bugs(proxy loops). Corrected configuration files. Added spec, README, INSTALL, conf files. Rearranged hierarchy.
XMLRPCService is being used to share memory across the several instances of intelligentmirror. This fix the problem
of looping for the same url while trying to fetch package from remote (because we use the same proxy server to fetch
the package and that ends in loops). More options added to configuration files. Also, README and INSTALL files are
added to for help. Manpage is also added.

* Tue Jun 17 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Temporary directory for downloads is introduced. Package are first saved to temp_dir and then moved to cache_dir after a successful download.

* Fri Jun 13 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Configuration file moved to /etc/sysconfig/intelligentmirror.conf . Config parser taken from yum source code.

* Sun Jun 8 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Few bug fixes. Tested with squid. Everything seems to work fine :)

* Sat Jun 7 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Packages are downloaded parallely in the background now and are not served from the cache for the first time.
Special thanks to http://blog.buffis.com/?p=63 for daemon forking tutorial :)

* Wed Jun 4 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Added support for handling errors while retrieving packages.

* Tue Jun 3 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Changed logging system from simple file logging to the standard python logging.

* Mon Jun 2 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
Improved caching. Now package is checked for updates. Separate function added for testing on command line. Also included extensive logging.

* Mon Jun 2 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
intelligentmirror : Initial Commit Version 0.0

