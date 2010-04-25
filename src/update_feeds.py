#!/usr/bin/env python2.5

# 
# Copyright (c) 2007-2008 INdT.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# ============================================================================
# Name        : update_feeds.py
# Author      : Yves Marcoz
# Version     : 0.6.1
# Description : Simple RSS Reader
# ============================================================================

from rss import Listing
from config import Config

import threading
import os
import gobject

CONFIGDIR="/home/user/.feedingit/"
LOCK = CONFIGDIR + "update.lock"
#DESKTOP_FILE = "/usr/share/applications/hildon-status-menu/feedingit_status.desktop"

from updatedbus import UpdateServerObject, get_lock

class Download(threading.Thread):
    def __init__(self, listing, config, dbusHandler):
        threading.Thread.__init__(self)
        self.running = True
        self.listing = listing
        self.config = config
        self.dbusHandler = dbusHandler
        self.dbug = open(CONFIGDIR+"dbug.log", "w")
        self.dbug.flush()
        
    def run(self):
        self.dbug.write("Starting updates")
        self.dbug.flush()
        try:
            self.dbusHandler.UpdateStarted()
            (use_proxy, proxy) = self.config.getProxy()
            for key in self.listing.getListOfFeeds():
                self.dbug.write("updating %s\n" %key)
                self.dbug.flush()
                try:
                    if use_proxy:
                        from urllib2 import install_opener, build_opener
                        install_opener(build_opener(proxy))
                        self.listing.updateFeed(key, self.config.getExpiry(), proxy=proxy, imageCache=self.config.getImageCache() )
                    else:
                        self.listing.updateFeed(key, self.config.getExpiry(), imageCache=self.config.getImageCache() )
                except:
                    import traceback
                    file = open("/home/user/.feedingit/feedingit_update.log", "a")
                    traceback.print_exc(file=file)
                    file.close()
                if not self.running:
                    self.dbug.write("received stopUpdate after %s\n" %key)
                    self.dbug.flush()
                    break
            self.dbusHandler.UpdateFinished()
            self.dbusHandler.ArticleCountUpdated()
            self.dbug.write("Dbus ArticleCountUpdated signal sent\n")
            self.dbug.flush()
            try:
                os.remove(LOCK)
                #os.remove(DESKTOP_FILE)
            except:
                pass
        except:
            pass
        self.listing.saveConfig()
        self.dbug.write("About to main_quit\n")
        self.dbug.flush()
        mainloop.quit()
        file.write("After main_quit\n")
        self.dbug.flush()
        self.dbug.close()

class FeedUpdate():
    def __init__(self):
        self.listing = Listing(CONFIGDIR)
        self.config = Config(self, CONFIGDIR+"config.ini")
        self.dbusHandler = UpdateServerObject(self)
        self.updateThread = False
        
    def automaticUpdate(self):
        #self.listing.updateFeeds()
        if self.updateThread == False:
            self.updateThread = Download(self.listing, self.config, self.dbusHandler)
            self.updateThread.start()
        
    def stopUpdate(self):
        try:
            self.updateThread.running = False
        except:
            pass

import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

gobject.threads_init()
mainloop = gobject.MainLoop()

app_lock = get_lock("app_lock")

if app_lock != None:
    try:
        feed = FeedUpdate()
        mainloop.run()
        del app_lock
    except:
        import traceback
        file = open("/home/user/.feedingit/feedingit_update.log", "a")
        traceback.print_exc(file=file)
        file.close()
else:
    file = open("/home/user/.feedingit/feedingit_update.log", "a")
    file.write("Update in progress")
    file.close()
    
