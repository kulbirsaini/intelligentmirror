%define name 	intelligentmirror
%define version	0.2
%define release	1
%define prefix	/home2/Studies/project/testing/

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
cp -f intelligentmirror.8 ${RPM_BUILD_ROOT}%{prefix}/usr/share/man/man8/intelligentmirror.8
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
%{prefix}/usr/share/man/man8/intelligentmirror.8

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
* Mon Jun 23 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- 0.2-1
- Fixed few bugs. Added config file support. Now videos are not checked for updates assuming that videos will never change.
- Previously youtube_cache tried to connect to internet directly. Now it uses the proxy on which its hosted.

* Thu Jun 12 2008 Kulbir Saini <kulbirsaini@students.iiit.ac.in>
- 0.1-1
- Initial Version: youtube_cache-0.1 . Works well with squid-2.6STABLE16 and up. Redundand caching.
