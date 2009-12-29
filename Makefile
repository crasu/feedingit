# This Makefile is only used when building Debian packages

DESTDIR=/

all:

install:
	install -d ${DESTDIR}/usr/bin
	install src/FeedingIt ${DESTDIR}/usr/bin
	install -d ${DESTDIR}/opt/FeedingIt
	install src/FeedingIt.py ${DESTDIR}/opt/FeedingIt
	install src/feedparser.py ${DESTDIR}/opt/FeedingIt
	install -d ${DESTDIR}/usr/share/applications/hildon
	install src/FeedingIt.desktop ${DESTDIR}/usr/share/applications/hildon