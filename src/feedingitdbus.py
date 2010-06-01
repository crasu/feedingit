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
# Name        : FeedingIt.py
# Author      : Yves Marcoz
# Version     : 0.5.4
# Description : Simple RSS Reader
# ============================================================================

import dbus
import dbus.service

class ServerObject(dbus.service.Object):
    def __init__(self, app):
        # Here the service name
        bus_name = dbus.service.BusName('org.maemo.feedingit',bus=dbus.SessionBus())
        # Here the object path
        dbus.service.Object.__init__(self, bus_name, '/org/maemo/feedingit')
        self.app = app

    # Here the interface name, and the method is named same as on dbus.
    @dbus.service.method('org.maemo.feedingit')
    def AddFeed(self, url):
        self.app.addFeed(url)
        return "Done"
    
    @dbus.service.method('org.maemo.feedingit')
    def GetStatus(self):
        return self.app.getStatus()

    @dbus.service.method('org.maemo.feedingit')
    def OpenFeed(self, key):
        #self.app.buttonFeedClicked(None, self.app, None, key)
        self.app.openFeed(key)
        return "Done"
