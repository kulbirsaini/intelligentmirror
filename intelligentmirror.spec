%define name 	intelligentmirror
%define version	0.2
%define release	1
%define prefix	/

Summary: 	Squid redirector to cache rpm packages
Name: 		%{name}
Version: 	%{version}
Release: 	%{release}
License: GPL
Group: 		Applications/Internet
URL:      http://fedora.co.in/
Source:   %{name}-%{version}-%{release}.tar.gz
Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root 
BuildArch: noarch
Requires: python
Requires:	python-urlgrabber
Requires: squid
Requires: httpd

%description
IntelligentMirror can be used to create a mirror of static HTTP content on your local network. When you download something (say a software package) from Internet, it is stored/cached on a local machine on your network and subsequent downloads of that particular software package are supplied from the storage/cache of the local machine. This facilitate the efficient usage of bandwidth and also reduces the average download time. IntelligentMirror can also do pre-fetching of RPM packages from fedora repositories spread all over the world and can also pre-populate the local repo with popular packages like mplayer, vlc, gstreamer which are normally accessed immediately after a fresh install. 
%prep

%setup -n %{name}-%{version}-%{release}

%build
echo "No building... its python..." > /dev/null

%install
rm -rf $RPM_BUILD_ROOT/
mkdir -p $RPM_BUILD_ROOT
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/etc/sysconfig
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/etc/httpd/conf.d/
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/etc/squid/intelligentmirror/
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/var/log/squid/
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror/temp/
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/usr/share/man/man8/
cp -f intelligentmirror/* ${RPM_BUILD_ROOT}%{prefix}/etc/squid/intelligentmirror/
cp -f intelligentmirror_sysconf.conf ${RPM_BUILD_ROOT}%{prefix}/etc/sysconfig/intelligentmirror.conf
cp -f intelligentmirror_httpd.conf ${RPM_BUILD_ROOT}%{prefix}/etc/httpd/conf.d/intelligentmirror.conf
cp -f intelligentmirror.8.gz ${RPM_BUILD_ROOT}%{prefix}/usr/share/man/man8/intelligentmirror.8.gz
touch ${RPM_BUILD_ROOT}%{prefix}/var/log/squid/intelligentmirror.log

%clean
rm -rf $RPM_BUILD_ROOT
rm -rf $RPM_BUILD_DIR/%{name}-%{version}-%{release}

%files
%{prefix}/etc/squid/intelligentmirror/*
%{prefix}/etc/sysconfig/intelligentmirror.conf
%{prefix}/etc/httpd/conf.d/intelligentmirror.conf
%{prefix}/var/log/squid/intelligentmirror.log
%{prefix}/var/spool/squid/intelligentmirror/*
%{prefix}/usr/share/man/man8/intelligentmirror.8.gz

%post
chown squid:squid ${RPM_BUILD_ROOT}%{prefix}/var/log/squid/intelligentmirror.log
chown -R squid:squid ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror
chmod -R 755 ${RPM_BUILD_ROOT}%{prefix}/var/spool/squid/intelligentmirror
echo "Reloading httpd service..."
service httpd reload
echo "You need to modify /etc/sysconfig/intelligentmirror.conf to make caching work properly."
echo "Also you need to configure squid. Check intelligentmirror manpage for more details."

%preun

%changelog
* Wed Jun 25 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Bumped to version 0.2

* Wed Jun 25 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Fixed few bugs(proxy loops). Corrected configuration files. Added spec, README, INSTALL, conf files. Rearranged hierarchy.
- XMLRPCService is being used to share memory across the several instances of intelligentmirror. This fix the problem
- of looping for the same url while trying to fetch package from remote (because we use the same proxy server to fetch
- the package and that ends in loops). More options added to configuration files. Also, README and INSTALL files are
- added to for help. Manpage is also added.

* Tue Jun 17 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Temporary directory for downloads is introduced. Package are first saved to temp_dir and then moved to cache_dir after a successful download.

* Fri Jun 13 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Configuration file moved to /etc/sysconfig/intelligentmirror.conf . Config parser taken from yum source code.

* Sun Jun 8 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Few bug fixes. Tested with squid. Everything seems to work fine :)

* Sat Jun 7 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Packages are downloaded parallely in the background now and are not served from the cache for the first time.
- Special thanks to http://blog.buffis.com/?p=63 for daemon forking tutorial :)

* Wed Jun 4 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Added support for handling errors while retrieving packages.

* Tue Jun 3 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Changed logging system from simple file logging to the standard python logging.

* Mon Jun 2 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- Improved caching. Now package is checked for updates. Separate function added for testing on command line. Also included extensive logging.

* Mon Jun 2 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- intelligentmirror : Initial Commit Version 0.0

