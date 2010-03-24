# This Makefile is only used when building Debian packages

DESTDIR=/

all:

install:
	install -d ${DESTDIR}/usr/bin
	install src/FeedingIt ${DESTDIR}/usr/bin
	install -d ${DESTDIR}/opt/FeedingIt
	install src/FeedingIt.py ${DESTDIR}/opt/FeedingIt
	install src/feedparser.py ${DESTDIR}/opt/FeedingIt
	install src/portrait.py ${DESTDIR}/opt/FeedingIt
	install src/rss.py ${DESTDIR}/opt/FeedingIt
	install src/opml.py ${DESTDIR}/opt/FeedingIt
	install src/config.py ${DESTDIR}/opt/FeedingIt
	install src/BeautifulSoup.py ${DESTDIR}/opt/FeedingIt
	install src/feedingitdbus.py ${DESTDIR}/opt/FeedingIt
	install -d ${DESTDIR}/usr/share/applications/hildon
	install src/FeedingIt.desktop ${DESTDIR}/usr/share/applications/hildon
	install -d ${DESTDIR}/usr/share/icons/hicolor/40x40/apps/
	install data/40px.png ${DESTDIR}/usr/share/icons/hicolor/40x40/apps/feedingit.png
	install -d ${DESTDIR}/usr/share/icons/hicolor/26x26/apps/
	install data/26px.png ${DESTDIR}/usr/share/icons/hicolor/26x26/apps/feedingit.png
	install -d ${DESTDIR}/usr/share/icons/hicolor/64x64/apps/
	install data/64px.png ${DESTDIR}/usr/share/icons/hicolor/64x64/apps/feedingit.png
	install -d ${DESTDIR}/usr/share/dbus-1/services/
	install src/feedingit.service ${DESTDIR}/usr/share/dbus-1/services/
	install -d ${DESTDIR}/etc/osso-backup/applications/
	install src/feedingit.conf ${DESTDIR}/etc/osso-backup/applications/
	
clean:
	rm src/*pyo
	
sourcepkg:
	dpkg-buildpackage -rfakeroot -sa -S -i -I.git
